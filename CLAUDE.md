# 🤖 CLAUDE2.md - Guide Technique LEXO v1 [État Actuel]

## 📌 Contexte Projet

**LEXO v1** est une application SaaS locale de gestion administrative intelligente qui automatise complètement le traitement documentaire pour les professions libérales.

**Environnement :** macOS (Mac mini M4 - 32 Go RAM)  
**Architecture :** 100% locale avec pipeline IA hybride  
**État :** MVP opérationnel - 7 étapes sur 12 complétées (82% fonctionnel)

---

## 🏗️ Architecture Hybride Opérationnelle

### Structure Principale
```
~/Documents/LEXO_v1/
├── IA_Administratif/            # 🏗️ PROJET PRINCIPAL
│   ├── backend/                 # FastAPI (port 8000) ✅
│   ├── frontend/                # Next.js (port 3000) ✅  
│   ├── ai_services/             # Mistral MLX (port 8004) ✅
│   ├── data/ + ml_models/       # Données + Modèles ✅
│   └── docker-compose.yml       # Stack complète ✅
├── OCR/                         # 📁 Dossier surveillé
└── start_all.sh / stop_all.sh   # Scripts globaux ✅
```

### Services Actifs
| Service | Port | État | Fonction |
|---------|------|------|----------|
| **Backend FastAPI** | 8000 | ✅ | API, OCR, Classification |
| **Frontend Next.js** | 3000 | ✅ | Interface utilisateur |
| **Mistral MLX** | 8004 | ✅ | Analyse IA locale |
| **ChromaDB** | 8001 | ✅ | Base vectorielle RAG |
| **PostgreSQL** | 5432 | ✅ | Métadonnées |
| **Redis** | 6379 | ✅ | Cache + queues |

---

## 🎯 État d'Avancement par Étapes

### ✅ COMPLÉTÉES (Score: 85%+)
1. **Étape 1-2 :** Fondations Backend + Frontend ✅ *100%*
2. **Étape 3 :** Pipeline OCR (TrOCR + Tesseract + Hybride) ✅ *82%*
3. **Étape 4 :** Classification automatique (9 catégories) ✅ *100%*
4. **Étape 5 :** RAG + ChromaDB + Mistral MLX ✅ *95%*
5. **Étape 7 :** Dashboard Analytics avancé ✅ *95%*

### 🚧 EN COURS 
- **Étape 6 :** Intégrations externes (Gmail, Calendar) *20%*
- **Étape 8 :** Interface vocale *0%*
- **Étape 9 :** Sécurité + Performance *40%*

### 📋 PLANIFIÉES
- **Étape 10-12 :** Tests, Déploiement, Post-launch

---

## ⚡ Pipeline Documentaire Unifié

### Flux Opérationnel
```mermaid
graph LR
    A[📄 Upload] --> B[🔍 OCR Hybride]
    B --> C[🤖 Mistral MLX]
    C --> D[🏷️ Classification]
    D --> E[📁 Classement Auto]
    E --> F[💾 ChromaDB + Cache]
```

### API Endpoints Clés
```bash
# Pipeline unifié (RECOMMANDÉ)
POST /api/v1/documents/upload-and-process    # Upload + OCR + IA + Classification

# Composants individuels  
POST /api/v1/documents/upload               # Upload seul
POST /api/v1/ocr/process                    # OCR hybride
POST /api/v1/intelligence/analyze          # Analyse Mistral
POST /api/v1/classification/classify       # Classification

# RAG + Recherche
POST /api/v1/rag/search                     # Recherche sémantique
POST /api/v1/rag/chat                       # Chat avec contexte
```

---

## 🚀 Démarrage Optimisé (90 secondes)

### Commandes Essentielles
```bash
# 🚀 DÉMARRAGE COMPLET (recommandé)
cd ~/Documents/LEXO_v1
./start_all.sh                    # Démarre toute l'infrastructure

# 🐳 Services Docker
cd IA_Administratif
docker-compose up -d             # PostgreSQL, Redis, ChromaDB

# 🤖 Service MLX natif
./start_document_analyzer.sh     # Mistral MLX (port 8004)

# 🛑 ARRÊT PROPRE
./stop_all.sh                    # Arrête tout
```

