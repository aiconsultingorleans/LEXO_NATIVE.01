# 🏗️ Architecture Hybride LEXO v1 - Intégration Mistral MLX

## 📋 Vue d'Ensemble

Cette architecture hybride permet d'intégrer **Mistral 7B MLX** dans le pipeline d'analyse documentaire de LEXO v1, en contournant la limitation Docker/GPU sur Apple Silicon.

## 🎯 Objectif

Combiner le **pipeline OCR existant** (Tesseract + TrOCR) avec l'**analyse sémantique avancée** de Mistral MLX pour créer un système d'intelligence documentaire complet.

## 🏗️ Architecture Technique

```
🔄 ARCHITECTURE HYBRIDE LEXO v1
├── 🐳 DOCKER LAYER (Production Ready)
│   ├── ✅ PostgreSQL (port 5432) : Base de données
│   ├── ✅ Redis (port 6379) : Cache et sessions  
│   ├── ✅ Backend FastAPI (port 8000) : API + OCR + Proxy MLX
│   ├── ✅ Frontend Next.js (port 3000) : Interface utilisateur
│   └── ✅ Adminer (port 8080) : Interface DB
│
└── 🖥️ NATIVE MLX LAYER (Analyse IA)
    ├── 📄 Document Analyzer Service (port 8004) : Service MLX natif
    ├── 🤖 Mistral 7B MLX : LLM local Apple Silicon
    ├── 🧠 Analyse sémantique de documents
    └── 📊 Classification et extraction intelligente
```

## 📦 Composants Créés

### 1. 🔍 **Service MLX Natif** (`ai_services/document_analyzer.py`)

**Fonctionnalités :**
- ✅ Classification automatique de documents (facture, RIB, contrat, etc.)
- ✅ Extraction d'informations clés (dates, montants, personnes, entreprises)
- ✅ Résumé intelligent de documents
- ✅ Analyse de conformité documentaire
- ✅ API FastAPI native sur port 8004

**Types de documents supportés :**
- `facture` : Factures commerciales
- `rib` : Relevés d'identité bancaire
- `contrat` : Contrats et conventions
- `attestation` : Attestations diverses
- `courrier` : Correspondances
- `rapport` : Rapports et études
- `autre` : Documents non classifiés

### 2. 🔗 **API Proxy** (`backend/api/document_intelligence.py`)

**Fonctionnalités :**
- ✅ Proxy HTTP vers le service MLX natif
- ✅ Authentification JWT intégrée
- ✅ Gestion d'erreurs et timeouts
- ✅ Health checks automatiques
- ✅ Endpoints RESTful dans le backend Docker

### 3. 🚀 **Scripts de Démarrage**

- `start_document_analyzer.sh` : Démarre le service MLX natif
- `stop_document_analyzer.sh` : Arrête le service proprement
- `test_hybrid_document_analysis.py` : Tests complets de l'architecture

## 🚀 Installation et Démarrage

### Prérequis

```bash
# 1. MLX Framework (Apple Silicon uniquement)
pip install mlx mlx-lm

# 2. FastAPI pour le service natif
pip install fastapi uvicorn pydantic

# 3. httpx pour les requêtes HTTP
pip install httpx
```

### Démarrage de l'Architecture Hybride

```bash
# 1. Démarrer l'infrastructure Docker
cd IA_Administratif
docker-compose up -d

# 2. Démarrer le service MLX natif
./start_document_analyzer.sh

# 3. Vérifier que tout fonctionne
python ../test_hybrid_document_analysis.py
```

## 📡 Endpoints API

### Service MLX Natif (Port 8004)

```http
# Health check
GET http://127.0.0.1:8004/health

# Analyse de document
POST http://127.0.0.1:8004/analyze
Content-Type: application/json
{
  "text": "Texte du document à analyser",
  "analysis_types": ["classification", "key_extraction", "summarization"],
  "document_context": "Contexte optionnel"
}

# Types supportés
GET http://127.0.0.1:8004/document-types
GET http://127.0.0.1:8004/analysis-types

# Documentation Swagger
GET http://127.0.0.1:8004/docs
```

### Backend Docker (Port 8000)

```http
# Intelligence documentaire via proxy
GET http://localhost:8000/api/v1/intelligence/health
POST http://localhost:8000/api/v1/intelligence/analyze
GET http://localhost:8000/api/v1/intelligence/supported-types

# Pipeline OCR traditionnel
GET http://localhost:8000/api/v1/ocr/health
POST http://localhost:8000/api/v1/ocr/preprocess
POST http://localhost:8000/api/v1/ocr/process
```

## 🔄 Pipeline Complet

### Scénario d'Utilisation : Analyse d'une Facture

```python
# 1. Upload du fichier PDF/PNG
# 2. OCR avec Tesseract/TrOCR (Docker)
# 3. Analyse sémantique avec Mistral MLX (Natif)
# 4. Retour des résultats combinés

# Exemple de réponse hybride :
{
  "ocr_result": {
    "text": "FACTURE N° 2024-001...",
    "confidence": 0.92,
    "processing_time": 4.1
  },
  "analysis_result": {
    "document_type": "facture",
    "confidence": 0.95,
    "key_information": {
      "dates": ["2024-01-15"],
      "montants": ["1500.00 €", "300.00 €", "1800.00 €"],
      "entreprises": ["ABC SARL"],
      "personnes": ["Jean Dupont"]
    },
    "summary": "Facture de conseil émise par ABC SARL pour 1800€ TTC"
  }
}
```

## 📊 Performance Attendue

| Composant | Temps de traitement | Précision |
|-----------|-------------------|-----------|
| **OCR Tesseract** | 2-5s | 85-92% |
| **Analyse MLX** | 1-3s | 90-95% |
| **Pipeline complet** | 3-8s | 88-94% |

## 🐛 Résolution de Problèmes

### Service MLX ne démarre pas

```bash
# Vérifier MLX
python -c "import mlx.core, mlx_lm; print('MLX OK')"

# Vérifier le port
lsof -i :8004

# Consulter les logs
tail -f logs/document_analyzer.log
```

### Erreur de communication Docker ↔ MLX

```bash
# Vérifier la connectivité
curl http://127.0.0.1:8004/health

# Tester le proxy
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/v1/intelligence/health
```

### Performance dégradée

- ✅ Vérifier que le Mac utilise la puce M1/M2/M3/M4
- ✅ S'assurer que Mistral MLX utilise le GPU Metal
- ✅ Réduire `max_tokens` dans la config si nécessaire

## 🔧 Configuration Avancée

### Personnaliser les Prompts

Modifier `ai_services/document_analyzer.py` section `self.prompts` pour adapter les instructions Mistral à vos besoins spécifiques.

### Optimisation Apple Silicon

Le service détecte automatiquement la puce Apple et optimise les performances MLX en conséquence.

## 🎯 Prochaines Étapes

1. **Intégration OCR+MLX** : Créer le pipeline end-to-end
2. **Interface utilisateur** : Ajouter l'analyse MLX dans le frontend
3. **Cache intelligent** : Optimiser avec Redis
4. **Modèles spécialisés** : Fine-tuning Mistral pour les documents métier

## 📚 Ressources

- [MLX Framework](https://github.com/ml-explore/mlx)
- [Mistral 7B MLX](https://huggingface.co/mlx-community/Mistral-7B-Instruct-v0.3-4bit)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

---

**🎉 Architecture Hybride LEXO v1 - Prête pour Production**

*Dernière mise à jour : Janvier 2025*