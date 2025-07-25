# 🤖 CLAUDE.md - Guide Claude Code pour LEXO v1

## 📌 Contexte du Projet

Tu travailles sur **LEXO v1**, une application SaaS locale de gestion administrative intelligente utilisant OCR et RAG. L'objectif est d'automatiser complètement le traitement documentaire pour les professions libérales.

**Environnement cible :** macOS (Mac mini M4 - 32 Go RAM)  
**Architecture :** 100% locale avec capacités SaaS  
**Technologies principales :** Python, FastAPI, Next.js, ChromaDB, Mistral 7B MLX

## 🎯 Objectifs Principaux

1. **Automatiser** le scan et la classification de documents (OCR intelligent)
2. **Centraliser** l'information dans une base vectorielle (ChromaDB)
3. **Permettre** des requêtes en langage naturel via RAG
4. **Apprendre** continuellement des corrections utilisateur
5. **Sécuriser** toutes les données localement

## 🏗️ Architecture Technique

### Backend (Python 3.11+)
```
backend/
├── api/          # FastAPI endpoints
├── core/         # Business logic
├── models/       # SQLAlchemy models
├── ocr/          # Pipeline OCR
├── rag/          # ChromaDB + Mistral
└── utils/        # Helpers
```

### Frontend (Next.js 14+)
```
frontend/
├── components/   # React components
├── pages/        # Next.js pages
├── hooks/        # Custom hooks
├── store/        # Zustand state
└── styles/       # Tailwind CSS
```

### Stack Technologique
- **API** : FastAPI + PostgreSQL + Redis
- **Frontend** : Next.js + React + Tailwind CSS
- **OCR** : TrOCR + LayoutLMv3 + Tesseract
- **RAG** : ChromaDB + Mistral 7B MLX
- **Auth** : JWT + OAuth2
- **MCP Context7** une recherche dans une documentation à jour sera prioritaire en cas de doute.
- **Repo GitHub** : https://github.com/aiconsultingorleans/LEXO_v1
- **Projet Next.js** : le projet Next.js est dans le dossier `/src/`

## 📋 Fonctionnalités Prioritaires

### Phase 1 - MVP (En cours)
1. **Surveillance du dossier** `~/Documents/LEXO_v1/OCR`
2. **OCR basique** sur PDF et images
3. **Classification automatique** dans sous-dossiers
4. **Interface web** minimale
5. **Authentification** email/password

### Phase 2 - Beta
1. **RAG avec ChromaDB** pour recherche sémantique
2. **Dashboard** avec analytics
3. **Intégration Gmail** (OAuth2)
4. **Assistant IA** pour génération de documents

## 🛠️ Conventions de Code

### Python Backend
```python
# Structure des endpoints FastAPI
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> DocumentResponse:
    """Upload et traite un document."""
    pass

# Naming conventions
# Classes : PascalCase
# Functions : snake_case
# Constants : UPPER_SNAKE_CASE
# Private : _leading_underscore
```

### React/Next.js Frontend
```typescript
// Structure des composants
export const DocumentCard: FC<DocumentCardProps> = ({ 
  document, 
  onEdit, 
  onDelete 
}) => {
  // Hooks en premier
  const [isLoading, setIsLoading] = useState(false);
  
  // Logic
  
  // Render
  return (
    <div className="p-4 border rounded-lg">
      {/* Content */}
    </div>
  );
};

// Naming conventions
// Components : PascalCase
// Hooks : use prefix (useDocument)
// Utils : camelCase
// Types : PascalCase with suffix (DocumentType)
```

### Structure des Données
```typescript
interface Document {
  id: string;
  filename: string;
  category: DocumentCategory;
  dateDocument: Date;
  dateIndexation: Date;
  confidenceScore: number;
  entities: string[];
  amount?: number;
  customTags: string[];
  ocrText: string;
  embeddings?: number[];
}
```

## 🔧 Pipeline OCR

```python
# Pipeline recommandé
async def process_document(file_path: str) -> ProcessedDocument:
    # 1. Prétraitement
    image = preprocess_image(file_path)  # OpenCV
    
    # 2. Détection layout
    layout = detect_layout(image)  # LayoutLMv3
    
    # 3. OCR
    text = extract_text(image, layout)  # TrOCR + Tesseract fallback
    
    # 4. Extraction entités
    entities = extract_entities(text)  # NER
    logos = detect_logos(image)  # YOLO v8
    
    # 5. Classification
    category = classify_document(text, entities, logos)
    
    # 6. Indexation
    embeddings = generate_embeddings(text)  # Sentence Transformers
    
    return ProcessedDocument(
        text=text,
        category=category,
        entities=entities,
        embeddings=embeddings
    )
```

