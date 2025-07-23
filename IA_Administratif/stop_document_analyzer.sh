#!/bin/bash

# Script d'arrêt du service Document Analyzer MLX natif
# LEXO v1 - Architecture hybride

echo "🛑 Arrêt Document Analyzer MLX - LEXO v1"
echo "========================================"

PID_FILE="pids/document_analyzer.pid"
SERVICE_PORT=8004

# Vérifier si le PID file existe
if [ ! -f "$PID_FILE" ]; then
    echo "⚠️  Aucun fichier PID trouvé ($PID_FILE)"
    
    # Chercher le processus par port
    PROCESS_PID=$(lsof -ti:$SERVICE_PORT)
    if [ ! -z "$PROCESS_PID" ]; then
        echo "🔍 Processus trouvé utilisant le port $SERVICE_PORT (PID: $PROCESS_PID)"
        echo "🛑 Arrêt du processus..."
        kill $PROCESS_PID
        sleep 2
        
        if ps -p $PROCESS_PID > /dev/null 2>&1; then
            echo "⚠️  Processus résistant, force kill..."
            kill -9 $PROCESS_PID
        fi
        echo "✅ Processus arrêté"
    else
        echo "ℹ️  Aucun processus trouvé sur le port $SERVICE_PORT"
    fi
    exit 0
fi

# Lire le PID
PID=$(cat "$PID_FILE")

# Vérifier si le processus existe
if ps -p $PID > /dev/null 2>&1; then
    echo "🛑 Arrêt du service Document Analyzer (PID: $PID)..."
    
    # Arrêt gracieux
    kill $PID
    sleep 3
    
    # Vérifier si le processus est encore actif
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Processus résistant, force kill..."
        kill -9 $PID
        sleep 1
    fi
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "❌ Impossible d'arrêter le processus $PID"
        exit 1
    else
        echo "✅ Service arrêté avec succès"
    fi
else
    echo "⚠️  Processus $PID non trouvé (déjà arrêté?)"
fi

# Nettoyer le fichier PID
rm -f "$PID_FILE"

# Vérifier que le port est libéré
if lsof -Pi :$SERVICE_PORT -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Le port $SERVICE_PORT est encore utilisé"
    REMAINING_PID=$(lsof -ti:$SERVICE_PORT)
    echo "🔧 Processus restant : $REMAINING_PID"
else
    echo "✅ Port $SERVICE_PORT libéré"
fi

echo "🏁 Arrêt terminé"