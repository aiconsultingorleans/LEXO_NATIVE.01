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

## 📁 Structure des Fichiers

```
~/Documents/LEXO_v1/
├── OCR/                    # Dossier surveillé
│   ├── factures/          # Auto-classé
│   ├── impots/           
│   ├── rib/              
│   └── non_classes/       # En attente
│
└── IA_Administratif/       # Application
    ├── backend/
    ├── frontend/
    ├── ml_models/
    └── data/
```

## ⚡ Commandes Utiles

```bash
# Backend
cd ~/Documents/LEXO_v1/IA_Administratif/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd ~/Documents/LEXO_v1/IA_Administratif/frontend
npm install
npm run dev

# Tests
pytest backend/tests/
npm run test

# Docker (dev)
docker-compose up -d

# Migrations DB
alembic upgrade head
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

## 🔗 Ressources

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [Next.js 14 Docs](https://nextjs.org/docs)
- [ChromaDB Guide](https://docs.trychroma.com/)
- [MLX Examples](https://github.com/ml-explore/mlx-examples)
- [TrOCR Paper](https://arxiv.org/abs/2109.10282)

---

**Rappel :** Ce projet vise à simplifier radicalement la gestion administrative. Chaque décision technique doit servir cet objectif. Si une fonctionnalité complique l'expérience utilisateur, elle doit être repensée ou supprimée.

**Philosophie :** "It just works" - L'utilisateur dépose un document, LEXO fait le reste.