## 📁 Arborescence du Projet

```
~/Documents/LEXO_v1/
├── OCR/                         # 📁 Dossier surveillé pour upload documents
│   ├── ATTESTATION_Edf OA.pdf  # Fichiers de test
│   ├── Carte Rémi.pdf
│   └── Carte senior Remi .PNG
│
├── IA_Administratif/            # 🏗️ Projet principal (architecture Docker)
│   ├── ai_services/             # 🤖 Services IA MLX natifs
│   │   ├── document_analyzer.py # Service Mistral MLX (port 8004)
│   │   ├── requirements.txt
│   │   └── __init__.py
│   │
│   ├── backend/                 # 🐍 API FastAPI (port 8000)
│   │   ├── api/                 # Endpoints API
│   │   │   ├── auth.py          # Authentification JWT
│   │   │   ├── documents.py     # CRUD documents
│   │   │   ├── ocr_routes_simple.py  # OCR Tesseract
│   │   │   ├── ocr_routes.py    # OCR avancé (TrOCR, LayoutLM)
│   │   │   ├── document_intelligence.py  # Intégration Mistral
│   │   │   └── health.py        # Health checks
│   │   ├── core/                # Configuration
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── rate_limit.py
│   │   ├── models/              # Modèles SQLAlchemy
│   │   │   ├── user.py
│   │   │   └── document.py
│   │   ├── ocr/                 # Pipeline OCR
│   │   │   ├── tesseract_ocr.py
│   │   │   ├── trocr_ocr.py
│   │   │   ├── layoutlm_ocr.py
│   │   │   ├── hybrid_ocr.py
│   │   │   ├── image_preprocessor.py
│   │   │   ├── table_detector.py
│   │   │   ├── entity_extractor.py
│   │   │   └── ocr_cache.py
│   │   ├── alembic/             # Migrations DB
│   │   ├── fixtures/            # Données de test
│   │   ├── tests/               # Tests unitaires
│   │   └── main.py              # Point d'entrée FastAPI
│   │
│   ├── frontend/                # ⚛️ Interface Next.js (port 3000)
│   │   ├── src/
│   │   │   ├── app/             # Pages Next.js 14
│   │   │   │   ├── auth/        # Pages authentification
│   │   │   │   ├── dashboard/   # Dashboard principal
│   │   │   │   ├── admin/       # Interface admin
│   │   │   │   └── layout.tsx   # Layout racine
│   │   │   ├── components/      # Composants React
│   │   │   │   ├── auth/        # AuthGuard, ActivityTracker
│   │   │   │   ├── documents/   # DocumentUpload, DocumentsList
│   │   │   │   ├── layout/      # Header, Sidebar, MainLayout
│   │   │   │   └── ui/          # Button, Card, Input
│   │   │   ├── hooks/           # Hooks personnalisés
│   │   │   │   └── useAuth.ts
│   │   │   ├── stores/          # État global Zustand
│   │   │   │   └── authStore.ts
│   │   │   ├── lib/             # Utilitaires
│   │   │   └── types/           # Types TypeScript
│   │   ├── public/              # Assets statiques
│   │   ├── package.json
│   │   └── next.config.ts
│   │
│   ├── data/                    # 💾 Données persistantes Docker
│   │   ├── postgres/            # Données PostgreSQL
│   │   ├── redis/               # Cache Redis
│   │   └── chromadb/            # Base vectorielle
│   │
│   ├── config/                  # ⚙️ Configurations
│   ├── logs/                    # 📝 Logs applicatifs
│   ├── scripts/                 # 🛠️ Scripts utilitaires
│   ├── tests/                   # 🧪 Tests d'intégration
│   ├── ml_models/               # 🧠 Modèles ML téléchargés
│   │   ├── mistral_7b_mlx/      # Modèle Mistral pour MLX
│   │   ├── ocr_models/          # Modèles TrOCR, LayoutLM
│   │   └── embeddings/          # Modèles d'embeddings
│   │
│   ├── docker-compose.yml       # 🐳 Stack Docker complète
│   ├── start_document_analyzer.sh  # 🚀 Script démarrage MLX
│   ├── stop_document_analyzer.sh   # 🛑 Script arrêt MLX
│   └── README.md
│
├── src/                         # 📂 Composants dupliqués (legacy)
│   └── components/documents/    # ⚠️ À supprimer (dans IA_Administratif/frontend)
│
├── start_all.sh                 # 🚀 Script démarrage complet
├── stop_all.sh                  # 🛑 Script arrêt complet
├── CLAUDE.md                    # 📖 Ce guide
├── PLANNING.md                  # 🗓️ Roadmap projet
├── TACHES.md                    # ✅ Suivi des tâches
├── ARCHITECTURE_HYBRIDE_MISTRAL.md  # 🏗️ Doc architecture
│
└── tests_*.py                   # 🧪 Scripts de test divers
```

