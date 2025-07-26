# 🤖 LEXO v1 - Assistant IA Administratif

> Application SaaS locale de gestion administrative intelligente utilisant OCR et RAG

## 📋 Description

LEXO v1 est un assistant IA conçu pour automatiser complètement le traitement documentaire des professions libérales. Il combine OCR intelligent, classification automatique et recherche sémantique via RAG (Retrieval-Augmented Generation).

### 🎯 Objectifs Principaux

- **Automatiser** le scan et la classification de documents (OCR intelligent)
- **Centraliser** l'information dans une base vectorielle (ChromaDB)
- **Permettre** des requêtes en langage naturel via RAG
- **Apprendre** continuellement des corrections utilisateur
- **Sécuriser** toutes les données localement

## 🏗️ Architecture

### Stack Technologique

- **Backend** : FastAPI + PostgreSQL + Redis + ChromaDB
- **Frontend** : Next.js 14 + React + Tailwind CSS + TypeScript
- **OCR** : TrOCR + LayoutLMv3 + Tesseract
- **RAG** : ChromaDB + Mistral 7B MLX
- **Auth** : JWT + OAuth2
- **Infrastructure** : Architecture native macOS

### Structure du Projet

```
IA_Administratif/
├── backend/              # API FastAPI
│   ├── api/             # Endpoints REST
│   ├── core/            # Configuration & DB
│   ├── models/          # Modèles SQLAlchemy
│   ├── ocr/             # Pipeline OCR
│   ├── rag/             # ChromaDB + Mistral
│   └── utils/           # Utilitaires
├── frontend/            # Application Next.js
│   └── src/
│       ├── components/  # Composants React
│       ├── hooks/       # Hooks personnalisés
│       ├── lib/         # Utilitaires
│       ├── stores/      # État Zustand
│       └── types/       # Types TypeScript
├── ml_models/           # Modèles IA
├── data/                # Données (DB, cache)
└── start_native.sh      # Démarrage natif
```

## 🚀 Démarrage Rapide

### Prérequis

- Node.js 20+
- Python 3.11+
- PostgreSQL 15 (Homebrew)
- Redis 7 (Homebrew)
- 16GB RAM minimum
- macOS (optimisé pour Apple Silicon)

### Installation

1. **Cloner le repository**
   ```bash
   git clone https://github.com/aiconsultingorleans/LEXO_v1.git
   cd LEXO_v1/IA_Administratif
   ```

2. **Configuration initiale**
   ```bash
   cd IA_Administratif
   ./start_native.sh
   ```

3. **Démarrer les services**
   ```bash
   ./start_native.sh
   ```

4. **Accéder aux applications**
   - 🌐 Frontend : http://localhost:3000
   - 🔌 API Backend : http://localhost:8000
   - 📚 Documentation API : http://localhost:8000/docs
   - 🤖 Service IA Mistral : http://localhost:8004

## 📖 Commandes Utiles

```bash
# Développement natif
./start_native.sh    # Démarre tous les services natifs
./stop_native.sh     # Arrête tous les services natifs
./diagnostic_native.sh # Diagnostic système complet

# Services individuels
./start_backend_native.sh  # Backend FastAPI seul
./start_frontend_native.sh # Frontend Next.js seul

# Tests
cd backend && python test_complete_integration.py
cd frontend && npm run test

# Base de données (Homebrew)
brew services start postgresql@15
brew services start redis
```

## 🔧 Configuration

### Variables d'Environnement

La configuration native utilise les variables dans :

```bash
# Configuration ML native
config/ml_cache.env

# Variables backend
backend/.env

# Variables frontend
frontend/.env.local
```

### Principales Configurations

- **TRANSFORMERS_CACHE** : Cache modèles natif
- **DATABASE_URL** : PostgreSQL Homebrew
- **REDIS_URL** : Redis natif
- **JWT_SECRET_KEY** : Clé de chiffrement JWT
- **UPLOAD_PATH** : `/Users/stephaneansel/Documents/LEXO_v1/OCR/En attente`

## 📁 Surveillance de Dossier

LEXO surveille automatiquement le dossier :
```
~/Documents/LEXO_v1/OCR/
├── factures/          # Auto-classé
├── impots/           
├── rib/              
├── contrats/
├── courriers/
├── releves_bancaires/
└── non_classes/       # En attente
```

## 🧪 Tests

```bash
# Tests backend natifs
cd backend && source venv/bin/activate
python test_complete_integration.py

# Tests frontend natifs
cd frontend && npm run test

# Tests pipeline OCR
cd backend && python test_ocr_etape3.py
```

## 📊 Fonctionnalités

### Phase 1 - MVP ✅
- [x] OCR basique (PDF, images)
- [x] Classification automatique simple
- [x] Interface web minimale
- [x] Authentification basique

### Phase 2 - Beta 🚧
- [ ] OCR avancé multi-formats
- [ ] RAG avec ChromaDB
- [ ] Dashboard complet
- [ ] Intégration Gmail
- [ ] Assistant IA

### Phase 3 - V1.0 📋
- [ ] Apprentissage supervisé
- [ ] Google Calendar
- [ ] Génération de documents
- [ ] Analytics avancés
- [ ] Multi-utilisateurs

## 🔐 Sécurité

- **Local-first** : Toutes les données restent sur votre Mac
- **Chiffrement AES-256** pour les documents sensibles
- **JWT** avec refresh tokens
- **Rate limiting** sur les API
- **CORS** configuré pour le frontend uniquement

## 🐛 Dépannage

### Problèmes Courants

1. **Processus en cours**
   ```bash
   ./stop_native.sh
   ./start_native.sh
   ```

2. **Problème de permissions**
   ```bash
   sudo chown -R $USER:$USER .
   ```

3. **Erreur de base de données**
   ```bash
   brew services restart postgresql@15
   ```

4. **Module Python manquant**
   ```bash
   cd backend && source venv/bin/activate && pip install -r requirements.txt
   ```

## 📚 Documentation

- [Guides utilisateur](./docs/user/)
- [Documentation technique](./docs/tech/)
- [API Reference](http://localhost:8000/docs)
- [Contribution Guide](./CONTRIBUTING.md)

## 🤝 Contribution

1. Fork le projet
2. Créer une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commit (`git commit -m 'Add AmazingFeature'`)
4. Push (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir [LICENSE](LICENSE) pour plus de détails.

## 👥 Équipe

- **Tech Lead** : [Nom]
- **Frontend** : [Nom]
- **Backend** : [Nom]
- **ML/IA** : [Nom]

## 📞 Support

- 📧 Email : support@lexo-app.com
- 💬 Discord : [Lien]
- 🐛 Issues : [GitHub Issues](https://github.com/aiconsultingorleans/LEXO_v1/issues)

---

**Philosophie** : "It just works" - L'utilisateur dépose un document, LEXO fait le reste. ✨