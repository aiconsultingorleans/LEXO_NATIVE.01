#!/bin/bash

# 🛑 LEXO v1 - Script d'arrêt complet
# Arrête proprement tous les services LEXO v1
# Nettoie les processus, libère les ports et sauvegarde les états

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

# Fonction pour arrêter un processus par PID
stop_process_by_pid() {
    local PID_FILE=$1
    local SERVICE_NAME=$2
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            log "Arrêt de $SERVICE_NAME (PID: $PID)..."
            kill -TERM $PID 2>/dev/null || true
            
            # Attendre l'arrêt gracieux (max 10 secondes)
            TIMEOUT=10
            while [ $TIMEOUT -gt 0 ] && ps -p $PID > /dev/null 2>&1; do
                sleep 1
                TIMEOUT=$((TIMEOUT - 1))
            done
            
            # Force kill si nécessaire
            if ps -p $PID > /dev/null 2>&1; then
                warning "Force kill pour $SERVICE_NAME..."
                kill -9 $PID 2>/dev/null || true
            fi
            
            rm -f "$PID_FILE"
            success "✅ $SERVICE_NAME arrêté"
        else
            warning "$SERVICE_NAME n'était pas en cours d'exécution"
            rm -f "$PID_FILE"
        fi
    fi
}

# 1. Sauvegarde des statistiques et vérifications préalables
log "📊 Sauvegarde des statistiques..."
if curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    # Exporter les stats si l'API est disponible
    mkdir -p "$LEXO_DIR/backups/$(date +%Y%m%d)"
    curl -s http://localhost:8000/api/stats/export > "$LEXO_DIR/backups/$(date +%Y%m%d)/stats_$(date +%H%M%S).json" 2>/dev/null || true
    
    # Sauvegarder l'état des tâches batch en cours
    curl -s http://localhost:8000/api/v1/batch/status > "$LEXO_DIR/backups/$(date +%Y%m%d)/batch_status_$(date +%H%M%S).json" 2>/dev/null || true
    
    success "✅ Statistiques sauvegardées"
else
    warning "Backend non accessible, sauvegarde ignorée"
fi

# Vérifier s'il y a des traitements batch en cours
log "🔍 Vérification des traitements en cours..."
if curl -s http://localhost:8000/api/v1/batch/status 2>/dev/null | grep -q '"active_tasks": [1-9]'; then
    warning "⚠️  Des traitements batch sont en cours!"
    echo "Voulez-vous vraiment arrêter ? Les traitements seront interrompus. [y/N]"
    read -r CONFIRM
    if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
        echo "Arrêt annulé."
        exit 0
    fi
fi

# 2. Arrêt du watcher OCR
log "👁️  Arrêt du watcher OCR..."
stop_process_by_pid "$LEXO_DIR/logs/ocr_watcher.pid" "Watcher OCR"

# Arrêt par nom de processus au cas où
if pgrep -f "ocr_watcher.py" > /dev/null; then
    pkill -f "ocr_watcher.py" || true
    success "✅ Processus watcher OCR arrêtés"
fi

# 3. Arrêt du service MLX
log "🤖 Arrêt du service MLX..."
stop_process_by_pid "$LEXO_DIR/IA_Administratif/pids/document_analyzer.pid" "Service MLX"

# Arrêt par nom de processus
if pgrep -f "document_analyzer" > /dev/null; then
    pkill -f "document_analyzer" || true
    success "✅ Processus MLX arrêtés"
fi

# Vérifier le port 8004
if lsof -Pi :8004 -sTCP:LISTEN -t >/dev/null 2>&1; then
    warning "Port 8004 encore utilisé, libération forcée..."
    lsof -ti:8004 | xargs kill -9 2>/dev/null || true
fi

# 4. Arrêt des services Docker
log "🐳 Arrêt des services Docker..."

# Vérifier que Docker est accessible
if ! docker info >/dev/null 2>&1; then
    warning "Docker n'est pas accessible - arrêt des processus par PID seulement"
else
    # Aller dans le répertoire IA_Administratif
    if [ -f "$LEXO_DIR/IA_Administratif/docker-compose.yml" ]; then
        cd "$LEXO_DIR/IA_Administratif"
        
        # Arrêt gracieux des conteneurs
        log "Arrêt des conteneurs Docker..."
        docker compose stop --timeout 30 2>/dev/null || docker-compose stop --time 30 2>/dev/null || true
        
        # Attendre l'arrêt complet (max 45 secondes)
        TIMEOUT=45
        while [ $TIMEOUT -gt 0 ]; do
            RUNNING_CONTAINERS=$(docker compose ps -q 2>/dev/null | wc -l | tr -d ' ')
            if [ "$RUNNING_CONTAINERS" -eq 0 ]; then
                break
            fi
            sleep 1
            TIMEOUT=$((TIMEOUT - 1))
            echo -n "."
        done
        echo ""
        
        # Force l'arrêt des conteneurs récalcitrants
        REMAINING=$(docker compose ps -q 2>/dev/null | wc -l | tr -d ' ')
        if [ "$REMAINING" -gt 0 ]; then
            warning "Forçage de l'arrêt des conteneurs restants..."
            docker compose kill 2>/dev/null || true
            sleep 2
        fi
        
        # Suppression des conteneurs et nettoyage
        log "Suppression des conteneurs..."
        docker compose down --remove-orphans --volumes 2>/dev/null || docker-compose down --remove-orphans --volumes 2>/dev/null || true
        
        # Nettoyage des images orphelines
        log "Nettoyage des ressources Docker..."
        docker system prune -f 2>/dev/null || true
        
        success "✅ Services Docker arrêtés"
        
        cd "$LEXO_DIR"
    else
        warning "Fichier docker-compose.yml non trouvé dans IA_Administratif"
    fi
