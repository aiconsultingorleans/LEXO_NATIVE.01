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
- **Infrastructure** : Docker + Docker Compose

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
└── docker-compose.yml   # Orchestration
```

## 🚀 Démarrage Rapide

### Prérequis

- Docker Desktop
- Node.js 20+
- Python 3.11+
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
   make setup-dev
   ```

3. **Démarrer les services**
   ```bash
   make start
   ```

4. **Accéder aux applications**
   - 🌐 Frontend : http://localhost:3000
   - 🔌 API Backend : http://localhost:8000
   - 📚 Documentation API : http://localhost:8000/docs
   - 🗄️ Adminer (BDD) : http://localhost:8080

## 📖 Commandes Utiles

```bash
# Aide
make help

# Développement
make start          # Démarre tous les services
make stop           # Arrête tous les services
make logs           # Affiche les logs
make restart        # Redémarre tous les services

# Code Quality
make lint           # Vérification du code
make format         # Formatage automatique
make test           # Lance les tests
make type-check     # Vérification TypeScript

# Base de données
make db-migrate     # Applique les migrations
make db-reset       # Remet à zéro la BDD
make backup-db      # Sauvegarde la BDD

# Maintenance
make clean          # Nettoyage complet
make update         # Met à jour les dépendances
make health         # Vérifie la santé des services
```

## 🔧 Configuration

### Variables d'Environnement

Copiez et modifiez les fichiers `.env.example` :

```bash
# Backend
cp .env.example .env

# Frontend
cp frontend/.env.example frontend/.env.local
```

### Principales Configurations

- **DATABASE_URL** : Connexion PostgreSQL
- **REDIS_URL** : Connexion Redis
- **JWT_SECRET_KEY** : Clé de chiffrement JWT
- **UPLOAD_PATH** : Dossier surveillé pour OCR
- **MISTRAL_MODEL_PATH** : Chemin vers Mistral 7B

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
# Tous les tests
make test

# Tests backend uniquement
make test-backend

# Tests frontend uniquement
make test-frontend
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

1. **Port déjà utilisé**
   ```bash
   make stop
   make clean
   make start
   ```

2. **Problème de permissions**
   ```bash
   sudo chown -R $USER:$USER .
   ```

3. **Erreur de base de données**
   ```bash
   make db-reset
   ```

4. **Module Python manquant**
   ```bash
   cd backend && pip install -r requirements.txt
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