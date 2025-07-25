#!/bin/bash

# 🔍 Script de vérification du cache spaCy persistant

echo "🔍 Vérification du cache LEXO..."
echo ""

# Vérifier l'image de base
if docker image inspect lexo-base:latest >/dev/null 2>&1; then
    IMAGE_SIZE=$(docker images lexo-base:latest --format "table {{.Size}}" | tail -n 1)
    IMAGE_DATE=$(docker image inspect lexo-base:latest --format='{{.Created}}' | cut -d'T' -f1)
    echo "✅ Image de base spaCy disponible"
    echo "   Taille: $IMAGE_SIZE"
    echo "   Créée: $IMAGE_DATE"
else
    echo "❌ Image de base manquante - recompilation nécessaire"
fi

echo ""

# Vérifier le volume Python
if docker volume inspect ia_administratif_python_cache >/dev/null 2>&1; then
    echo "✅ Volume Python cache disponible"
    VOLUME_PATH=$(docker volume inspect ia_administratif_python_cache --format='{{.Mountpoint}}')
    echo "   Chemin: $VOLUME_PATH"
else
    echo "❌ Volume Python cache manquant"
fi

echo ""

# Estimer le temps de démarrage
if docker image inspect lexo-base:latest >/dev/null 2>&1; then
    echo "⚡ Prochain démarrage estimé: ~30 secondes"
else
    echo "⏱️ Prochain démarrage estimé: ~5 minutes (recompilation)"
fi

echo ""
echo "💡 Pour forcer la recompilation: ./build_base_image.sh --force"