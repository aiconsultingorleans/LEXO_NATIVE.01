#!/bin/bash

# 🔍 Script de vérification des modèles ML pour LEXO v1
# Vérifie que tous les modèles sont disponibles avant démarrage

set -e

# Couleurs pour les logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[CHECK]${NC} $1"
}

success() {
    echo -e "${GREEN}[✅]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[⚠️]${NC} $1"
}

error() {
    echo -e "${RED}[❌]${NC} $1"
}

# Répertoire de base
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ML_MODELS_DIR="$PROJECT_DIR/ml_models"

log "Vérification des modèles ML pour LEXO v1"
log "Répertoire projet: $PROJECT_DIR"

# Vérifier la structure des répertoires
log "📁 Vérification de la structure des répertoires..."

REQUIRED_DIRS=(
    "$ML_MODELS_DIR"
    "$ML_MODELS_DIR/transformers"
    "$ML_MODELS_DIR/spacy"
    "$ML_MODELS_DIR/mistral_7b_mlx"
)

DIRS_OK=true
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        success "Répertoire trouvé: $(basename "$dir")"
    else
        error "Répertoire manquant: $dir"
        DIRS_OK=false
    fi
done

if [ "$DIRS_OK" = false ]; then
    warning "Création des répertoires manquants..."
    mkdir -p "${REQUIRED_DIRS[@]}"
fi

# Vérifier les modèles HuggingFace
log "🤗 Vérification du cache HuggingFace..."

HF_CACHE="$HOME/.cache/huggingface/hub"
if [ -d "$HF_CACHE" ]; then
    # Compter les modèles dans le cache
    MODEL_COUNT=$(find "$HF_CACHE" -name "models--*" -type d | wc -l)
    if [ "$MODEL_COUNT" -gt 0 ]; then
        success "Cache HuggingFace: $MODEL_COUNT modèles trouvés"
        
        # Vérifier les modèles spécifiques
        TROCR_FOUND=false
        EMBEDDINGS_FOUND=false
        MISTRAL_FOUND=false
        
        if [ -d "$HF_CACHE/models--microsoft--trocr-base-printed" ]; then
            success "TrOCR: microsoft/trocr-base-printed ✅"
            TROCR_FOUND=true
        else
            error "TrOCR: microsoft/trocr-base-printed ❌"
        fi
        
        if [ -d "$HF_CACHE/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2" ]; then
            success "Embeddings: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 ✅"
            EMBEDDINGS_FOUND=true
        else
            error "Embeddings: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 ❌"
        fi
        
        if [ -d "$HF_CACHE/models--mlx-community--Mistral-7B-Instruct-v0.3-4bit" ]; then
            success "Mistral MLX: mlx-community/Mistral-7B-Instruct-v0.3-4bit ✅"
            MISTRAL_FOUND=true
        else
            warning "Mistral MLX: mlx-community/Mistral-7B-Instruct-v0.3-4bit ❌"
        fi
        
    else
        warning "Cache HuggingFace vide"
    fi
else
    error "Cache HuggingFace non trouvé: $HF_CACHE"
fi

# Vérifier spaCy
log "🔤 Vérification des modèles spaCy..."

if command -v python3 &> /dev/null; then
    # Tester si spaCy et le modèle français sont disponibles
    if python3 -c "import spacy; spacy.load('fr_core_news_sm'); print('spaCy français OK')" 2>/dev/null; then
        success "spaCy: fr_core_news_sm ✅"
    else
        error "spaCy: fr_core_news_sm ❌"
        warning "Pour installer: python -m spacy download fr_core_news_sm"
    fi
else
    error "Python3 non trouvé"
fi

# Vérifier MLX (Apple Silicon seulement)
log "🍎 Vérification de MLX (Apple Silicon)..."

if [[ $(uname -m) == "arm64" ]]; then
    if python3 -c "import mlx.core; print('MLX OK')" 2>/dev/null; then
        success "MLX: Disponible ✅"
    else
        warning "MLX: Non installé ❌"
        warning "Pour installer: pip install mlx-lm"
    fi
else
    warning "MLX: Non supporté sur cette architecture ($(uname -m))"
fi

# Calculer les tailles des caches
log "📊 Tailles des caches..."

calculate_size() {
    local dir="$1"
    if [ -d "$dir" ]; then
        local size=$(du -sh "$dir" 2>/dev/null | cut -f1)
        echo "$size"
    else
        echo "0B"
    fi
}

HF_SIZE=$(calculate_size "$HF_CACHE")
TRANSFORMERS_SIZE=$(calculate_size "$ML_MODELS_DIR/transformers")
SPACY_SIZE=$(calculate_size "$ML_MODELS_DIR/spacy")
MLX_SIZE=$(calculate_size "$ML_MODELS_DIR/mistral_7b_mlx")

log "Cache HuggingFace global: $HF_SIZE ($HF_CACHE)"
log "Cache Transformers local: $TRANSFORMERS_SIZE ($ML_MODELS_DIR/transformers)"
log "Cache spaCy local: $SPACY_SIZE ($ML_MODELS_DIR/spacy)"
log "Cache MLX local: $MLX_SIZE ($ML_MODELS_DIR/mistral_7b_mlx)"

# Recommandations
log "💡 Recommandations..."

if [ "$TROCR_FOUND" = false ] || [ "$EMBEDDINGS_FOUND" = false ]; then
    warning "Modèles manquants détectés"
    warning "Exécutez: python3 scripts/download_models.py"
fi

if [ ! -s "$ML_MODELS_DIR/transformers" ]; then
    warning "Cache local vide - Les modèles seront téléchargés au premier démarrage"
    warning "Pour pré-télécharger: python3 scripts/download_models.py"
fi

log "✅ Vérification terminée"

# Afficher le temps de démarrage estimé
if [ "$TROCR_FOUND" = true ] && [ "$EMBEDDINGS_FOUND" = true ]; then
    success "🚀 Démarrage rapide: ~30 secondes"
else
    warning "⏱️  Premier démarrage: ~3-5 minutes (téléchargement)"
fi