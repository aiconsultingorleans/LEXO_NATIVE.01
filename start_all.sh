#!/bin/bash

# 🚀 LEXO v1 - Script de démarrage complet
# Démarre tous les services nécessaires pour LEXO v1
# Architecture: Docker (backend, frontend, db) + MLX natif

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
log "📁 Répertoire LEXO: $LEXO_DIR"

# 1. Vérification des prérequis
log "🔍 Vérification des prérequis..."

# Docker
if ! command -v docker &> /dev/null; then
    error "Docker n'est pas installé"
    exit 1
fi

# Docker Compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    error "Docker Compose n'est pas installé"
    exit 1
fi

# Python 3.11+
if ! command -v python3 &> /dev/null; then
    error "Python 3 n'est pas installé"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if [ "$(echo "$PYTHON_VERSION < 3.11" | bc)" -eq 1 ]; then
    error "Python 3.11+ requis (version actuelle: $PYTHON_VERSION)"
    exit 1
fi

success "✅ Prérequis vérifiés"

# 2. Nettoyage des processus zombies
log "🧹 Nettoyage des processus existants..."

# Arrêt des processus MLX existants
if pgrep -f "mlx_server" > /dev/null; then
    warning "Arrêt des processus MLX existants..."
    pkill -f "mlx_server" || true
    sleep 2
fi

# Vérification des ports
PORTS=(3000 8000 8001 8004 5432 6379 8080)
for PORT in "${PORTS[@]}"; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        warning "Port $PORT déjà utilisé, tentative de libération..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
done

# 3. Création des répertoires nécessaires
log "📁 Création des répertoires..."
mkdir -p "$LEXO_DIR/OCR"/{factures,impots,rib,non_classes}
mkdir -p "$LEXO_DIR/logs"
mkdir -p "$LEXO_DIR/data"/{postgres,redis,chromadb}
mkdir -p "$LEXO_DIR/training_dataset"

# 4. Configuration de l'environnement
log "🔧 Configuration de l'environnement..."

# Création du .env si absent
if [ ! -f "$LEXO_DIR/.env" ]; then
    warning "Création du fichier .env..."
    cat > "$LEXO_DIR/.env" << 'EOF'
# LEXO v1 - Configuration d'environnement

# Backend
BACKEND_PORT=8000
BACKEND_HOST=0.0.0.0
SECRET_KEY=your-secret-key-change-me-in-production
ENVIRONMENT=development

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000

# Database
POSTGRES_USER=lexo
POSTGRES_PASSWORD=lexo_password
POSTGRES_DB=lexo_db
DATABASE_URL=postgresql://lexo:lexo_password@localhost:5432/lexo_db

# Redis
REDIS_URL=redis://localhost:6379

# ChromaDB
CHROMA_PORT=8001
CHROMA_HOST=0.0.0.0

# MLX Service
MLX_PORT=8004
MLX_HOST=0.0.0.0
MLX_MODEL=mlx-community/Mistral-7B-Instruct-v0.3-4bit

# OCR Settings
OCR_CONFIDENCE_THRESHOLD=0.7
OCR_ENABLE_CACHE=true
OCR_CACHE_TTL=3600

# Monitoring
LOG_LEVEL=INFO
ENABLE_METRICS=true
EOF
    success "✅ Fichier .env créé"
fi

# Charger les variables d'environnement
export $(cat "$LEXO_DIR/.env" | grep -v '^#' | xargs)

# 5. Démarrage des services Docker
log "🐳 Démarrage des services Docker..."

# Vérifier que Docker est accessible
if ! docker info >/dev/null 2>&1; then
    error "Docker n'est pas accessible. Veuillez démarrer Docker Desktop."
    exit 1
fi

# Aller dans le répertoire IA_Administratif où se trouve docker-compose.yml
cd "$LEXO_DIR/IA_Administratif" || {
    error "Répertoire IA_Administratif non trouvé"
    exit 1
}

# Nettoyer les conteneurs en état incohérent
log "Nettoyage des conteneurs orphelins..."
docker compose down --remove-orphans 2>/dev/null || true
docker system prune -f --volumes 2>/dev/null || true

# Démarrer les services avec rebuild si nécessaire
log "Construction et démarrage des conteneurs..."
if ! docker compose up -d --build --force-recreate; then
    error "Échec du démarrage des services Docker"
    log "Tentative de diagnostic..."
    docker compose logs --tail=50
    exit 1
fi

# Retourner au répertoire principal
cd "$LEXO_DIR"

# Attendre que les services soient prêts
log "⏳ Attente du démarrage des services..."
TIMEOUT=90
ELAPSED=0

# Fonctions de vérification améliorées
check_docker_service() {
    local service_name=$1
    local container_name=$2
    
    cd "$LEXO_DIR/IA_Administratif"
    if docker compose ps --format "table {{.Service}}\t{{.State}}" | grep -q "$service_name.*running"; then
        return 0
    else
        return 1
    fi
}

check_service_health() {
    local url=$1
    local expected=$2
    
    if [ -n "$expected" ]; then
        curl -s --connect-timeout 3 --max-time 5 "$url" | grep -q "$expected" 2>/dev/null
    else
        curl -s --connect-timeout 3 --max-time 5 "$url" >/dev/null 2>&1
    fi
}

