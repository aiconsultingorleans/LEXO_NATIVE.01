#!/bin/bash

# Script de démarrage du service Document Analyzer MLX natif
# LEXO v1 - Architecture hybride

echo "🚀 Démarrage Document Analyzer MLX - LEXO v1"
echo "=============================================="

# Configuration
SERVICE_NAME="Document Analyzer"
SERVICE_PORT=8004
VENV_PATH="ai_services/venv"
LOG_FILE="logs/document_analyzer.log"
PID_FILE="pids/document_analyzer.pid"

# Créer les dossiers nécessaires
mkdir -p logs pids

# Vérifier que l'environnement virtuel existe
echo "📦 Vérification de l'environnement virtuel MLX..."
if [ ! -f "$VENV_PATH/bin/activate" ]; then
    echo "❌ Environnement virtuel MLX non trouvé"
    echo "💡 Création de l'environnement virtuel..."
    cd ai_services
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    deactivate
    cd ..
    echo "✅ Environnement virtuel créé"
fi

# Activer l'environnement virtuel et vérifier MLX
source "$VENV_PATH/bin/activate"
if ! python -c "import mlx.core, mlx_lm" 2>/dev/null; then
    echo "❌ MLX ou mlx-lm non installé dans l'environnement virtuel"
    echo "💡 Installation en cours..."
    pip install mlx mlx-lm fastapi uvicorn
fi

# Vérifier que FastAPI est disponible
if ! python -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI non installé dans l'environnement virtuel"
    echo "💡 Installation en cours..."
    pip install fastapi uvicorn
fi

deactivate

# Vérifier si le service est déjà en cours
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p $OLD_PID > /dev/null 2>&1; then
        echo "⚠️  Service déjà en cours (PID: $OLD_PID)"
        echo "🛑 Arrêt de l'ancien processus..."
        kill $OLD_PID
        sleep 2
    fi
    rm -f "$PID_FILE"
fi

# Vérifier que le port est libre
echo "🔍 Vérification du port $SERVICE_PORT..."
if lsof -Pi :$SERVICE_PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "❌ Port $SERVICE_PORT déjà utilisé"
    echo "🔧 Processus utilisant le port :"
    lsof -Pi :$SERVICE_PORT -sTCP:LISTEN
    exit 1
fi

# Démarrer le service
echo "🎯 Démarrage du $SERVICE_NAME..."
echo "📂 Log file: $LOG_FILE"
echo "🆔 PID file: $PID_FILE"
echo "🌐 URL: http://127.0.0.1:$SERVICE_PORT"

# Lancer le service en arrière-plan avec l'environnement virtuel
cd ai_services
source venv/bin/activate
nohup python document_analyzer.py > "../$LOG_FILE" 2>&1 & echo $! > "../$PID_FILE"
deactivate

# Attendre le démarrage
sleep 3

# Vérifier que le service a démarré
PID=$(cat "../$PID_FILE")
if ps -p $PID > /dev/null 2>&1; then
    echo "✅ $SERVICE_NAME démarré avec succès (PID: $PID)"
    
    # Test de santé
    echo "🏥 Test de santé du service..."
    sleep 2
    
    if curl -s http://127.0.0.1:$SERVICE_PORT/health > /dev/null; then
        echo "✅ Service opérationnel - Health check OK"
        echo ""
        echo "📋 Endpoints disponibles :"
        echo "   http://127.0.0.1:$SERVICE_PORT/health"
        echo "   http://127.0.0.1:$SERVICE_PORT/analyze"
        echo "   http://127.0.0.1:$SERVICE_PORT/docs (Swagger UI)"
        echo ""
        echo "🔧 Pour arrêter le service :"
        echo "   ./stop_document_analyzer.sh"
        echo "   ou: kill $PID"
    else
        echo "⚠️  Service démarré mais health check échoué"
        echo "📖 Consulter les logs : tail -f $LOG_FILE"
    fi
else
    echo "❌ Échec du démarrage du service"
    echo "📖 Consulter les logs : cat $LOG_FILE"
    exit 1
fi