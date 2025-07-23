# 📅 PLANNING.md - Feuille de Route Technique LEXO v1

## 🎯 Vision Produit

### Mission
Transformer radicalement la gestion administrative des professions libérales en créant un assistant IA local qui automatise 80% des tâches documentaires répétitives.

### Vision à 3 ans
Devenir la référence en matière de gestion documentaire intelligente pour les indépendants francophones, avec une base de 10 000+ utilisateurs actifs et un écosystème de plugins communautaires.

### Principes Directeurs
1. **Local-First** : Sécurité et confidentialité absolues
2. **Zero-Config** : Fonctionne immédiatement après installation
3. **Intelligence Adaptative** : Apprend des habitudes de chaque utilisateur
4. **Design Invisible** : L'interface disparaît derrière l'efficacité
5. **Performance Native** : Exploitation maximale du hardware Apple

---

## 🏗️ Architecture Système

### Vue d'Ensemble
```mermaid
graph TB
    subgraph "Client Layer"
        UI[Next.js Frontend]
        CLI[CLI Tools]
    end
    
    subgraph "API Layer"
        API[FastAPI Backend]
        WS[WebSocket Server]
    end
    
    subgraph "Processing Layer"
        OCR[OCR Pipeline]
        CLASS[Classifier]
        NLP[NLP Engine]
        VOICE[Voice Module]
    end
    
    subgraph "Data Layer"
        PG[(PostgreSQL)]
        CHROMA[(ChromaDB)]
        REDIS[(Redis)]
        FS[File System]
    end
    
    subgraph "ML Layer"
        MISTRAL[Mistral 7B]
        EMBED[Embeddings]
        MODELS[OCR Models]
    end
    
    UI --> API
    CLI --> API
    API --> WS
    API --> OCR
    API --> CLASS
    API --> NLP
    API --> VOICE
    OCR --> MODELS
    CLASS --> MISTRAL
    NLP --> MISTRAL
    NLP --> EMBED
    API --> PG
    API --> CHROMA
    API --> REDIS
    OCR --> FS
```

### Architecture Détaillée

#### 1. **Couche Présentation**
- **Web App** : Interface principale (Next.js)
- **CLI** : Outils ligne de commande pour automatisation
- **API REST** : Endpoints pour intégrations tierces
- **WebSocket** : Updates temps réel

#### 2. **Couche Métier**
- **Document Processor** : Pipeline de traitement unifié
- **Classification Engine** : ML pour catégorisation auto
- **RAG System** : Recherche et génération de réponses
- **Task Scheduler** : Automatisation des tâches récurrentes

#### 3. **Couche Données**
- **PostgreSQL** : Métadonnées et relations
- **ChromaDB** : Embeddings vectoriels
- **Redis** : Cache et queues
- **File System** : Stockage documents originaux

#### 4. **Couche ML/IA**
- **Mistral 7B MLX** : LLM principal
- **OCR Models** : TrOCR, LayoutLM, Tesseract
- **Embeddings** : Sentence Transformers
- **Voice Models** : STT/TTS (Phase 2)

---

## 💻 Stack Technologique Complète

### Backend
| Catégorie | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **Langage** | Python | 3.11+ | Performance, écosystème ML |
| **Framework** | FastAPI | 0.109+ | Async, performance, OpenAPI |
| **ORM** | SQLAlchemy | 2.0+ | Flexibilité, async support |
| **Migration** | Alembic | 1.13+ | Versioning DB robuste |
| **Validation** | Pydantic | 2.5+ | Type safety, serialization |
| **Auth** | Python-Jose | 3.3+ | JWT implementation |
| **Tasks** | Celery | 5.3+ | Distributed tasks |
| **Queue** | Redis | 7.2+ | Performance, pub/sub |
| **Cache** | Redis | 7.2+ | In-memory caching |
| **Tests** | Pytest | 7.4+ | Fixtures, async support |
| **Lint** | Ruff | 0.1+ | Fast, comprehensive |
| **Format** | Black | 23.12+ | Consistent formatting |

### Frontend
| Catégorie | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **Framework** | Next.js | 14.1+ | SSR, performance, DX |
| **UI Lib** | React | 18.2+ | Ecosystem, concurrent |
| **Language** | TypeScript | 5.3+ | Type safety |
| **Styling** | Tailwind CSS | 3.4+ | Utility-first, DX |
| **Components** | Radix UI | 1.0+ | Accessible, unstyled |
| **Animation** | Framer Motion | 11.0+ | Smooth animations |
| **State** | Zustand | 4.4+ | Simple, performant |
| **Forms** | React Hook Form | 7.48+ | Performance, validation |
| **Charts** | Recharts | 2.10+ | Composable, React-based |
| **Icons** | Lucide React | 0.300+ | Consistent, tree-shake |
| **HTTP** | Axios | 1.6+ | Interceptors, progress |
| **WS** | Socket.io Client | 4.7+ | Reconnection, rooms |
| **Tests** | Vitest | 1.1+ | Fast, Vite integration |
| **E2E** | Playwright | 1.41+ | Cross-browser |
| **Lint** | ESLint | 8.56+ | Code quality |
| **Format** | Prettier | 3.2+ | Code formatting |