### Points Importants Navigation

1. **⚠️ Structure Hybride** : Projet principal dans `IA_Administratif/`
2. **Frontend Next.js** : Code dans `IA_Administratif/frontend/src/`
3. **Backend FastAPI** : Code dans `IA_Administratif/backend/`
4. **Services IA MLX** : Code dans `IA_Administratif/ai_services/`
5. **Docker Compose** : Stack dans `IA_Administratif/docker-compose.yml`
6. **Scripts Globaux** : `start_all.sh` et `stop_all.sh` à la racine

### Raccourcis Utiles

- **Pages Next.js** : `IA_Administratif/frontend/src/app/`
- **Composants React** : `IA_Administratif/frontend/src/components/`
- **API Backend** : `IA_Administratif/backend/api/`
- **Modèles DB** : `IA_Administratif/backend/models/`
- **Tests Backend** : `IA_Administratif/backend/tests/`
- **Services IA** : `IA_Administratif/ai_services/`
- **Pipeline OCR** : `IA_Administratif/backend/ocr/`
- **Configuration Docker** : `IA_Administratif/docker-compose.yml`

## ⚡ Commandes Utiles

```bash
# 🚀 DÉMARRAGE COMPLET (recommandé)
cd ~/Documents/LEXO_v1
./start_all.sh                    # Démarre toute l'infrastructure
./stop_all.sh                     # Arrête tout proprement

# 🐍 Backend FastAPI
cd ~/Documents/LEXO_v1/IA_Administratif/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# ⚛️ Frontend Next.js  
cd ~/Documents/LEXO_v1/IA_Administratif/frontend
npm install
npm run dev                       # http://localhost:3000

# 🤖 Service MLX (natif)
cd ~/Documents/LEXO_v1/IA_Administratif
./start_document_analyzer.sh     # Port 8004
./stop_document_analyzer.sh

# 🐳 Docker Stack
cd ~/Documents/LEXO_v1/IA_Administratif
docker-compose up -d             # Démarre PostgreSQL, Redis, ChromaDB
docker-compose down              # Arrête les services

# 📊 Base de données
cd ~/Documents/LEXO_v1/IA_Administratif/backend
alembic upgrade head             # Migrations
python scripts/load_fixtures_auto.py  # Données de test

# 🧪 Tests
cd ~/Documents/LEXO_v1/IA_Administratif/backend
pytest tests/                    # Tests unitaires
python test_ocr_pipeline.py      # Tests OCR
cd ~/Documents/LEXO_v1/IA_Administratif/frontend
npm run test                     # Tests frontend

# 🔧 Build production
cd ~/Documents/LEXO_v1/IA_Administratif/frontend
npm run build                    # Build Next.js
```

## 🧪 Tests Prioritaires

### Backend
1. **OCR** : Tester rotation, qualité faible, multi-pages
2. **Classification** : Vérifier précision > 90%
3. **API** : Auth, upload, search endpoints
4. **RAG** : Pertinence des résultats

### Frontend
1. **Upload** : Drag & drop, progress, erreurs
2. **Dashboard** : Chargement des données
3. **Search** : Filtres et résultats
4. **Responsive** : Mobile, tablet, desktop

## 🐛 Problèmes Connus

1. **OCR sur PDF scannés** : Utiliser pdf2image avant OCR
2. **Performance ChromaDB** : Batch les embeddings
3. **Mémoire Mistral** : Utiliser quantization 4-bit
4. **CORS Next.js** : Configurer dans next.config.js

