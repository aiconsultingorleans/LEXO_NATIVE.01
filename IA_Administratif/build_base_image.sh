#!/bin/bash

# 🏗️ LEXO v1 - Script de build intelligent pour l'image de base
# Compile spaCy et les dépendances ML lourdes une seule fois
# Usage: ./build_base_image.sh [--force]

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Variables
IMAGE_NAME="lexo-base"
IMAGE_TAG="latest"
DOCKERFILE_BASE="backend/Dockerfile.base"
REQUIREMENTS_FILE="backend/requirements-minimal.txt"

# Vérifier le répertoire
cd "$(dirname "$0")"
SCRIPT_DIR=$(pwd)
log "📁 Répertoire: $SCRIPT_DIR"

# Vérifier que les fichiers nécessaires existent
if [ ! -f "$DOCKERFILE_BASE" ]; then
    error "Dockerfile.base non trouvé: $DOCKERFILE_BASE"
    exit 1
fi

if [ ! -f "$REQUIREMENTS_FILE" ]; then
    error "Fichier requirements non trouvé: $REQUIREMENTS_FILE"
    exit 1
fi

# Fonction pour vérifier si l'image existe et est récente
check_base_image() {
    if docker image inspect "$IMAGE_NAME:$IMAGE_TAG" >/dev/null 2>&1; then
        # Image existe, vérifier sa date
        IMAGE_DATE=$(docker image inspect "$IMAGE_NAME:$IMAGE_TAG" --format='{{.Created}}')
        REQUIREMENTS_DATE=$(stat -f%m "$REQUIREMENTS_FILE" 2>/dev/null || stat -c%Y "$REQUIREMENTS_FILE" 2>/dev/null)
        
        # Convertir les dates pour comparaison (approximative)
        if [ -n "$IMAGE_DATE" ] && [ -n "$REQUIREMENTS_DATE" ]; then
            log "✅ Image de base trouvée: $IMAGE_NAME:$IMAGE_TAG"
            log "   Créée: $IMAGE_DATE"
            return 0
        fi
    fi
    return 1
}

# Fonction pour construire l'image de base
build_base_image() {
    log "🏗️ Construction de l'image de base avec spaCy..."
    log "   Cela peut prendre 5-8 minutes la première fois"
    
    # Estimer le temps
    START_TIME=$(date +%s)
    
    # Build avec progress et cache
    if docker build \
        -f "$DOCKERFILE_BASE" \
        -t "$IMAGE_NAME:$IMAGE_TAG" \
        --progress=plain \
        --no-cache=$([[ "$1" == "--force" ]] && echo "true" || echo "false") \
        backend/; then
        
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        MINUTES=$((DURATION / 60))
        SECONDS=$((DURATION % 60))
        
        success "✅ Image de base construite avec succès!"
        success "   Durée: ${MINUTES}m ${SECONDS}s"
        success "   Image: $IMAGE_NAME:$IMAGE_TAG"
        
        # Vérifier que spaCy fonctionne
        log "🧪 Test de spaCy dans l'image..."
        if docker run --rm "$IMAGE_NAME:$IMAGE_TAG" python -c "import spacy; nlp = spacy.load('fr_core_news_sm'); print('✅ spaCy opérationnel')"; then
            success "✅ spaCy fonctionne correctement dans l'image"
        else
            warning "⚠️ Problème avec spaCy dans l'image"
        fi
        
        return 0
    else
        error "❌ Échec de construction de l'image de base"
        return 1
    fi
}

# Afficher les informations
log "🚀 LEXO v1 - Build de l'image de base optimisée"
log "   Image cible: $IMAGE_NAME:$IMAGE_TAG"
log "   Dockerfile: $DOCKERFILE_BASE"

# Vérifier les arguments
FORCE_BUILD=false
if [ "$1" == "--force" ]; then
    FORCE_BUILD=true
    warning "🔄 Mode force activé - reconstruction complète"
fi

# Vérifier si l'image existe déjà
if [ "$FORCE_BUILD" = false ] && check_base_image; then
    log "✅ Image de base déjà disponible et récente"
    log "   Pour forcer la reconstruction: $0 --force"
    
    # Proposer de continuer avec docker-compose
    echo ""
    log "💡 Étapes suivantes:"
    echo "   1. docker-compose up -d --build (pour utiliser l'image de base)"
    echo "   2. Le backend démarrera rapidement (~30 secondes)"
    echo ""
    exit 0
fi

# Construire l'image de base
if build_base_image "$1"; then
    echo ""
    log "🎉 Image de base prête!"
    echo ""
    log "💡 Étapes suivantes:"
    echo "   1. docker-compose up -d --build"
    echo "   2. Le backend utilisera l'image pré-compilée (démarrage rapide)"
    echo ""
    log "📊 Avantages obtenus:"
    echo "   ✅ spaCy compilé une seule fois"
    echo "   ✅ Builds futurs: ~30 secondes au lieu de 5-8 minutes"
    echo "   ✅ Cache persistant entre redémarrages"
    echo ""
else
    error "❌ Échec de construction de l'image de base"
    exit 1
fi