### Performance Démarrage
- **API prête** : ~30 secondes
- **OCR disponible** : Lazy loading (premier document)
- **Mistral chargé** : ~60 secondes
- **Interface web** : Immédiat après API

---

## 🎨 Stack Technologique Validée

### Backend Opérationnel
```python
# FastAPI 0.115+ avec async
# SQLAlchemy 2.0 + PostgreSQL 15
# Redis 7 (cache + queues)
# Alembic (migrations)

# OCR Pipeline
# - TrOCR (HuggingFace) ✅
# - Tesseract 5 (fallback) ✅  
# - LayoutLMv3 (structure) ✅
# - OpenCV (prétraitement) ✅

# IA Locale
# - Mistral 7B MLX ✅
# - ChromaDB 0.5+ ✅
# - Sentence-Transformers ✅
```

### Frontend Moderne
```typescript
// Next.js 15 + React 19
// TypeScript strict
// Tailwind CSS 4
// Zustand (state)
// React Hook Form + Zod

// Composants spécialisés
// - DocumentUpload ✅
// - DashboardWidget ✅  
// - KPIWidget ✅
// - VirtualizedDocumentList ✅
```

---

## 📊 Fonctionnalités Opérationnelles

### 1. Upload + Traitement Intelligent
- **Drag & Drop** : PDF, images (PNG, JPG, TIFF) ✅
- **Pipeline unifié** : Upload → OCR → IA → Classification ✅
- **Feedback temps réel** : Progression + résultats enrichis ✅
- **Performance** : <10 secondes par document ✅

### 2. Classification Automatique (9 catégories)
```typescript
Categories = {
  factures, rib, contrats, attestations, 
  courriers, rapports, cartes_transport,
  documents_personnels, non_classes
}
// Score moyen: 89.7% de confiance ✅
```

### 3. Dashboard Analytics
- **KPIs temps réel** : Documents traités, précision OCR, sécurité ✅
- **Graphiques** : Bar, Line, Pie charts avec Recharts ✅
- **Timeline** : Activité récente avec événements colorés ✅
- **Filtres avancés** : Date, catégorie, statut ✅

### 4. RAG + Chat Intelligent  
- **Recherche sémantique** : ChromaDB + embeddings multilingues ✅
- **Chat contexte** : Mistral MLX avec sources citées ✅
- **Performance** : <100ms retrieval, <2s génération ✅

---

## 🔧 Conventions de Code

### Backend Python
```python
# Structure endpoints FastAPI
@router.post("/endpoint")
async def function_name(
    param: Type,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
) -> ResponseModel:
    """Description claire."""
    pass

# Conventions
# - Classes: PascalCase
# - Functions: snake_case  
# - Constants: UPPER_SNAKE_CASE
# - Private: _leading_underscore
```

### Frontend TypeScript
```typescript
// Composants React
export const ComponentName: FC<Props> = ({ param }) => {
  const [state, setState] = useState();
  
  return (
    <div className="tailwind-classes">
      {/* Content */}
    </div>
  );
};

# Conventions
# - Components: PascalCase
# - Hooks: usePrefix
# - Utils: camelCase
# - Types: PascalCase + suffix
```

---

## 🧪 Tests Validés

### Scripts de Test Opérationnels
```bash
cd IA_Administratif/backend

# Tests complets validés ✅
python test_ocr_etape3.py        # OCR pipeline (82% succès)
python test_rag_etape5.py        # RAG système (95% succès)  
python test_complete_integration.py  # Pipeline intégré

# Tests unitaires
pytest tests/                    # Backend
cd ../frontend && npm run test   # Frontend
```

### Validation Documents Réels
- **Carte transport** : Classée "cartes_transport" (89.7% confiance) ✅
- **Factures EDF** : Entités extraites + résumé IA ✅
- **Documents scannés** : OCR hybride fonctionnel ✅