## 📊 Métriques à Suivre

- **Précision OCR** : Log confidence scores
- **Temps de traitement** : Timer chaque étape
- **Taux de classification** : Track corrections
- **Usage mémoire** : Monitor avec psutil

## 🔐 Sécurité

1. **Jamais de secrets dans le code**
2. **Utiliser .env pour config**
3. **Chiffrer documents sensibles**
4. **Valider tous les inputs**
5. **Rate limiting sur API**

## 💡 Tips pour Claude Code

### Pour l'OCR
- Toujours prétraiter les images (deskew, denoise)
- Utiliser plusieurs modèles et voter
- Garder l'image originale

### Pour le RAG
- Chunker intelligemment (paragraphes complets)
- Ajouter métadonnées aux embeddings
- Utiliser hybrid search (dense + sparse)

### Pour l'UI
- Mobile-first avec Tailwind
- Skeleton loaders partout
- Feedback utilisateur immédiat
- Animations subtiles (framer-motion)

### Pour la Performance
- Lazy loading des composants
- Virtualisation des listes longues
- Cache Redis pour requêtes fréquentes
- Workers pour tâches lourdes

## 🚀 Prochaines Étapes

1. **Finaliser MVP** : OCR + classification basique
2. **Intégrer ChromaDB** : Setup RAG pipeline
3. **Améliorer UI** : Dashboard complet
4. **Tests utilisateurs** : Feedback sur classification
5. **Optimiser performance** : Profiling Python

## 📝 Notes Importantes

- **Local-first** : Tout doit fonctionner offline
- **Privacy** : Aucune donnée ne sort du Mac
- **UX simple** : L'utilisateur ne doit rien configurer
- **Apprentissage** : Le système s'améliore avec l'usage
- **Robustesse** : Gérer tous les cas d'erreur
- **Journal** : les nouvelles fonctionalités et états de progression devront être ajoutés au fichier JOURNAL.md

## 🚀 Démarrage Optimisé (Janvier 2025)

### **Performance de Démarrage**
- **Temps total** : ~90 secondes (amélioration de 65% vs version initiale)
- **API disponible** : ~30 secondes après `./start_all.sh`
- **OCR prêt** : Chargement à la demande (lazy loading)

### **Architecture de Démarrage Rapide**
```bash
# 1. Cache ML Local (ZÉRO téléchargement)
ml_models/
├── transformers/
│   ├── trocr-base-printed/          # 1.2GB (OCR principal)
│   └── paraphrase-multilingual-MiniLM-L12-v2/  # 457MB (RAG)
└── spacy/ (optionnel)

# 2. Variables d'environnement critiques
HF_OFFLINE=1                    # Force cache local uniquement
TRANSFORMERS_OFFLINE=1          # Pas de téléchargement HuggingFace
local_files_only=True          # Configuration TrOCR stricte
```

### **Lazy Loading OCR**
- **Au démarrage** : API FastAPI prête, OCR **NON initialisé**
- **Premier document** : OCR s'initialise automatiquement (~30s)
- **Documents suivants** : Traitement immédiat (<5s)

### **Migration des Modèles (1ère fois)**
```bash
# Migrer depuis cache système vers cache local
cd IA_Administratif/scripts
python migrate_models_to_local_cache.py

# Valider la migration
python validate_models_cache.py --verbose

# Vérifier l'état OCR
curl http://localhost:8000/api/v1/health/ocr
```

### **Monitoring du Démarrage**
- `/api/v1/health` : Santé générale de l'API
- `/api/v1/health/ocr` : État des moteurs OCR (initialisés ou non)
- `/api/v1/watcher/status` : Statut du surveillance du dossier OCR

## 🔗 Ressources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js 14 Docs](https://nextjs.org/docs)
- [ChromaDB Guide](https://docs.trychroma.com/)
- [MLX Examples](https://github.com/ml-explore/mlx-examples)
- [TrOCR Paper](https://arxiv.org/abs/2109.10282)

---

**Rappel :** Ce projet vise à simplifier radicalement la gestion administrative. Chaque décision technique doit servir cet objectif. Si une fonctionnalité complique l'expérience utilisateur, elle doit être repensée ou supprimée.

**Philosophie :** "It just works" - L'utilisateur dépose un document, LEXO fait le reste.