while [ $ELAPSED -lt $TIMEOUT ]; do
    # Vérifier les conteneurs Docker d'abord
    if check_docker_service "postgres" "lexo_postgres"; then
        # Puis vérifier la connectivité PostgreSQL
        cd "$LEXO_DIR/IA_Administratif"
        if docker compose exec -T postgres pg_isready -U lexo &> /dev/null; then
            PG_READY=true
        else
            PG_READY=false
        fi
    else
        PG_READY=false
    fi
    
    # Vérifier Redis
    if check_docker_service "redis" "lexo_redis"; then
        cd "$LEXO_DIR/IA_Administratif"
        if docker compose exec -T redis redis-cli ping | grep -q PONG &> /dev/null; then
            REDIS_READY=true
        else
            REDIS_READY=false
        fi
    else
        REDIS_READY=false
    fi
    
    # Vérifier Backend
    if check_docker_service "backend" "lexo_backend"; then
        if check_service_health "http://localhost:8000/api/v1/health" "healthy"; then
            BACKEND_READY=true
        else
            BACKEND_READY=false
        fi
    else
        BACKEND_READY=false
    fi
    
    # Vérifier Frontend
    if check_docker_service "frontend" "lexo_frontend"; then
        if check_service_health "http://localhost:3000" ""; then
            FRONTEND_READY=true
        else
            FRONTEND_READY=false
        fi
    else
        FRONTEND_READY=false
    fi
    
    # Vérifier ChromaDB
    if check_docker_service "chromadb" "lexo_chromadb"; then
        if check_service_health "http://localhost:8001/api/v2/version" ""; then
            CHROMA_READY=true
        else
            CHROMA_READY=false
        fi
    else
        CHROMA_READY=false
    fi
    
    if [ "$PG_READY" = true ] && [ "$REDIS_READY" = true ] && [ "$BACKEND_READY" = true ] && [ "$FRONTEND_READY" = true ] && [ "$CHROMA_READY" = true ]; then
        break
    fi
    
    sleep 3
    ELAPSED=$((ELAPSED + 3))
    echo -n "."
    
    # Afficher le statut tous les 15 secondes
    if [ $(($ELAPSED % 15)) -eq 0 ]; then
        echo ""
        log "Statut actuel: PG=$PG_READY, Redis=$REDIS_READY, Backend=$BACKEND_READY, Frontend=$FRONTEND_READY, Chroma=$CHROMA_READY"
    fi
done

echo ""
cd "$LEXO_DIR"

# Vérification finale des services Docker
if [ "$BACKEND_READY" = true ]; then
    success "✅ Backend API (port 8000)"
else
    error "❌ Backend API non accessible"
fi

if [ "$FRONTEND_READY" = true ]; then
    success "✅ Frontend Next.js (port 3000)"
else
    error "❌ Frontend non accessible"
fi

if [ "$PG_READY" = true ]; then
    success "✅ PostgreSQL (port 5432)"
else
    error "❌ PostgreSQL non prêt"
fi

if [ "$REDIS_READY" = true ]; then
    success "✅ Redis (port 6379)"
else
    error "❌ Redis non prêt"
fi

if [ "$CHROMA_READY" = true ]; then
    success "✅ ChromaDB (port 8001)"
else
    error "❌ ChromaDB non accessible"
fi

# 6. Démarrage du service MLX natif
log "🤖 Démarrage du service MLX natif..."

# Vérifier si MLX peut être utilisé
MLX_AVAILABLE=false
if [ -f "$LEXO_DIR/IA_Administratif/ai_services/document_analyzer.py" ]; then
    cd "$LEXO_DIR/IA_Administratif/ai_services"
    
    # Créer un environnement virtuel pour MLX si nécessaire
    if [ ! -d "venv" ]; then
        log "Création de l'environnement virtuel MLX..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        if pip install -r requirements.txt 2>/dev/null; then
            MLX_AVAILABLE=true
        else
            warning "Échec de l'installation des dépendances MLX"
        fi
        deactivate
    else
        # Vérifier que MLX est disponible dans le venv
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            if python -c "import mlx" 2>/dev/null; then
                MLX_AVAILABLE=true
            else
                warning "MLX non disponible dans l'environnement virtuel"
            fi
            deactivate
        fi
    fi
fi

if [ "$MLX_AVAILABLE" = true ]; then
    # Démarrer le service MLX natif
    cd "$LEXO_DIR/IA_Administratif/ai_services"
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        # Vérifier si le service n'est pas déjà en cours
        if ! curl -s http://localhost:8004/health >/dev/null 2>&1; then
            nohup python document_analyzer.py > "$LEXO_DIR/logs/mlx_server.log" 2>&1 &
            MLX_PID=$!
            
            # Sauvegarder le PID
            echo $MLX_PID > "$LEXO_DIR/IA_Administratif/pids/document_analyzer.pid"
            
            # Attendre que MLX soit prêt (jusqu'à 30 secondes)
            MLX_TIMEOUT=30
            while [ $MLX_TIMEOUT -gt 0 ]; do
                if curl -s http://localhost:8004/health | grep -q "healthy" 2>/dev/null; then
                    break
                fi
                sleep 1
                MLX_TIMEOUT=$((MLX_TIMEOUT - 1))
            done
            
            if curl -s http://localhost:8004/health | grep -q "healthy" 2>/dev/null; then
                success "✅ Service MLX (port 8004) - PID: $MLX_PID"
            else
                warning "⚠️  Service MLX démarré mais pas encore prêt - Vérifier logs/mlx_server.log"
            fi
        else
            success "✅ Service MLX déjà actif (port 8004)"
        fi
        deactivate
    else
        warning "Environnement virtuel MLX non trouvé"
    fi