fi

# Nettoyage supplémentaire pour les conteneurs LEXO orphelins
log "Vérification des conteneurs LEXO orphelins..."
ORPHAN_CONTAINERS=$(docker ps -a --filter "name=lexo" --filter "name=ia_administratif" -q 2>/dev/null || true)
if [ -n "$ORPHAN_CONTAINERS" ]; then
    warning "Suppression des conteneurs orphelins..."
    echo $ORPHAN_CONTAINERS | xargs docker rm -f 2>/dev/null || true
fi

# 5. Nettoyage des processus orphelins
log "🧹 Nettoyage des processus orphelins..."

# Liste des processus à nettoyer
PROCESSES=("uvicorn" "gunicorn" "node" "next" "chromadb" "fastapi")

for PROC in "${PROCESSES[@]}"; do
    if pgrep -f "$PROC" > /dev/null; then
        warning "Arrêt des processus $PROC..."
        pkill -f "$PROC" 2>/dev/null || true
    fi
done

# 6. Libération des ports
log "🔓 Libération des ports..."

PORTS=(3000 8000 8001 8004 5432 6379 8080)
PORTS_FREED=0

for PORT in "${PORTS[@]}"; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log "Libération du port $PORT..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        PORTS_FREED=$((PORTS_FREED + 1))
        sleep 0.5
    fi
done

if [ $PORTS_FREED -gt 0 ]; then
    success "✅ $PORTS_FREED port(s) libéré(s)"
else
    success "✅ Tous les ports étaient déjà libres"
fi

# 7. Nettoyage des fichiers temporaires
log "🗑️  Nettoyage des fichiers temporaires..."

# Nettoyer les fichiers PID
rm -f "$LEXO_DIR/logs"/*.pid

# Nettoyer les fichiers temporaires Python
find "$LEXO_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$LEXO_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true

# Nettoyer les fichiers temporaires Node.js
rm -rf "$LEXO_DIR/.next/cache" 2>/dev/null || true

# 8. Vérification finale
log "🔍 Vérification finale..."

ALL_CLEAR=true

# Vérifier les conteneurs Docker
if docker info >/dev/null 2>&1; then
    ACTIVE_CONTAINERS=$(docker ps -q -f name=lexo -f name=ia_administratif 2>/dev/null | wc -l | tr -d ' ')
    if [ "$ACTIVE_CONTAINERS" -gt 0 ]; then
        error "❌ Des conteneurs Docker sont encore actifs:"
        docker ps --filter "name=lexo" --filter "name=ia_administratif" --format "table {{.Names}}\t{{.Status}}" 2>/dev/null || true
        ALL_CLEAR=false
    fi
else
    warning "Docker non accessible pour vérification finale"
fi

# Vérifier les ports
for PORT in "${PORTS[@]}"; do
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        error "❌ Le port $PORT est encore utilisé"
        ALL_CLEAR=false
    fi
done

# Vérifier les processus
if pgrep -f "document_analyzer\|ocr_watcher\|uvicorn.*lexo\|gunicorn.*lexo" > /dev/null; then
    error "❌ Des processus LEXO sont encore actifs"
    ALL_CLEAR=false
fi

# 9. Rapport final
echo ""
log "📋 LEXO v1 - Rapport d'arrêt"
echo ""

if [ "$ALL_CLEAR" = true ]; then
    success "✅ Tous les services ont été arrêtés proprement"
    echo ""
    echo "📊 Résumé:"
    echo "  - Services Docker: Arrêtés ✓"
    echo "  - Service MLX: Arrêté ✓"
    echo "  - Watcher OCR: Arrêté ✓"
    echo "  - Ports libérés: ${PORTS[*]}"
    echo "  - Fichiers temporaires: Nettoyés ✓"
    echo ""
    success "🎉 LEXO v1 est complètement arrêté!"
else
    warning "⚠️  Certains services n'ont pas pu être arrêtés complètement"
    echo ""
    echo "Vous pouvez forcer l'arrêt avec:"
    echo "  cd IA_Administratif && docker compose down --remove-orphans --volumes"
    echo "  docker ps -a | grep -E 'lexo|ia_administratif' | awk '{print \$1}' | xargs docker rm -f"
    echo "  lsof -ti:3000,8000,8001,8004,5432,6379,8080 | xargs kill -9"
    echo "  ./stop_all.sh --force  # (option forcée si implémentée)"
fi

echo ""
echo "💡 Pour redémarrer LEXO: ./start_all.sh"
echo ""

# Créer un fichier de statut
echo "stopped_at: $(date)" > "$LEXO_DIR/logs/lexo_status.log"

exit 0