# 🧪 Guide d'Exécution des Tests OCR Avancés

## 📁 Script de Test Principal

Le script `test_advanced_ocr.py` contient une suite complète de tests pour valider toutes les fonctionnalités OCR avancées implémentées.

## 🚀 Exécution des Tests

### Prérequis
```bash
# Naviguer vers le répertoire backend
cd /Users/stephaneansel/Documents/LEXO_v1/IA_Administratif/backend

# Activer l'environnement virtuel (si utilisé)
source venv/bin/activate

# Installer les dépendances manquantes si nécessaire
pip install -r requirements.txt
```

### Lancement des Tests Complets
```bash
# Exécuter tous les tests
python test_advanced_ocr.py

# Ou avec asyncio explicite
python -m asyncio test_advanced_ocr.py
```

### Tests Spécifiques avec pytest
```bash
# Si pytest est installé, tests individuels possibles
pytest test_advanced_ocr.py -v
```

## 📊 Résultats Attendus

### 🔍 Tests de Dépendances
- ✅ OpenCV, Pillow, Pytesseract (requis)
- ✅ Transformers, PyTorch (pour TrOCR)
- ✅ spaCy (pour extraction d'entités)
- ✅ Redis (pour cache)
- ⚠️ MLX (uniquement sur Apple Silicon)

### 📖 Tests OCR de Base
- ✅ Tesseract sur texte simple
- ✅ TrOCR (si transformers installé)
- ✅ Comparaison des performances

### 🔀 Tests OCR Hybride
- ✅ Stratégie TROCR_ONLY
- ✅ Stratégie TESSERACT_ONLY
- ✅ Stratégie TROCR_FALLBACK
- ✅ Stratégie BEST_CONFIDENCE
- ✅ Stratégie ENSEMBLE

### 📋 Tests LayoutLM
- ✅ Analyse de structure de document
- ✅ Détection de régions (titre, paragraphe, etc.)

### 📊 Tests Détection de Tableaux
- ✅ Détection sur image de tableau synthétique
- ✅ Extraction vers DataFrame pandas

### 🏷️ Tests Extraction d'Entités
- ✅ Détection SIRET, TVA, montants
- ✅ Extraction emails, téléphones, dates

### 🍎 Tests Apple Silicon
- ✅ Détection du matériel
- ✅ Optimisations MLX (si disponible)
- ✅ Metal Performance Shaders
- ✅ Benchmark de performance

### 💾 Tests Cache OCR
- ✅ Cache hybride (Redis + FileSystem)
- ✅ Performance cache hit/miss
- ✅ Statistiques de cache

## 📄 Rapport de Test

Le script génère automatiquement un rapport JSON complet :
```
test_report_ocr_advanced.json
```

Le rapport contient :
- Résultats détaillés par catégorie
- Temps d'exécution
- Recommandations d'amélioration
- Statistiques de performance

## 🔧 Dépannage

### Erreurs Communes

#### 1. Dépendances Manquantes
```bash
# Installer transformers
pip install transformers==4.46.3

# Installer spaCy + modèle français
pip install spacy==3.8.2
python -m spacy download fr_core_news_sm
```

#### 2. Redis Non Disponible
```bash
# Démarrer Redis (macOS avec Homebrew)
brew services start redis

# Ou Docker
docker run -d -p 6379:6379 redis:alpine
```

#### 3. Tesseract Non Trouvé
```bash
# macOS
brew install tesseract tesseract-lang

# Vérifier l'installation
tesseract --version
```

#### 4. Apple Silicon MLX
```bash
# Installer MLX sur Apple Silicon uniquement
pip install mlx
```

### Modes de Test Partiels

Si certaines dépendances manquent, le script s'adapte automatiquement :
- ❌ TrOCR manquant → Tests Tesseract uniquement
- ❌ Redis manquant → Cache FileSystem uniquement
- ❌ MLX manquant → Pas d'optimisations Apple Silicon

## 📈 Analyse des Performances

### Métriques Collectées
- **Temps de traitement** par moteur OCR
- **Précision** (confidence scores)
- **Débit** (mots/seconde)
- **Utilisation mémoire**
- **Accélération Apple Silicon**

### Benchmarks Typiques
- **Tesseract** : ~2-5 mots/sec
- **TrOCR** : ~1-3 mots/sec (plus précis)
- **Cache hit** : ~100x plus rapide
- **Apple Silicon** : 2-5x accélération selon la tâche

## 🎯 Prochaines Étapes

Après validation des tests :
1. **Corriger** les erreurs identifiées
2. **Optimiser** les performances lentes
3. **Compléter** les dépendances manquantes
4. **Intégrer** avec les endpoints API
5. **Déployer** en environnement de test

## 📞 Support

En cas de problème avec les tests :
1. Vérifier les logs dans le terminal
2. Consulter le rapport JSON généré
3. Tester les dépendances individuellement
4. Vérifier la configuration système

---

*Script créé le 23 Juillet 2025 - Tests pour Pipeline OCR Avancé LEXO v1*