---

## 📁 Navigation Rapide

### Chemins Critiques
```bash
# Backend API
IA_Administratif/backend/api/documents.py      # Upload unifié
IA_Administratif/backend/ocr/hybrid_ocr.py     # OCR principal
IA_Administratif/backend/rag/mistral_wrapper.py # Interface Mistral

# Frontend Interface  
IA_Administratif/frontend/src/app/dashboard/page.tsx       # Dashboard principal
IA_Administratif/frontend/src/components/documents/       # Upload + liste
IA_Administratif/frontend/src/components/dashboard/       # Analytics

# Services IA
IA_Administratif/ai_services/document_analyzer.py         # Mistral MLX

# Configuration
IA_Administratif/docker-compose.yml           # Stack Docker
IA_Administratif/backend/core/config.py       # Configuration
```

### Scripts Utiles
```bash
# Gestion projet
./start_all.sh                    # Démarrage complet avec auto-correction
./stop_all.sh                     # Arrêt propre avec sauvegarde
./check_health.sh                 # Diagnostic complet système ✨ NOUVEAU
IA_Administratif/start_document_analyzer.sh   # Mistral seul

# Validation et diagnostic
python test_complete_integration.py   # Test pipeline
curl http://localhost:8000/api/v1/health  # Health check
curl http://localhost:8000/api/v1/batch/status  # État progression batch ✨ NOUVEAU
```

---

## 🔄 Redémarrage Serveur Next.js - Procédure Obligatoire

### Cas nécessitant un redémarrage
- **Nouveaux composants React** : Ajout de fichiers `.tsx` dans `/components`
- **Modifications TypeScript** : Changements d'interfaces, types, hooks
- **Nouvelles routes API** : Modifications backend affectant le frontend
- **Modifications de configuration** : `next.config.js`, variables d'environnement
- **Ajout de dépendances** : Nouveaux packages npm

### Procédure standardisée OBLIGATOIRE

```bash
# 🔥 ÉTAPE 1 : Tuer le processus sur le port 3000
lsof -ti:3000 | xargs kill -9

# ⚙️ ÉTAPE 2 : Redémarrer Next.js sur le port 3000
cd IA_Administratif/frontend
npm run dev

# ✅ VÉRIFICATION : Le serveur doit démarrer sur http://localhost:3000
```

### Alternative : Reset complet système

```bash
# 🛑 Arrêt complet de tous les services
./stop_all.sh

# 🚀 Redémarrage complet (recommandé après modifications importantes)
./start_all.sh
```

### Commandes de diagnostic

```bash
# Vérifier les processus sur le port 3000
lsof -i:3000

# Vérifier tous les processus LEXO
ps aux | grep -E "(next|node|npm)" | grep -v grep

# Forcer l'arrêt de tous les processus Node.js (utiliser avec précaution)
pkill -f "node.*next"
```

### ⚠️ RÈGLES CRITIQUES

1. **Port 3000 OBLIGATOIRE** : Ne jamais utiliser un port alternatif (3001, 3002, etc.)
2. **Intégrité ecosystem** : Le frontend doit toujours être sur le port 3000 pour cohérence avec le backend (port 8000)
3. **Redémarrage systématique** : Après toute modification importante, TOUJOURS redémarrer
4. **Vérification visuelle** : Toujours vérifier que les modifications sont prises en compte dans le navigateur

### Workflow type après modifications

```bash
# 1. Modifications effectuées dans le code
# 2. Arrêt propre du serveur Next.js
lsof -ti:3000 | xargs kill -9

# 3. Redémarrage sur port 3000
cd IA_Administratif/frontend && npm run dev

# 4. Vérification dans le navigateur sur http://localhost:3000
# 5. Test des nouvelles fonctionnalités
```

### Dépannage port bloqué

```bash
# Si le port 3000 reste occupé après kill
sudo lsof -ti:3000 | sudo xargs kill -9

# En cas de problème persistant, redémarrage complet
./stop_all.sh && sleep 5 && ./start_all.sh
```

