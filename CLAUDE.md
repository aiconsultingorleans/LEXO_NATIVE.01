# 🤖 CLAUDE.md - Guide Technique LEXO_NATIVE.01

## 📌 Contexte Projet

**LEXO_NATIVE.01** : Application SaaS locale de gestion administrative intelligente qui automatise le traitement documentaire pour professions libérales.

**Environnement Dev :** MacBook Pro M4 Pro Max (128GB RAM) | **Cible :** Mac Mini M4 (32GB RAM)  
**Architecture :** 100% native macOS avec pipeline IA optimisé Apple Silicon  
**État :** MVP opérationnel - Pipeline documentaire fonctionnel (89.7% précision)

---

## 🏗️ Architecture Native macOS

### Structure Projet
```
~/Documents/LEXO_v1/IA_Administratif/
├── backend/                    # FastAPI (port 8000)
│   ├── api/                   # Endpoints API
│   ├── ocr/                   # Pipeline OCR hybride
│   ├── rag/                   # Mistral MLX + ChromaDB
│   ├── core/                  # Config, DB, Auth
│   ├── test_models_selection.py  # Benchmark DONUT
│   └── main.py               # Point d'entrée
├── frontend/                   # Next.js (port 3000)
│   └── src/
│       ├── app/              # Pages Next.js
│       └── components/       # Composants React
├── ai_services/               # Mistral MLX (port 8004)
│   ├── document_analyzer.py  # Service principal
│   └── venv/                 # Environnement MLX
├── ml_models/                 # Modèles locaux
├── data/                     # ChromaDB + Cache
└── OCR/                      # Dossier surveillé
```

### Services Actifs
| Service | Port | Type | Fonction |
|---------|------|------|----------|
| **Backend FastAPI** | 8000 | uvicorn | API, OCR, Classification |
| **Frontend Next.js** | 3000 | npm dev | Interface utilisateur |
| **Mistral MLX** | 8004 | Python | Analyse IA Apple Silicon |
| **Donut + CamemBERT** | 8005 | Python | Pipeline alternatif (en dev) |
| **PostgreSQL** | 5432 | Homebrew | Base données |
| **Redis** | 6379 | Homebrew | Cache + queues |
| **ChromaDB** | - | Standalone | Base vectorielle |

---

## 🔧 Guidelines de Développement LEXO

### 🎯 Philosophie générale

**KISS (Keep It Simple, Stupid)** - La simplicité est la sophistication ultime. Préférer toujours la solution la plus simple qui fonctionne.

### 📋 Règles fondamentales

