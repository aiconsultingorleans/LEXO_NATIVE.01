#!/bin/bash

# 🔍 LEXO v1 - Script de vérification de santé
# Diagnostique l'état des services et corrige les problèmes courants

set -e  # Arrêt en cas d'erreur

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonction de log
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Vérification du répertoire
cd "$(dirname "$0")"
LEXO_DIR=$(pwd)

echo "🔍 LEXO v1 - Vérification de santé complète"
echo "============================================"
echo ""

# 1. Vérification des services Docker
log "📊 Vérification des services Docker..."
cd "$LEXO_DIR/IA_Administratif"

if ! docker info >/dev/null 2>&1; then
    error "❌ Docker n'est pas accessible"
    exit 1
fi

SERVICES=("postgres" "redis" "backend" "frontend" "chromadb")
ALL_RUNNING=true

for SERVICE in "${SERVICES[@]}"; do
    if docker compose ps "$SERVICE" | grep -q "running"; then
        success "✅ $SERVICE: En cours d'exécution"
    else
        error "❌ $SERVICE: Arrêté ou en erreur"
        ALL_RUNNING=false
    fi
done

echo ""

# 2. Vérification des endpoints
log "🌐 Vérification des endpoints..."

ENDPOINTS=(
    "http://localhost:3000:Frontend"
    "http://localhost:8000/api/v1/health:Backend API"
    "http://localhost:8001/api/v2/version:ChromaDB"
    "http://localhost:8004/health:MLX Service"
    "http://localhost:8000/api/v1/batch/status:API Batch Progress"
)

for ENDPOINT_INFO in "${ENDPOINTS[@]}"; do
    IFS=':' read -r URL NAME <<< "$ENDPOINT_INFO"
    if curl -s --connect-timeout 3 --max-time 5 "$URL" >/dev/null 2>&1; then
        success "✅ $NAME: Accessible"
    else
        error "❌ $NAME: Non accessible ($URL)"
    fi
done

echo ""

# 3. Vérification des dépendances critiques
log "🔧 Vérification des dépendances critiques..."

if docker compose ps backend | grep -q "running"; then
    # Vérifier psutil
    if docker compose exec -T backend python -c "import psutil" 2>/dev/null; then
        success "✅ psutil: Disponible"
    else
        error "❌ psutil: Manquant"
        echo "   🔧 Correction: docker compose exec backend pip install psutil==6.1.0"
    fi
    
    # Vérifier les autres dépendances critiques
    DEPS=("sqlalchemy" "fastapi" "redis" "chromadb")
    for DEP in "${DEPS[@]}"; do
        if docker compose exec -T backend python -c "import $DEP" 2>/dev/null; then
            success "✅ $DEP: Disponible"
        else
            error "❌ $DEP: Manquant"
        fi
    done
else
    warning "⚠️  Backend non accessible, vérification des dépendances ignorée"
fi

echo ""

# 4. Vérification de la base de données
log "🗄️  Vérification de la base de données..."

if docker compose ps postgres | grep -q "running"; then
    if docker compose exec -T postgres pg_isready -U lexo >/dev/null 2>&1; then
        success "✅ PostgreSQL: Prêt"
        
        # Vérifier les comptes utilisateurs
        USER_COUNT=$(docker compose exec -T backend python -c "
import asyncio
from models.user import User
from core.database import AsyncSessionLocal
from sqlalchemy import select

async def check_users():
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User))
            users = result.scalars().all()
            return len(users)
    except Exception:
        return -1

result = asyncio.run(check_users())
print(result)
" 2>/dev/null)
        
        if [ "$USER_COUNT" = "0" ] || [ "$USER_COUNT" = "-1" ]; then
            error "❌ Comptes utilisateurs: Aucun compte trouvé"
            echo "   🔧 Correction: docker compose exec backend python scripts/load_fixtures_auto.py"
        else
            success "✅ Comptes utilisateurs: $USER_COUNT utilisateurs trouvés"
        fi
        
        # Vérifier spécifiquement le compte admin
        ADMIN_EXISTS=$(docker compose exec -T backend python -c "
import asyncio
from models.user import User
from core.database import AsyncSessionLocal
from sqlalchemy import select

async def check_admin():
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(User).where(User.email == 'admin@lexo.fr'))
            admin = result.scalar_one_or_none()
            return admin is not None
    except Exception:
        return False

result = asyncio.run(check_admin())
print('True' if result else 'False')
" 2>/dev/null)
        
        if [ "$ADMIN_EXISTS" = "True" ]; then
            success "✅ Compte admin: Présent (admin@lexo.fr)"
        else
            error "❌ Compte admin: Manquant"
            echo "   🔧 Correction: docker compose exec backend python scripts/load_fixtures_auto.py"
        fi
    else
        error "❌ PostgreSQL: Non prêt"
    fi
else
    error "❌ PostgreSQL: Conteneur non accessible"
fi

echo ""

# 5. Vérification des ports
log "🔌 Vérification des ports..."

PORTS=(3000 8000 8001 8004 5432 6379 8080)
for PORT in "${PORTS[@]}"; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        PROCESS=$(lsof -Pi :$PORT -sTCP:LISTEN -t | head -1)
        success "✅ Port $PORT: Utilisé (PID: $PROCESS)"
    else
        warning "⚠️  Port $PORT: Libre"
    fi
done

echo ""

# 6. Vérification des nouvelles fonctionnalités
log "🚀 Vérification des nouvelles fonctionnalités..."

if curl -s http://localhost:8000/api/v1/batch/status >/dev/null 2>&1; then
    success "✅ API de progression batch: Disponible"
    
    # Vérifier le format de la réponse
    RESPONSE=$(curl -s http://localhost:8000/api/v1/batch/status)
    if echo "$RESPONSE" | grep -q "active_tasks"; then
        success "✅ Format API batch: Correct"
    else
        warning "⚠️  Format API batch: Inattendu"
    fi
else
    error "❌ API de progression batch: Non accessible"
fi

echo ""

# 7. Résumé et recommandations
log "📋 Résumé et recommandations..."

if [ "$ALL_RUNNING" = true ]; then
    success "✅ Tous les services Docker sont en cours d'exécution"
else
    error "❌ Certains services Docker ne fonctionnent pas"
    echo ""
    echo "🔧 Actions recommandées:"
    echo "   1. Redémarrer les services: ./stop_all.sh && ./start_all.sh"
    echo "   2. Vérifier les logs: cd IA_Administratif && docker compose logs"
fi

echo ""
echo "🎯 Commandes de correction rapide:"
echo "   - Problèmes généraux: ./stop_all.sh && ./start_all.sh"
echo "   - Dépendances manquantes: cd IA_Administratif && docker compose exec backend pip install -r requirements.txt"
echo "   - Comptes utilisateurs: cd IA_Administratif && docker compose exec backend python scripts/load_fixtures_auto.py"
echo "   - psutil manquant: cd IA_Administratif && docker compose exec backend pip install psutil==6.1.0"
echo ""

cd "$LEXO_DIR"