#!/bin/bash
# Script de démarrage du service DONUT CamemBERT Analyzer
# Étape 2 Infrastructure - Service parallèle port 8005

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/venv_donut"
SERVICE_SCRIPT="$SCRIPT_DIR/donut_camembert_analyzer.py"

echo "🍩 Démarrage Service DONUT CamemBERT Analyzer"
echo "📁 Dossier: $SCRIPT_DIR"
echo "🐍 Environnement: $VENV_PATH"

# Vérifications
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ Environnement virtuel non trouvé: $VENV_PATH"
    exit 1
fi

if [ ! -f "$SERVICE_SCRIPT" ]; then
    echo "❌ Script service non trouvé: $SERVICE_SCRIPT"
    exit 1
fi

# Activation environnement et démarrage
echo "🔄 Activation environnement virtuel..."
source "$VENV_PATH/bin/activate"

echo "🚀 Lancement service port 8005..."
echo "📍 URL: http://localhost:8005"
echo "📚 Documentation: http://localhost:8005/docs"
echo ""
echo "⚠️  Appuyer Ctrl+C pour arrêter"

# Démarrage du service
python "$SERVICE_SCRIPT"