**🎯 Principe fondamental** : Maintenir l'intégrité de l'architecture LEXO avec frontend:3000 + backend:8000 + services Docker

---

## 🛡️ Auto-correction et Diagnostic - Prévention des Problèmes

### Problèmes automatiquement corrigés par start_all.sh

Le script de démarrage détecte et corrige automatiquement ces problèmes courants :

#### ✅ **Dépendances manquantes**
```bash
# Auto-détection et installation de psutil si manquant
if ! docker compose exec -T backend python -c "import psutil"; then
    log "Installation de psutil..."
    docker compose exec -T backend pip install psutil==6.1.0
    docker compose restart backend
fi
```

#### ✅ **Comptes utilisateurs manquants**
```bash
# Vérification et création automatique des comptes
USER_COUNT=$(vérification base de données)
if [ "$USER_COUNT" = "0" ]; then
    log "Création des comptes utilisateurs..."
    docker compose exec -T backend python scripts/load_fixtures_auto.py
fi
```

#### ✅ **Vérification compte admin**
```bash
# S'assurer que admin@lexo.fr existe toujours
if [ "$ADMIN_EXISTS" != "True" ]; then
    warning "Compte admin manquant, recréation..."
    docker compose exec -T backend python scripts/load_fixtures_auto.py
fi
```

### Script de diagnostic autonome

```bash
# 🔍 Diagnostic complet du système
./check_health.sh

# Vérifie automatiquement :
# ✅ État des services Docker
# ✅ Accessibilité des endpoints
# ✅ Dépendances critiques (psutil, sqlalchemy, etc.)
# ✅ Comptes utilisateurs et admin
# ✅ Ports et connectivité
# ✅ Nouvelles fonctionnalités (API batch progression)
```

### Protection contre les interruptions

Le script `stop_all.sh` vérifie maintenant les traitements en cours :

```bash
# Vérification des tâches batch avant arrêt
if curl -s http://localhost:8000/api/v1/batch/status | grep -q '"active_tasks": [1-9]'; then
    warning "Des traitements batch sont en cours!"
    echo "Voulez-vous vraiment arrêter ? [y/N]"
    # Attend confirmation utilisateur
fi
```

### Sauvegarde automatique

Lors de l'arrêt, sauvegarde automatique dans `backups/YYYYMMDD/` :
- **Statistiques système** : `stats_HHMMSS.json`
- **État batch en cours** : `batch_status_HHMMSS.json`

### Commandes de réparation rapide

```bash
# Problèmes généraux
./stop_all.sh && ./start_all.sh

# Diagnostic détaillé
./check_health.sh

# Corrections manuelles spécifiques
cd IA_Administratif
docker compose exec backend pip install psutil==6.1.0
docker compose exec backend python scripts/load_fixtures_auto.py
docker compose restart backend
```

**🎯 Objectif** : Plus jamais de problèmes de `psutil` manquant ou de comptes perdus !

---

## 🔍 Optimisations Performance

### Cache Intelligent
```python
# Cache Mistral (70% amélioration)
utils/mistral_cache.py: TTL 1h, hash-based keys

# Cache OCR  
ocr/ocr_cache.py: Redis + FileSystem hybrid

# Cache modèles ML
ml_models/: Local uniquement (HF_OFFLINE=1)
```

### Lazy Loading
- **OCR** : Initialisé au premier document (évite 30s démarrage)
- **Mistral** : Chargé en arrière-plan
- **Composants React** : Chargement conditionnel

---

## 🚧 Points d'Amélioration

### Performance
- [ ] TrOCR réactivation (boucle infinie résolue)
- [ ] Batch processing multi-documents
- [ ] Cache intelligent embeddings

### UX  
- [ ] Mode sombre
- [ ] Prévisualisation documents
- [ ] Notifications push
- [ ] Shortcuts clavier

### Monitoring
- [ ] Métriques détaillées pipeline
- [ ] Alertes automatiques
- [ ] Logs structurés

---

## 🎊 Points Forts Actuels

