#!/bin/bash

# 🛑 LEXO v1 - Arrêt Native macOS
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

LEXO_DIR=$(pwd)
log "🛑 Arrêt LEXO v1 Native"

# Vérification des tâches batch avant arrêt natif
if curl -s http://localhost:8000/api/v1/batch/status 2>/dev/null | grep -q '"active_tasks": [1-9]'; then
    echo -e "${YELLOW}[WARNING]${NC} Des traitements batch natifs sont en cours!"
    echo "Voulez-vous vraiment arrêter ? [y/N]"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log "Arrêt annulé par l'utilisateur"
        exit 0
    fi
fi

# Sauvegarde automatique native
BACKUP_DIR="logs/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Sauvegarder état batch en cours
curl -s http://localhost:8000/api/v1/batch/status > "$BACKUP_DIR/batch_status_$(date +%H%M%S).json" 2>/dev/null || true

# Arrêt par PID files
if [ -f "logs/backend_native.pid" ]; then
    BACKEND_PID=$(cat logs/backend_native.pid)
    kill $BACKEND_PID 2>/dev/null || true
    rm logs/backend_native.pid
    success "✅ Backend FastAPI arrêté"
fi

if [ -f "logs/frontend_native.pid" ]; then
    FRONTEND_PID=$(cat logs/frontend_native.pid)
    kill $FRONTEND_PID 2>/dev/null || true
    rm logs/frontend_native.pid
    success "✅ Frontend Next.js arrêté"
fi

if [ -f "logs/mistral_native.pid" ]; then
    MISTRAL_PID=$(cat logs/mistral_native.pid)
    kill $MISTRAL_PID 2>/dev/null || true
    rm logs/mistral_native.pid
    success "✅ Service Mistral MLX arrêté"
fi

# Arrêt par ports (backup)
for PORT in 3000 8000 8004; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        log "Port $PORT libéré"
    fi
done

# Sauvegarder statistiques processus natifs
ps aux | grep -E "(uvicorn|next|python.*document_analyzer)" | grep -v grep > "$BACKUP_DIR/native_stats_$(date +%H%M%S).txt" 2>/dev/null || true

# Services système (optionnel - garder pour développement)
# brew services stop postgresql@15
# brew services stop redis

success "✅ Tous les services LEXO arrêtés"
echo ""
echo "💡 PostgreSQL et Redis restent actifs pour le développement"
echo "   Pour les arrêter: brew services stop postgresql@15 redis"
echo "📁 Sauvegarde dans: $BACKUP_DIR"