#### 1. **Pas de sur-ingénierie**
- ❌ PAS de patterns complexes si non nécessaires (pas de factories abstraites pour créer un simple objet)
- ❌ PAS d'architecture sur-dimensionnée (pas de microservices pour une app desktop)
- ✅ Code direct et lisible plutôt que "clever"
- ✅ YAGNI (You Aren't Gonna Need It) - Ne pas coder pour des besoins futurs hypothétiques

#### 2. **Architecture minimaliste**
```
app/
├── main/           # Code Swift/Objective-C pour macOS
├── backend/        # API Python simple (FastAPI/Flask)
├── frontend/       # Next.js si vraiment nécessaire
└── shared/         # Types et utilitaires partagés
```

#### 3. **Dépendances minimales**
- Utiliser les bibliothèques natives macOS quand possible
- Pour Python : stdlib > petite lib bien maintenue > grosse framework
- Pour Next.js : éviter les meta-frameworks et plugins non essentiels
- Chaque dépendance doit être justifiée

### 🐍 Python - Règles spécifiques

#### Structure simple
```python
# ❌ ÉVITER
class AbstractLLMProviderFactory:
    def create_provider(self, config: Dict) -> AbstractLLMProvider:
        # 50 lignes de code...

# ✅ PRÉFÉRER
def create_llm_client(api_key: str, model: str = "gpt-4"):
    return OpenAI(api_key=api_key, model=model)
```

#### Gestion des LLM
- Utiliser directement les SDK officiels (OpenAI, Anthropic, etc.)
- Pas de wrapper abstrait sauf si 2+ providers
- Gestion d'erreur simple avec try/except
- Logs clairs et utiles

#### API Backend
```python
# FastAPI minimal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Query(BaseModel):
    text: str
    model: str = "gpt-4"

@app.post("/process")
async def process_document(query: Query):
    try:
        # Code direct, pas de couches d'abstraction
        result = llm_client.complete(query.text)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### 🖥️ macOS Native - Règles spécifiques

#### Swift/SwiftUI
- Utiliser SwiftUI sauf besoin spécifique AppKit
- Pas de MVVM complexe si MV suffit
- Utiliser les APIs natives (NSDocument, etc.)
- Éviter les bibliothèques tierces pour l'UI

#### Communication avec le backend
```swift
// ❌ ÉVITER - Sur-abstraction
protocol NetworkManagerProtocol { }
class NetworkManager: NetworkManagerProtocol { }
class APIClient { }
class LLMService { }

// ✅ PRÉFÉRER - Direct et simple
class APIClient {
    func processDocument(_ text: String) async throws -> String {
        // URLSession direct
    }
}
```

#### Intégration Python
- Utiliser un subprocess Python ou
- API REST locale (http://localhost:8000)
- Pas de bridge complexe Python-Swift

### ⚛️ Next.js (si nécessaire) - Règles spécifiques

#### Quand l'utiliser
- ❓ Se demander d'abord : "Ai-je vraiment besoin de Next.js ?"
- Une WebView SwiftUI simple peut suffire
- Si oui : App Router simple, pas de magie

#### Structure minimale
```
frontend/
├── app/
│   ├── page.tsx        # Page unique si possible
│   └── api/            # Seulement si nécessaire
├── components/         # Composants simples
└── lib/               # Utilitaires
```

#### Composants
```tsx
// ❌ ÉVITER
const DocumentProcessor: FC<DocumentProcessorProps> = ({ 
  config, 
  callbacks, 
  providers 
}) => {
  // 200 lignes de hooks custom...
}

// ✅ PRÉFÉRER
function DocumentView({ document, onProcess }) {
  const [result, setResult] = useState(null);
  
  async function handleProcess() {
    const res = await fetch('/api/process', {
      method: 'POST',
      body: JSON.stringify({ text: document })
    });
    setResult(await res.json());
  }
  
  return (
    <div>
      {/* UI simple et directe */}
    </div>
  );
}
```

### 🔧 Patterns à utiliser

#### 1. **Configuration simple**
```python
# config.py
import os
from dataclasses import dataclass

@dataclass
class Config:
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = "gpt-4"
    max_tokens: int = 2000

config = Config()
```

#### 2. **Gestion d'erreur pragmatique**
```python
def process_with_llm(text: str) -> str:
    try:
        return llm_client.complete(text)
    except RateLimitError:
        time.sleep(1)
        return process_with_llm(text)  # Retry simple
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return "Erreur de traitement"
```

#### 3. **Tests simples**
```python
# test_simple.py
def test_document_processing():
    result = process_document("test")
    assert result is not None
    assert len(result) > 0
```

### 🚫 Anti-patterns à éviter

1. **Dependency Injection complexe** pour une app desktop
2. **Event Sourcing / CQRS** - Overkill
3. **GraphQL** quand REST suffit
4. **Kubernetes/Docker** pour dev local
5. **Redux/MobX** quand useState suffit
6. **TypeScript strict partout** - Seulement où c'est utile
7. **Tests unitaires de tout** - Tester ce qui a de la valeur

### 📝 Checklist avant d'ajouter de la complexité

- [ ] Est-ce que la solution simple a été essayée ?
- [ ] Est-ce que cette abstraction sera utilisée plus d'une fois ?
- [ ] Est-ce que ça rend le code plus lisible ?
- [ ] Est-ce que ça facilite vraiment la maintenance ?
- [ ] Est-ce que c'est nécessaire MAINTENANT ?

### 🎪 Exemples de simplification

#### Gestion d'état
```python
# ❌ ÉVITER
class StateManager:
    def __init__(self):
        self._observers = []
        self._state = {}
    
    def subscribe(self, observer):
        # ...

# ✅ PRÉFÉRER
app_state = {
    "current_document": None,
    "processing": False
}
```

#### Appels LLM
```python
# ❌ ÉVITER
class LLMChain:
    def __init__(self, prompt_template, parser, memory):
        # ...

# ✅ PRÉFÉRER
def ask_llm(question: str, context: str = "") -> str:
    prompt = f"{context}\n\nQuestion: {question}"
    return openai_client.complete(prompt)
```

### 🏁 Résumé

1. **Écrire du code boring** - Facile à lire, facile à débugger
2. **Commencer simple** - Complexifier seulement si nécessaire
3. **Préférer la composition** à l'héritage
4. **Une fonction = une responsabilité**
5. **Si c'est difficile à expliquer, c'est trop complexe**

### 💡 Mantra final

> "Le meilleur code est celui qu'on n'a pas écrit. Le deuxième meilleur est celui qu'un junior peut comprendre en 5 minutes."

**Note pour Claude Code** : Ces guidelines sont prioritaires. En cas de doute, choisir la simplicité. Ne pas suggérer de patterns complexes sauf demande explicite. Proposer toujours la solution la plus directe en premier.

---

## 🛡️ Approche Non-Destructive Garantie

### Principe Fondamental
- **AUCUNE suppression de code** sans validation explicite utilisateur
- **Conservation totale** des pipelines fonctionnels (Mistral MLX reste principal)
- **Développement en parallèle** sans impact sur l'existant
- **Rollback instantané** toujours possible

### Workflow Sécurisé
- **Branches isolées** par feature (`feat/donut_alternative_pipeline`)
- **Services parallèles** sur ports distincts (8004 Mistral, 8005 DONUT)
- **Tests non-destructifs** sans remplacement du pipeline principal
- **Validation utilisateur** obligatoire avant toute suppression
- **Conservation API** existante intacte

### Règles de Développement
1. **Ajout uniquement** : Nouvelles fonctionnalités en plus de l'existant
2. **Coexistence** : Anciens et nouveaux systèmes fonctionnent ensemble
3. **Toggle utilisateur** : Choix entre pipelines depuis l'interface
4. **Fallback automatique** : Retour vers Mistral en cas de problème DONUT
5. **Tests isolés** : Validation sans affecter le production
6. **Documentation** : Chaque ajout documenté pour traçabilité

---

## ⚡ Pipeline Documentaire

### Flux Principal (Non-Destructif)
```
📄 Upload → 🔍 OCR Hybride → 🤖 [Mistral MLX (principal) | DONUT+CamemBERT (alternatif)] → 🏷️ Classification → 📁 Classement Auto
```

**Toggle utilisateur** : Choix du pipeline depuis le dashboard, Mistral MLX reste par défaut

### API Endpoints Clés
```bash
# Pipeline unifié (RECOMMANDÉ)
POST /api/v1/documents/upload-and-process    # Upload + OCR + IA + Classification

# Composants individuels  
POST /api/v1/ocr/process                    # OCR hybride
POST /api/v1/intelligence/analyze          # Analyse Mistral
POST /api/v1/classification/classify       # Classification

# RAG + Recherche
POST /api/v1/rag/search                     # Recherche sémantique
POST /api/v1/rag/chat                       # Chat avec contexte
```

---

## 🚀 Démarrage Native

### Commandes Essentielles
```bash
# Démarrage complet (30 secondes)
cd ~/Documents/LEXO_v1/IA_Administratif
./start_native.sh

# Arrêt propre
./stop_native.sh

# Services individuels
./start_backend_native.sh     # Backend seul
./start_frontend_native.sh    # Frontend seul

# Diagnostic
./diagnostic_native.sh        # État système complet
```

### Performance Démarrage
- **Services système** : Instantané (Homebrew)
- **API Backend** : ~10s (vs 30s Docker)
- **Interface web** : ~5s 
- **Mistral MLX** : ~30s (vs 60s Docker)
- **Pipeline complet** : **30-40s total**

---

## 🎯 État Avancement

### ✅ COMPLÉTÉES
- **Étapes 1-2** : Backend + Frontend (100%)
- **Étape 3** : Pipeline OCR hybride (82%)
- **Étape 4** : Classification 9 catégories (100%)
- **Étape 5** : RAG + Mistral MLX (95%)
- **Étape 7** : Dashboard Analytics (95%)

### 🚧 EN COURS (Approche Non-Destructive)
- **Pipeline DONUT** : Alternative complémentaire Mistral (Étape 1/7 complétée)
- **Étape 6** : Intégrations externes (20%)
- **Étape 9** : Sécurité + Performance (40%)

**Note** : Tous développements conservent intégralement le pipeline Mistral MLX existant

---

## 🔧 Stack Technologique

### Backend Native
```python
# FastAPI 0.115+ avec uvicorn Apple Silicon
# SQLAlchemy 2.0 + PostgreSQL 15 Homebrew
# Redis 7 (cache + queues)
# Alembic migrations

# OCR Pipeline
# - TrOCR (HuggingFace) ARM64 optimisé
# - Tesseract 5 Homebrew (fallback)
# - LayoutLMv3 (structure)

# IA Apple Silicon
# - Mistral 7B MLX (optimisation M4)
# - ChromaDB standalone
# - Sentence-Transformers ARM64

# Pipeline Alternatif DONUT (en développement)
# - Donut OCR-free (naver-clova-ix/donut-base-finetuned-cord-v2)
# - CamemBERT français (almanach/camembert-base)
# - NER français (Jean-Baptiste/camembert-ner)
```

### Frontend Moderne
```typescript
// Next.js 15 + React 19
// TypeScript strict + Tailwind CSS 4
// Zustand (state) + React Hook Form
// Composants optimisés hot reload
```

---

## 📁 Navigation Rapide - Fichiers Clés

### Configuration & API
```bash
backend/core/config.py         # Configuration principale
backend/main.py               # Point d'entrée FastAPI
backend/api/documents.py      # Upload unifié
backend/api/health.py         # Health checks
```

### Pipeline Documentaire
```bash
backend/ocr/hybrid_ocr.py     # OCR principal
backend/rag/mistral_wrapper.py # Interface Mistral MLX
backend/services/document_classifier.py # Classification
backend/test_models_selection.py # Benchmark DONUT
backend/api/donut_endpoints.py    # API DONUT (planifié)
ai_services/donut_camembert_analyzer.py # Service DONUT (planifié)
```

### Frontend Interface
```bash
frontend/src/app/dashboard/page.tsx       # Dashboard principal
frontend/src/components/documents/        # Upload + liste
frontend/src/components/dashboard/        # Analytics KPI
frontend/src/services/api.ts              # Client API
```

### Services IA
```bash
ai_services/document_analyzer.py         # Service Mistral MLX
ml_models/mistral_7b_mlx/                # Modèles locaux
data/chromadb/                           # Base vectorielle
```

---

## 📊 Fonctionnalités Opérationnelles

### 1. Upload + Traitement Intelligent (Non-Destructif)
- **Drag & Drop** : PDF, images (PNG, JPG, TIFF)
- **Pipeline unifié** : Upload → OCR → [Mistral MLX (défaut) | DONUT (alternatif)] → Classification
- **Toggle utilisateur** : Choix pipeline dans dashboard, Mistral conservé par défaut
- **Performance** : <10 secondes par document
- **Fallback automatique** : Retour vers Mistral en cas d'erreur DONUT

### 2. Classification Automatique
```typescript
Categories = {
  factures, rib, contrats, attestations, 
  courriers, rapports, cartes_transport,
  documents_personnels, non_classes
}
// Score moyen: 89.7% de confiance
```

### 3. Dashboard Analytics
- **KPIs temps réel** : Documents traités, précision OCR
- **Graphiques** : Bar, Line, Pie charts (Recharts)
- **Timeline** : Activité récente
- **Filtres** : Date, catégorie, statut

### 4. RAG + Chat Intelligent  
- **Recherche sémantique** : ChromaDB + embeddings
- **Chat contexte** : Mistral MLX avec sources
- **Performance** : <100ms retrieval, <2s génération

---

## 🧪 Tests Validés

### Scripts Principaux
```bash
cd backend && source venv/bin/activate

# Tests pipeline
python test_ocr_etape3.py        # OCR (82% succès)
python test_rag_etape5.py        # RAG (95% succès)  
python test_models_selection.py # Benchmark DONUT

# Tests spécifiques
pytest tests/                   # Tests unitaires
```

### Validation Documents Réels
- **Factures EDF** : Classification + extraction entités ✅
- **RIB bancaires** : Détection + classement automatique ✅
- **Attestations** : CPAM, CAF détectées ✅

---

## 🔄 Hot Reload Développement

### Workflow Optimisé
```bash
# Démarrage une fois
./start_native.sh

# Développement continu - pas de redémarrage
# - Composants React : HMR instantané (<500ms)
# - API Python : uvicorn --reload automatique (<1s)
# - Styles CSS : Hot reload instantané
```

### Cas Redémarrage Nécessaire
- **Frontend** : Modification `package.json` → `npm install`
- **Backend** : Modification `requirements.txt` → `pip install`
- **Complet** : `./stop_native.sh && ./start_native.sh`

---

## 🛡️ Stabilité & Performance

### Auto-correction Native
- **Services Homebrew** : Démarrage automatique PostgreSQL/Redis
- **Environnements virtuels** : Création automatique si manquants
- **Dépendances** : Vérification et installation auto

### Protection Données
- **Sauvegarde auto** : Lors arrêt dans `logs/backups/YYYYMMDD/`
- **Vérification batch** : Pas d'arrêt si traitements en cours
- **Logs centralisés** : `logs/backend_native.log`, `logs/mistral_native.log`

---

**📈 État :** MVP natif opérationnel - Pipeline Mistral MLX fonctionnel (89.7% précision)  
**🎯 Focus :** Pipeline DONUT alternatif en développement (Étape 1/7 complétée - Modèles validés)  
**🛡️ Approche :** 100% Non-Destructive - Conservation totale de l'existant

*Dernière mise à jour : 27 juillet 2025 - Guidelines + Approche Non-Destructive intégrées*