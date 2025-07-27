#!/bin/bash

# 🚀 LEXO v1 - Démarrage Native macOS
set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

LEXO_DIR=$(pwd)
log "🚀 Démarrage LEXO v1 Native - $LEXO_DIR"

# Créer répertoire logs s'il n'existe pas
mkdir -p logs

# 1. Vérification services système
log "🔍 Vérification services système..."

# PostgreSQL
if brew services list | grep -q "postgresql@15.*started"; then
    success "✅ PostgreSQL 15 actif"
else
    log "Démarrage PostgreSQL..."
    brew services start postgresql@15
    sleep 3
    success "✅ PostgreSQL 15 démarré"
fi

# Redis
if brew services list | grep -q "redis.*started"; then
    success "✅ Redis actif"
else
    log "Démarrage Redis..."
    brew services start redis
    sleep 2
    success "✅ Redis démarré"
fi

# 2. Démarrage Backend FastAPI
log "🐍 Démarrage Backend FastAPI..."
cd "$LEXO_DIR/backend"

if [ ! -d "venv" ]; then
    error "Environnement virtuel backend manquant - Exécutez d'abord la Phase 3"
    exit 1
fi

# Tuer processus existant
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Démarrage en arrière-plan
source venv/bin/activate
nohup uvicorn main:app --reload --port 8000 > "$LEXO_DIR/logs/backend_native.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > "$LEXO_DIR/logs/backend_native.pid"

# Attendre démarrage
sleep 8
if curl -s http://localhost:8000/api/v1/health | grep -q "healthy"; then
    success "✅ Backend FastAPI (port 8000) - PID: $BACKEND_PID"
else
    error "❌ Backend FastAPI non accessible"
fi

# 3. Démarrage Frontend Next.js
log "⚛️  Démarrage Frontend Next.js..."
cd "$LEXO_DIR/frontend"

# Tuer processus existant
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Démarrage en arrière-plan
nohup npm run dev > "$LEXO_DIR/logs/frontend_native.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > "$LEXO_DIR/logs/frontend_native.pid"

# Attendre démarrage
sleep 8
if curl -s http://localhost:3000 >/dev/null 2>&1; then
    success "✅ Frontend Next.js (port 3000) - PID: $FRONTEND_PID"
else
    error "❌ Frontend Next.js non accessible"
fi

# 4. Démarrage Service MLX
log "🤖 Démarrage Service Mistral MLX..."
cd "$LEXO_DIR/ai_services"

# Tuer processus existant
lsof -ti:8004 | xargs kill -9 2>/dev/null || true

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    nohup python document_analyzer.py > "$LEXO_DIR/logs/mistral_native.log" 2>&1 &
    MISTRAL_PID=$!
    echo $MISTRAL_PID > "$LEXO_DIR/logs/mistral_native.pid"
    
    # Attendre chargement modèle (plus long)
    log "⏳ Chargement modèle Mistral (30-60s)..."
    sleep 30
    
    if curl -s http://localhost:8004/health | grep -q "healthy"; then
        success "✅ Service Mistral MLX (port 8004) - PID: $MISTRAL_PID"
    else
        error "❌ Service Mistral MLX non prêt - Vérifier logs/mistral_native.log"
    fi
else
    error "❌ Environnement MLX manquant"
fi

# 5. Démarrage Service DONUT (optionnel)
log "🍩 Démarrage Service DONUT (alternatif)..."
cd "$LEXO_DIR/ai_services"

# Tuer processus existant
lsof -ti:8005 | xargs kill -9 2>/dev/null || true

if [ -f "venv_donut/bin/activate" ]; then
    source venv_donut/bin/activate
    nohup python donut_camembert_analyzer.py > "$LEXO_DIR/logs/donut_native.log" 2>&1 &
    DONUT_PID=$!
    echo $DONUT_PID > "$LEXO_DIR/logs/donut_native.pid"
    
    # Attendre chargement modèles DONUT (plus rapide que Mistral)
    log "⏳ Chargement modèles DONUT + CamemBERT (15-20s)..."
    sleep 15
    
    if curl -s http://localhost:8005/health | grep -q "healthy"; then
        success "✅ Service DONUT (port 8005) - PID: $DONUT_PID"
    else
        error "❌ Service DONUT non prêt - Vérifier logs/donut_native.log"
    fi
else
    log "⚠️  Environnement DONUT non trouvé - Service alternatif non démarré"
fi

cd "$LEXO_DIR"

# 6. Statut final
echo ""
log "🎉 LEXO v1 Native - Démarrage terminé!"
echo ""
echo "📊 Services disponibles:"
echo "  ✅ Frontend:     http://localhost:3000"
echo "  ✅ Backend API:  http://localhost:8000"
echo "  ✅ API Docs:     http://localhost:8000/docs"
echo "  ✅ PostgreSQL:   localhost:5432"
echo "  ✅ Redis:        localhost:6379"
echo "  ✅ Mistral MLX:  http://localhost:8004"
if [ -f "logs/donut_native.pid" ]; then
    echo "  ✅ DONUT Alt:    http://localhost:8005"
fi
echo ""
echo "📁 Logs: logs/"
echo "🛑 Arrêt: ./stop_native.sh"
echo ""

# Ouvrir navigateur
sleep 2
if command -v open &> /dev/null; then
    open http://localhost:3000
fi