### ML/IA
| Catégorie | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **LLM** | Mistral 7B | Latest | Local, performant |
| **Framework** | MLX | 0.0.10+ | Apple Silicon optimized |
| **Embeddings** | Sentence-Transformers | 2.2+ | Multilingual |
| **OCR** | TrOCR | Latest | State-of-art accuracy |
| **Layout** | LayoutLMv3 | Latest | Document understanding |
| **OCR Fallback** | Tesseract | 5.3+ | Robustness |
| **Vision** | YOLO v8 | Latest | Logo/object detection |
| **NER** | CamemBERT | Latest | French NER |
| **Vector DB** | ChromaDB | 0.4.22+ | Simple, performant |
| **Image Proc** | OpenCV | 4.9+ | Preprocessing |
| **PDF** | PyPDF2 | 3.0+ | PDF manipulation |
| **Office** | python-docx | 1.1+ | Word documents |
| **Excel** | openpyxl | 3.1+ | Excel files |

### Infrastructure & DevOps
| Catégorie | Technologie | Version | Justification |
|-----------|-------------|---------|---------------|
| **Database** | PostgreSQL | 15+ | JSON, performance |
| **Vector Store** | ChromaDB | 0.4.22+ | Embeddings storage |
| **Cache/Queue** | Redis | 7.2+ | Speed, reliability |
| **Container** | Docker | 24.0+ | Dev environment |
| **Orchestration** | Docker Compose | 2.23+ | Local dev |
| **Monitoring** | Prometheus | 2.48+ | Metrics collection |
| **Visualization** | Grafana | 10.3+ | Dashboards |
| **Logs** | Loki | 2.9+ | Log aggregation |
| **CI/CD** | GitHub Actions | - | Automation |
| **Package** | Poetry | 1.7+ | Dependency management |
| **Secrets** | python-dotenv | 1.0+ | Environment config |

---

## 🛠️ Outils de Développement

### IDE & Éditeurs
- **VS Code** : IDE principal
  - Extensions : Python, Pylance, Prettier, ESLint, Tailwind IntelliSense
- **Cursor** : AI-powered editing
- **PyCharm** : Debugging Python complexe

### Outils de Développement
| Outil | Usage | Configuration |
|-------|-------|---------------|
| **Git** | Version control | Conventional commits |
| **GitHub** | Repository | Protected branches |
| **Bruno** | API testing | Collections versionnées |
| **TablePlus** | Database GUI | PostgreSQL + Redis |
| **Proxyman** | HTTP debugging | Local proxy |
| **Ray** | Debugging | Error tracking |
| **DevUtils** | Utilities | JSON, JWT, etc. |

### Outils de Conception
- **Figma** : Design UI/UX
- **Excalidraw** : Architecture diagrams
- **Mermaid** : Technical diagrams
- **draw.io** : Flow charts

### Outils de Test
- **Pytest** : Tests unitaires Python
- **Vitest** : Tests unitaires React
- **Playwright** : Tests E2E
- **k6** : Tests de charge
- **Artillery** : Tests performance API

### Outils de Documentation
- **MkDocs** : Documentation technique
- **Docusaurus** : Documentation utilisateur
- **Swagger UI** : Documentation API
- **Storybook** : Component library

---

## 📊 Planning de Développement

### Phase 1 : Foundation (Mois 1-3)

#### Sprint 1-2 : Architecture de Base
- [ ] Setup environnement développement
- [ ] Architecture backend FastAPI
- [ ] Structure frontend Next.js
- [ ] Configuration Docker Compose
- [ ] CI/CD pipeline basique

#### Sprint 3-4 : OCR Pipeline
- [ ] Intégration Tesseract baseline
- [ ] Préprocessing images (OpenCV)
- [ ] Support PDF multi-pages
- [ ] Tests sur documents réels
- [ ] Benchmarking performance

#### Sprint 5-6 : Classification
- [ ] Modèle de classification basique
- [ ] Règles métier (regex, keywords)
- [ ] Interface de correction
- [ ] Système d'apprentissage
- [ ] Métriques de précision

### Phase 2 : Intelligence (Mois 4-5)

#### Sprint 7-8 : RAG Implementation
- [ ] Setup ChromaDB
- [ ] Pipeline d'embeddings
- [ ] Intégration Mistral MLX
- [ ] API de recherche
- [ ] Interface de chat

#### Sprint 9-10 : Intégrations
- [ ] OAuth2 Gmail
- [ ] Extraction pièces jointes
- [ ] Google Calendar sync
- [ ] Webhooks system
- [ ] Notifications

### Phase 3 : Production (Mois 6-7)

#### Sprint 11-12 : Optimisation
- [ ] Performance tuning
- [ ] Caching strategy
- [ ] Batch processing
- [ ] Memory optimization
- [ ] Load testing

#### Sprint 13-14 : Sécurité & Finition
- [ ] Audit sécurité
- [ ] Chiffrement données
- [ ] Backup system
- [ ] Documentation complète
- [ ] Beta testing

### Phase 4 : Évolution (Mois 8-10)