else
    warning "⚠️  MLX n'est pas disponible - Service IA documentaire désactivé"
    warning "   Pour l'installer: cd IA_Administratif/ai_services && pip install mlx mlx-lm"
fi

cd "$LEXO_DIR"

# 7. Initialisation de la base de données
log "🗄️  Initialisation de la base de données..."
cd "$LEXO_DIR/IA_Administratif"
if [ "$BACKEND_READY" = true ]; then
    docker compose exec -T backend alembic upgrade head 2>/dev/null || warning "Migration déjà appliquée ou erreur"
    
    # Charger les fixtures si la base est vide
    if docker compose exec -T backend python -c "from app.models.user import User; from app.core.database import SessionLocal; db = SessionLocal(); print('Users:', db.query(User).count()); db.close()" 2>/dev/null | grep -q "Users: 0"; then
        log "Chargement des données de test..."
        docker compose exec -T backend python scripts/load_fixtures_auto.py 2>/dev/null || warning "Échec du chargement des fixtures"
    fi
else
    warning "Backend non disponible, migration de la base de données ignorée"
fi
cd "$LEXO_DIR"

# 8. Démarrage du watcher OCR (optionnel)
if [ -f "$LEXO_DIR/backend/app/services/ocr_watcher.py" ]; then
    log "👁️  Démarrage du watcher OCR..."
    cd "$LEXO_DIR/backend"
    if [ -d "venv" ]; then
        source venv/bin/activate
        nohup python app/services/ocr_watcher.py > "$LEXO_DIR/logs/ocr_watcher.log" 2>&1 &
        WATCHER_PID=$!
        echo $WATCHER_PID > "$LEXO_DIR/logs/ocr_watcher.pid"
        deactivate
        success "✅ Watcher OCR démarré - PID: $WATCHER_PID"
    fi
fi

# 9. Affichage du statut final
echo ""
log "🎉 LEXO v1 - Démarrage terminé!"
echo ""
echo "📊 Services disponibles:"
if [ "$FRONTEND_READY" = true ]; then
    echo "  ✅ Frontend:    http://localhost:3000"
else
    echo "  ❌ Frontend:    http://localhost:3000 (non accessible)"
fi

if [ "$BACKEND_READY" = true ]; then
    echo "  ✅ Backend API: http://localhost:8000"
    echo "  ✅ API Docs:    http://localhost:8000/docs"
else
    echo "  ❌ Backend API: http://localhost:8000 (non accessible)"
fi

if [ "$CHROMA_READY" = true ]; then
    echo "  ✅ ChromaDB:    http://localhost:8001"
else
    echo "  ❌ ChromaDB:    http://localhost:8001 (non accessible)"
fi

if [ "$PG_READY" = true ]; then
    echo "  ✅ Adminer:     http://localhost:8080"
else
    echo "  ❌ Adminer:     http://localhost:8080 (non accessible)"
fi

if curl -s http://localhost:8004/health | grep -q "healthy" 2>/dev/null; then
    echo "  ✅ MLX Service: http://localhost:8004"
else
    echo "  ❌ MLX Service: http://localhost:8004 (non accessible)"
fi
echo ""
echo "📁 Dossier OCR surveillé: $LEXO_DIR/OCR"
echo "📝 Logs disponibles dans: $LEXO_DIR/logs"
echo ""
echo "💡 Pour arrêter tous les services: ./stop_all.sh"
echo ""

# Ouvrir le navigateur (optionnel)
if [ "$1" != "--no-browser" ]; then
    sleep 2
    if command -v open &> /dev/null; then
        open http://localhost:3000
    fi
fi

# Vérification finale et message de statut
ALL_SERVICES_OK=true
if [ "$BACKEND_READY" != true ] || [ "$FRONTEND_READY" != true ] || [ "$PG_READY" != true ] || [ "$REDIS_READY" != true ] || [ "$CHROMA_READY" != true ]; then
    ALL_SERVICES_OK=false
fi

if [ "$ALL_SERVICES_OK" = true ]; then
    success "✅ Tous les services sont opérationnels!"
else
    warning "⚠️  Certains services ne sont pas accessibles"
    echo ""
    echo "Pour diagnostiquer:"
    echo "  - Logs Docker: cd IA_Administratif && docker compose logs"
    echo "  - Statut: cd IA_Administratif && docker compose ps"
    echo "  - Redémarrage: ./stop_all.sh && ./start_all.sh"
fi