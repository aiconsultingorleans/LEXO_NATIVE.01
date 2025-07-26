# 🎨 LEXO_NATIVE.01 - Frontend Next.js Natif

Interface utilisateur moderne pour l'assistant IA administratif LEXO.

## 🚀 Architecture Native

- **Framework** : Next.js 15 + React 19
- **Styling** : Tailwind CSS 4
- **État** : Zustand (performance native)
- **Types** : TypeScript strict
- **Démarrage** : npm dev natif (port 3000)

## 📋 Fonctionnalités

### 🏠 Dashboard
- **KPIs temps réel** : Documents traités, précision OCR
- **Timeline activité** : Événements récents colorés
- **Graphiques** : Charts avec Recharts
- **Responsive** : Mobile-first design

### 📄 Upload Documents
- **Drag & Drop** : PDF, images (PNG, JPG, TIFF)
- **Pipeline unifié** : Upload → OCR → IA → Classification
- **Feedback temps réel** : Barres de progression
- **Résultats enrichis** : Métadonnées extraites

### 🔍 Recherche Sémantique
- **Interface RAG** : Chat avec contexte
- **Recherche documents** : Vectorielle avec ChromaDB
- **Sources citées** : Références automatiques

## 🔧 Développement

### Démarrage rapide
```bash
cd ~/Documents/LEXO_v1/IA_Administratif/frontend
npm run dev
# Interface disponible : http://localhost:3000
```

### Hot Module Replacement
- **Modifications React** : Rechargement instantané (<500ms)
- **Styles CSS** : Mise à jour automatique
- **TypeScript** : Vérification types en temps réel

### Structure des composants
```
src/
├── components/
│   ├── dashboard/       # Dashboard & analytics
│   ├── documents/       # Upload & liste documents  
│   ├── ui/             # Composants base (buttons, etc.)
│   └── layout/         # Navigation & layout
├── hooks/              # Hooks personnalisés
├── lib/               # Utilitaires & API clients
├── stores/            # État Zustand
└── types/             # Types TypeScript
```

## 🎯 Composants Clés

### DocumentUpload
- Interface drag & drop moderne
- Support multi-formats
- Validation côté client
- Feedback progression temps réel

### DashboardWidget  
- KPIs dynamiques (documents traités, précision)
- Graphiques interactifs avec Recharts
- Filtres avancés (date, catégorie)

### VirtualizedDocumentList
- Liste performante (>1000 documents)
- Recherche & filtres instantanés
- Prévisualisation documents

## 🔄 État Global (Zustand)

### DocumentStore
```typescript
interface DocumentStore {
  documents: Document[]
  uploadProgress: number
  searchQuery: string
  // Actions
  uploadDocument: (file: File) => Promise<void>
  searchDocuments: (query: string) => void
}
```

### AnalyticsStore
```typescript
interface AnalyticsStore {
  kpis: KPIData
  recentActivity: ActivityEvent[]
  // Actions
  refreshKPIs: () => Promise<void>
}
```

## 🧪 Tests

```bash
# Tests unitaires composants
npm run test

# Tests E2E (si configurés)
npm run test:e2e

# Vérification TypeScript
npm run type-check
```

## 📱 Responsive Design

- **Mobile-first** : Design adaptatif
- **Breakpoints** : Tailwind CSS natifs
- **Touch-friendly** : Interactions tactiles optimisées
- **Performance** : Optimisé Apple Silicon

## 🔧 Scripts Disponibles

```bash
npm run dev        # Démarrage développement
npm run build      # Build production
npm run start      # Serveur production
npm run lint       # Linting ESLint
npm run type-check # Vérification TypeScript
```

## 🎨 Design System

### Couleurs
- **Primaire** : Bleu moderne (#3B82F6)
- **Secondaire** : Gris nuancé (#64748B)
- **Succès** : Vert (#10B981)
- **Erreur** : Rouge (#EF4444)

### Typographie
- **Titres** : Inter Bold
- **Corps** : Inter Regular
- **Code** : JetBrains Mono

### Icônes
- **Lucide React** : Icônes modernes et cohérentes
- **Héroicons** : Icônes système

## 🚀 Performance

### Optimisations
- **Lazy loading** : Composants et routes
- **Code splitting** : Bundles optimisés
- **Image optimization** : Next.js Image
- **Caching** : SWR pour données API

### Métriques cibles
- **First Paint** : <1s
- **Interaction** : <100ms
- **Bundle size** : <1MB gzippé

## 🔗 Intégration API

### Client HTTP
```typescript
// lib/api-client.ts
const apiClient = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  timeout: 30000
})
```

### Endpoints utilisés
- `POST /documents/upload-and-process` - Upload unifié
- `GET /documents/` - Liste documents
- `POST /rag/search` - Recherche sémantique
- `GET /monitoring/stats` - Analytics

## 📊 Monitoring

### Développement
- **Console logs** : Structurés et colorés
- **Error boundaries** : Capture erreurs React
- **Performance** : React DevTools

### Production
- **Error tracking** : Intégration Sentry possible
- **Analytics** : Métriques utilisateur
- **Performance** : Core Web Vitals

---

**🎯 Objectif** : Interface moderne, performante et intuitive pour l'assistant IA administratif LEXO_NATIVE.01

*Architecture native macOS - Optimisé Apple Silicon M4*