#### Sprint 15-16 : Voice Interface
- [ ] STT integration
- [ ] Intent recognition
- [ ] TTS synthesis
- [ ] Voice commands
- [ ] Accessibility

#### Sprint 17-20 : Scale & Mobile
- [ ] API publique
- [ ] Plugin system
- [ ] Mobile app
- [ ] Cloud version
- [ ] Marketplace

---

## 🎯 Milestones & Livrables

### Q1 2025 : MVP
- ✅ OCR fonctionnel sur 5 types de documents
- ✅ Classification automatique basique
- ✅ Interface web minimale
- ✅ 10 beta testeurs

### Q2 2025 : Beta
- 📋 RAG complet avec Mistral
- 📋 Intégrations Gmail/Calendar
- 📋 Dashboard analytics
- 📋 50 beta testeurs

### Q3 2025 : V1.0
- 📋 Voice interface
- 📋 99.9% uptime
- 📋 100+ utilisateurs payants
- 📋 Documentation complète

### Q4 2025 : V2.0
- 📋 Mobile apps
- 📋 API publique
- 📋 500+ utilisateurs
- 📋 Plugin marketplace

---

## 🔧 Configuration Environnement

### Développement Local
```bash
# Requirements système
- macOS 13+ (Apple Silicon recommandé)
- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+
- 16GB RAM minimum
- 50GB stockage libre

# Setup initial
git clone https://github.com/lexo-app/lexo-v1
cd lexo-v1
make setup-dev
make run-dev
```

### Variables d'Environnement
```env
# .env.development
DATABASE_URL=postgresql://lexo:password@localhost:5432/lexo_dev
REDIS_URL=redis://localhost:6379/0
CHROMA_PATH=./data/chromadb
SECRET_KEY=development-secret-key-change-in-production
MISTRAL_MODEL_PATH=./ml_models/mistral-7b-mlx
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Structure Finale
```
LEXO_v1/
├── .github/              # CI/CD workflows
├── backend/              # FastAPI application
├── frontend/             # Next.js application
├── ml_models/            # Downloaded models
├── docker/               # Docker configurations
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── tests/                # Integration tests
├── .env.example          # Environment template
├── docker-compose.yml    # Local development
├── Makefile              # Common commands
├── CLAUDE.md             # AI assistant guide
├── PLANNING.md           # This file
└── README.md             # Project overview
```

---

## 📈 Métriques de Suivi

### Techniques
- **Build Time** : < 5 minutes
- **Test Coverage** : > 80%
- **Bundle Size** : < 2MB
- **API Latency** : < 200ms p95
- **OCR Speed** : < 5s/document

### Business
- **User Activation** : > 60%
- **Daily Active Users** : > 40%
- **Churn Rate** : < 5%/month
- **NPS Score** : > 50
- **Support Tickets** : < 5%

---

## 🚀 Stratégie de Lancement

### Soft Launch (MVP)
1. **10 early adopters** : Feedback quotidien
2. **Itérations rapides** : Deploy daily
3. **Focus** : Stabilité OCR + Classification

### Beta Launch
1. **50 beta users** : Professions variées
2. **Onboarding optimisé** : < 5 minutes
3. **Community** : Discord server

### Public Launch
1. **Product Hunt** : Viser Top 5
2. **Content Marketing** : Blog technique
3. **Partnerships** : Associations professionnelles

---

## 🔐 Considérations de Sécurité

### Données
- Chiffrement AES-256 au repos
- TLS 1.3 en transit
- Isolation par utilisateur
- Backup automatique 3-2-1

### Application
- JWT tokens (1h expiry)
- Rate limiting (100 req/min)
- Input validation stricte
- SQL injection protection

### Infrastructure
- Firewall applicatif
- Monitoring 24/7
- Incident response plan
- RGPD compliance

---

## 📚 Ressources & Documentation

### Documentation Technique
- Architecture Decision Records (ADRs)
- API Reference (OpenAPI)
- Component Library (Storybook)
- Deployment Guide

### Documentation Utilisateur
- Getting Started Guide
- Video Tutorials
- FAQ
- Troubleshooting

### Documentation Développeur
- Contributing Guide
- Code Style Guide
- Testing Guide
- Security Guide

---

## ✅ Checklist Pré-Launch

### MVP
- [ ] OCR fonctionne sur 95% des cas tests
- [ ] Classification > 90% précision
- [ ] Temps de réponse < 5s
- [ ] Zero crash sur 48h
- [ ] Documentation utilisateur de base

### Beta
- [ ] Onboarding < 5 minutes
- [ ] Support multi-comptes
- [ ] Backup automatique
- [ ] Monitoring complet
- [ ] RGPD compliant

### V1.0
- [ ] 99.9% uptime sur 30 jours
- [ ] Performance stable 10k+ documents
- [ ] Support client < 24h
- [ ] Documentation complète
- [ ] Processus de mise à jour

---

*Ce document est la référence principale pour le planning technique de LEXO v1. Il doit être mis à jour à chaque sprint pour refléter l'avancement réel du projet.*

**Dernière mise à jour :** Janvier 2025  
**Prochain review :** Fin Sprint 1  
**Responsable :** Tech Lead