1. **🎯 Pipeline Unifié** : Upload → OCR → IA → Classification fonctionnel
2. **⚡ Performance** : <10s traitement, 89.7% précision classification
3. **🛡️ Local-First** : 100% local, aucune donnée externe
4. **📊 Analytics** : Dashboard temps réel opérationnel
5. **🤖 IA Intégrée** : Mistral MLX + RAG + Classification automatique
6. **🎨 UX Moderne** : Interface responsive + feedback temps réel

---

## 💡 Utilisation Optimale avec Claude Code

### Pour OCR et traitement
- Utiliser endpoint unifié `/upload-and-process` (recommandé)
- Tests avec `test_ocr_etape3.py` pour validation
- Cache automatique activé (performance)

### Pour développement interface
- Composants dans `IA_Administratif/frontend/src/components/`
- State management avec Zustand
- Mobile-first avec Tailwind

### Pour débogage
- Logs dans `IA_Administratif/logs/`
- Health checks `/api/v1/health/*`
- Monitoring `/api/v1/monitoring/stats`

---

## 🚀 Workflow de Validation Automatique

### Commande de Validation Rapide

**Déclencheur :** `"je valide"`

**Action automatique :** Création d'une nouvelle branche + commit + README + push vers GitHub

### Logique de Versioning Automatique

```bash
# Détection automatique du numéro de version suivant
git branch -r | grep "origin/LEXO_v1\." | sed 's/.*LEXO_v1\.//' | sort -n | tail -1
# Exemple : Si dernière version = LEXO_v1.5 → Nouvelle branche = LEXO_v1.6
```

### Processus Automatisé

```bash
# 1. Détection version suivante
LATEST_VERSION=$(git branch -r | grep "origin/LEXO_v1\." | sed 's/.*LEXO_v1\.//' | sort -n | tail -1)
NEW_VERSION=$((LATEST_VERSION + 1))
NEW_BRANCH="LEXO_v1.${NEW_VERSION}"

# 2. Création branche et commit
git checkout -b ${NEW_BRANCH}
git add -A
git commit -m "feat: ${NEW_BRANCH} - Améliorations et nouvelles fonctionnalités

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 3. Génération README résumé
# Création automatique du README.md avec résumé des changements

# 4. Push vers GitHub
git push -u origin ${NEW_BRANCH}
```

### Template README Automatique

```markdown
# LEXO v1.x - Résumé des Modifications

## 📊 Métadonnées
- **Version :** LEXO_v1.x
- **Date :** [Date automatique]
- **Branche :** LEXO_v1.x
- **Repo :** https://github.com/aiconsultingorleans/LEXO_v1

## 🎯 Résumé des Changements
[Résumé automatique généré par Claude des modifications effectuées]

## 📁 Fichiers Modifiés
[Liste automatique des fichiers modifiés avec description]

## 🧪 Tests Validés
[Tests exécutés et validés]

## 🚀 Impact Business
[Impact des modifications sur les fonctionnalités]

🤖 Generated with [Claude Code](https://claude.ai/code)
```

### Utilisation

```bash
# L'utilisateur tape simplement :
"je valide"

# Claude exécute automatiquement :
# ✅ Détection version (ex: v1.5 → v1.6)
# ✅ Création branche LEXO_v1.6
# ✅ Commit avec message standardisé
# ✅ Génération README résumé
# ✅ Push vers GitHub
# ✅ Confirmation avec URL branche
```

### Repo GitHub Cible
**URL :** https://github.com/aiconsultingorleans/LEXO_v1  
**Format branches :** LEXO_v1.x (où x = numéro incrémental)  
**Dernière version actuelle :** LEXO_v1.5

---

**📈 État Projet :** MVP opérationnel - Pipeline documentaire intelligent fonctionnel  
**🎯 Prochaine étape :** Optimisation TrOCR + Interface mobile + Intégrations externes  
**🚀 Philosophie :** "It just works" - L'utilisateur dépose un document, LEXO fait le reste

*Dernière mise à jour : 25 juillet 2025 - Architecture hybride opérationnelle*