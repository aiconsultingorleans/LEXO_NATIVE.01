#!/bin/bash

# Script de démarrage du service Document Analyzer MLX natif
# LEXO v1 - Architecture hybride

echo "🚀 Démarrage Document Analyzer MLX - LEXO v1"
echo "=============================================="

# Configuration
SERVICE_NAME="Document Analyzer"
SERVICE_PORT=8004
PYTHON_ENV="python3"
LOG_FILE="logs/document_analyzer.log"
PID_FILE="pids/document_analyzer.pid"

# Créer les dossiers nécessaires
mkdir -p logs pids

# Vérifier que MLX est installé
echo "📦 Vérification des dépendances MLX..."
if ! $PYTHON_ENV -c "import mlx.core, mlx_lm" 2>/dev/null; then
    echo "❌ MLX ou mlx-lm non installé"
    echo "💡 Installation requise :"
    echo "   pip install mlx mlx-lm"
    exit 1
fi

# Vérifier que FastAPI est disponible
if ! $PYTHON_ENV -c "import fastapi" 2>/dev/null; then
    echo "❌ FastAPI non installé"
    echo "💡 Installation requise :"
    echo "   pip install fastapi uvicorn"
    exit 1
fi

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

# Lancer le service en arrière-plan
cd ai_services
nohup $PYTHON_ENV document_analyzer.py > "../$LOG_FILE" 2>&1 & echo $! > "../$PID_FILE"

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