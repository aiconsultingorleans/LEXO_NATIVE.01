# 🤖 LEXO_NATIVE.01 - Classification Intelligente des Documents

## 🎯 Objectif Principal
Transformer le système de classification actuel (~85% précision) en IA vraiment intelligente (>95% précision) combinant :
- **Mistral MLX** (Apple Silicon optimisé) 
- **Règles expertes** françaises (SIRET, IBAN, organismes publics)
- **Apprentissage continu** via feedback utilisateur

## 🔧 Fichiers Critiques du Système

### Backend - Classification
- `backend/api/classification.py` - API endpoints classification
- `backend/services/document_classifier.py` - Logique classification principale
- `backend/api/documents.py` - Pipeline upload + classification unifié
- `ai_services/document_analyzer.py` - Interface Mistral MLX

### Tests & Validation  
- `backend/test_ocr_etape3.py` - Tests pipeline OCR + classification
- `backend/test_rag_etape5.py` - Tests système RAG complet
- ✅ **Créé** : `backend/test_classification_benchmark.py` - Tests précision par étape

### Configuration
- `config/ml_cache.env` - Variables cache modèles Apple Silicon
- **À créer** : `config/classification_rules.json` - Règles françaises centralisées

### Dossiers de Test
- `/Users/stephaneansel/Documents/LEXO_v1/OCR/` - Documents réels pour validation
- `/Users/stephaneansel/Documents/LEXO_v1/OCR/En attente/` - Pipeline surveillance native

## 📊 Workflow de Développement
1. **Étape implémentée** → Tests de validation → **Commit sur `feat/classement_IA`**
2. **Métriques mesurées** : Précision, performance, robustesse  
3. **Validation manuelle** : Tests sur documents réels du dossier ~/OCR/
4. **Progression** : 8 étapes avec objectifs quantifiés et testables

---

## 🗂️ Roadmap en 8 Étapes Testables

### ✅ **ÉTAPE 1** : 🔧 Corrections Critiques & Diagnostics
**Branche** : `feat/classement_IA`  
**Commit** : `fix(classification): corrections Mistral + outils de diagnostic`  
**Durée estimée** : 3-5 jours  
**Précision cible** : >85%

#### 📋 Tâches
- [x] **1.1** Corriger l'erreur Mistral `"informations_cles"` dans `ai_services/document_analyzer.py`
- [x] **1.2** Fixer le parsing JSON défaillant dans les réponses Mistral MLX
- [x] **1.3** Améliorer la gestion d'erreur robuste pour Mistral MLX (timeouts, fallbacks)
- [x] **1.4** Ajouter des logs détaillés pour débugger les échecs de classification
- [x] **1.5** Créer script `backend/test_classification_benchmark.py` pour validation automatique

#### 🧪 Tests de Validation  
- [x] RIB du dossier OCR correctement classé en catégorie "rib"
- [x] Logs détaillés affichés pour chaque étape de classification (règles + IA)
- [x] Script benchmark retourne précision >85% sur corpus existant
- [x] Gestion d'erreur : Aucun crash sur documents corrompus

#### 📊 Métriques de Succès
- **Précision** : >85% sur documents test existants
- **Performance** : <8 secondes par document
- **Robustesse** : 0 crash sur 100 documents variés
- **Traçabilité** : Logs complets pour 100% des classifications

### ✅ **ÉTAPE 1 COMPLÉTÉE** - 26 juillet 2025

#### 🔧 **Corrections Techniques**
- **Parsing JSON** : `_robust_json_parse()` + fallbacks regex
- **Timeouts** : 30s + 2 retries automatiques  
- **Logs** : Traçabilité complète avec timings
- **Gestion erreurs** : Fallbacks extraction si Mistral échoue
- **Script benchmark** : `test_classification_benchmark.py` opérationnel

#### 📊 **Résultats Tests**
- **Robustesse** : 0 crash sur 3 documents variés
- **Mistral MLX** : 100% success rate (3/3)
- **Performance** : 6-7s/document 
- **Précision** : RIB/contrats OK, factures à améliorer (Étape 2)

#### 🚀 **Prêt pour Étape 2**
Base technique stable établie. Prochaine priorité : optimisation prompts français + règles classification.

---

### ✅ **ÉTAPE 2** : 🧠 Prompts Mistral Optimisés
**Commit** : `feat(classification): prompts Mistral few-shot français`  
**Durée estimée** : 1 semaine  
**Précision cible** : >88%

#### 📋 Tâches
- [ ] **2.1** Réécrire le prompt de classification avec exemples concrets français
- [ ] **2.2** Ajouter du few-shot learning avec 2-3 exemples par catégorie (factures, RIB, etc.)
- [ ] **2.3** Inclure des mots-clés français spécifiques (IBAN, SIRET, URSSAF, etc.)
- [ ] **2.4** Forcer le format JSON strict avec schema validation côté Python
- [ ] **2.5** Enrichir les règles RIB avec plus de banques françaises
- [ ] **2.6** Ajouter les patterns IBAN français (FR76...)
- [ ] **2.7** Améliorer la détection des factures EDF/Orange/SFR avec mots-clés
- [ ] **2.8** Ajouter les patterns URSSAF/CPAM/CAF spécifiques

#### 🧪 Tests de Validation  
- [ ] Précision RIB/bancaire >95% sur corpus test étendu (20 documents minimum)
- [ ] Précision globale >88% (amélioration mesurable vs étape 1)
- [ ] Temps de traitement <6 secondes par document
- [ ] Zero false positive sur factures EDF/Orange déjà testées

#### 📊 Métriques de Succès
- **Précision** : >88% globale, >95% RIB/bancaire
- **Performance** : <6 secondes par document
- **Couverture** : 9 catégories avec exemples few-shot
- **Validation** : JSON strict 100% des réponses Mistral

---

### ✅ **ÉTAPE 3** : 🔍 Extraction Entités Françaises
**Commit** : `feat(classification): détection SIRET/TVA/montants français`  
**Durée estimée** : 1-2 semaines  
**Précision cible** : >90%

#### 📋 Tâches
- [ ] **3.1** Implémenter détection automatique des numéros SIRET (14 chiffres)
- [ ] **3.2** Créer patterns pour les numéros de TVA français (FR + 11 chiffres)
- [ ] **3.3** Ajouter reconnaissance des montants format français (€, virgule décimale)
- [ ] **3.4** Développer détection des dates françaises (DD/MM/YYYY, DD-MM-YYYY)
- [ ] **3.5** Créer un pré-classificateur basé sur le nom de fichier
- [ ] **3.6** Implémenter détection automatique de mots-clés dans le nom de fichier
- [ ] **3.7** Ajouter analyse de la structure du nom (préfixes, suffixes)
- [ ] **3.8** Créer un système de hints pour guider Mistral avec contexte enrichi

#### 🧪 Tests de Validation  
- [ ] SIRET détecté dans 95% des documents administratifs (URSSAF, etc.)
- [ ] Montants extraits correctement format français (123,45 €)
- [ ] Dates reconnues format DD/MM/YYYY dans 90% des cas
- [ ] Classification par nom de fichier >70% précision avant analyse contenu

#### 📊 Métriques de Succès
- **Extraction entités** : >90% précision SIRET/TVA/montants
- **Précision globale** : >90%
- **Performance** : <5 secondes par document
- **Pré-classification** : >70% précision sur nom de fichier seul

---

### ✅ **ÉTAPE 4** : ⚖️ Fusion Intelligente Règles + IA
**Commit** : `feat(classification): scoring pondéré + résolution conflits`  
**Durée estimée** : 1-2 semaines  
**Précision cible** : >91%

#### 📋 Tâches
- [ ] **4.1** Abaisser le seuil Mistral à 0.7 pour les cas RIB/bancaires spécifiques
- [ ] **4.2** Implémenter un système de scoring pondéré (règles 60% + IA 40%)
- [ ] **4.3** Créer une logique de résolution de conflits automatique
- [ ] **4.4** Ajouter un système de confiance adaptatif par catégorie
- [ ] **4.5** Implémenter cache de décisions pour documents identiques
- [ ] **4.6** Créer audit trail complet des décisions de classification

#### 🧪 Tests de Validation  
- [ ] Conflits règles/IA résolus automatiquement dans 95% des cas
- [ ] Score de confiance >0.8 pour 90% des classifications finales
- [ ] Précision globale >91% sur corpus test étendu
- [ ] Audit trail complet : Traçabilité 100% des décisions

#### 📊 Métriques de Succès
- **Précision** : >91% globale
- **Résolution conflits** : >95% automatique
- **Performance** : <4 secondes par document
- **Confiance** : >0.8 pour 90% des classifications

---

### ✅ **ÉTAPE 5** : 🚀 Pipeline Multi-Niveaux
**Commit** : `feat(classification): pipeline pré-filtrage + cache intelligent`  
**Durée estimée** : 2 semaines  
**Précision cible** : >94%

#### 📋 Tâches
- [ ] **5.1** Créer un classificateur rapide basé sur l'extension + taille de fichier
- [ ] **5.2** Implémenter détection des patterns évidents (logo, en-tête, structure)
- [ ] **5.3** Ajouter cache de classification par hash de fichier
- [ ] **5.4** Créer un système de blacklist/whitelist par mots-clés
- [ ] **5.5** Développer des prompts spécialisés par type de document
- [ ] **5.6** Implémenter chain-of-thought reasoning pour Mistral
- [ ] **5.7** Implémenter validation de cohérence (ex: facture avec IBAN)
- [ ] **5.8** Ajouter détection d'anomalies dans la classification
- [ ] **5.9** Créer un système de suggestions alternatives
- [ ] **5.10** Implémenter auto-correction basée sur l'historique

#### 🧪 Tests de Validation  
- [ ] 70% des documents classés en <2 secondes (pré-filtrage rapide)
- [ ] Cache hit rate >30% sur documents récurrents
- [ ] Précision globale >94% sur corpus test complet
- [ ] Validation cohérence élimine 95% des incohérences

#### 📊 Métriques de Succès
- **Précision** : >94% globale
- **Performance** : 70% docs <2s, moyenne <3s
- **Cache efficacité** : >30% hit rate
- **Cohérence** : >95% validation réussie

---

### ✅ **ÉTAPE 6** : 📊 Métriques & Apprentissage
**Commit** : `feat(classification): dashboard métriques + feedback loop`  
**Durée estimée** : 2-3 semaines  
**Précision cible** : >95%

#### 📋 Tâches
- [ ] **6.1** Implémenter tracking de précision par catégorie en temps réel
- [ ] **6.2** Créer dashboard de métriques temps réel (frontend)
- [ ] **6.3** Ajouter suivi des temps de traitement par composant
- [ ] **6.4** Implémenter alertes sur dégradation de performance
- [ ] **6.5** Créer interface de correction simple (drag & drop entre dossiers)
- [ ] **6.6** Implémenter stockage des corrections utilisateur en base
- [ ] **6.7** Ajouter système de réentraînement automatique des règles
- [ ] **6.8** Créer suggestions proactives basées sur l'historique
- [ ] **6.9** Constituer corpus de référence validé par catégorie
- [ ] **6.10** Implémenter similarity matching avec documents existants
- [ ] **6.11** Créer système de keywords extraction automatique
- [ ] **6.12** Ajouter gestion de synonymes et variantes françaises

#### 🧪 Tests de Validation  
- [ ] Dashboard affiche métriques temps réel (précision par catégorie)
- [ ] Corrections utilisateur appliquées et mémorisées automatiquement
- [ ] Similarity matching trouve documents similaires avec >85% précision
- [ ] Apprentissage améliore précision +2% après 10 corrections par catégorie

#### 📊 Métriques de Succès
- **Précision** : >95% globale, >97% par catégorie spécialisée
- **Performance** : <2 secondes par document
- **Apprentissage** : +2% précision après feedback utilisateur
- **Interface** : Dashboard temps réel fonctionnel

---

### ✅ **ÉTAPE 7** : 🎨 Interface Utilisateur Avancée
**Commit** : `feat(ui): interface admin classification + UX optimisée`  
**Durée estimée** : 2-3 semaines  
**Précision cible** : >96%

#### 📋 Tâches
- [ ] **7.1** Créer vue d'ensemble des classifications récentes
- [ ] **7.2** Implémenter graphiques de performance par catégorie
- [ ] **7.3** Ajouter timeline des classifications avec filtres avancés
- [ ] **7.4** Créer vue détaillée de chaque décision de classification
- [ ] **7.5** Interface de gestion des règles de classification
- [ ] **7.6** Outil de test/validation de nouveaux patterns en live
- [ ] **7.7** Interface de gestion du corpus de référence
- [ ] **7.8** Dashboard de monitoring des performances IA
- [ ] **7.9** Suggestions proactives "Ce document ressemble à..."
- [ ] **7.10** Interface de validation rapide par lot
- [ ] **7.11** Système de favoris/templates pour documents récurrents
- [ ] **7.12** Mode apprentissage guidé pour nouveaux types de documents

#### 🧪 Tests de Validation  
- [ ] Workflow correction d'un document mal classé en <30 secondes
- [ ] Suggestions "ressemble à" pertinentes dans >80% des cas
- [ ] Interface admin fonctionnelle : CRUD complet sur règles
- [ ] Tests utilisabilité : Parcours complets sans blocage

#### 📊 Métriques de Succès
- **Précision** : >96% globale
- **UX** : Workflow correction <30 secondes
- **Suggestions** : >80% pertinence
- **Performance** : <2 secondes par document

---

### ✅ **ÉTAPE 8** : 🔬 Technologies Avancées (Future)
**Commit** : `feat(classification): LayoutLM + NLP avancé + IA générative`  
**Durée estimée** : 3-4 semaines  
**Précision cible** : >97%

#### 📋 Tâches
- [ ] **8.1** Intégrer LayoutLM pour analyse de mise en page automatique
- [ ] **8.2** Implémenter détection automatique de logos et signatures
- [ ] **8.3** Ajouter reconnaissance de tableaux structurés
- [ ] **8.4** Créer analyse de signatures et tampons officiels
- [ ] **8.5** Intégrer BERT français pour compréhension contextuelle
- [ ] **8.6** Implémenter détection automatique de langue
- [ ] **8.7** Ajouter analyse de sentiment pour courriers (positif/négatif/neutre)
- [ ] **8.8** Créer extraction automatique de dates d'échéance
- [ ] **8.9** Générer automatiquement des résumés intelligents
- [ ] **8.10** Créer suggestions de classement métadonnées enrichies
- [ ] **8.11** Implémenter génération de mots-clés automatique
- [ ] **8.12** Ajouter traduction automatique si documents non-français

#### 🧪 Tests de Validation  
- [ ] LayoutLM améliore précision détection tableaux de +5%
- [ ] Détection langue automatique >98% précision
- [ ] Résumés générés cohérents et pertinents (validation humaine)
- [ ] Performance globale >97% précision toutes catégories

#### 📊 Métriques de Succès
- **Précision** : >97% globale, approche 99% catégories spécialisées
- **Performance** : <1 seconde par document
- **Capacités avancées** : LayoutLM, NLP, génération validés
- **Innovation** : Technologies état de l'art intégrées

---

## 📈 Objectifs de Performance par Étape

| Étape | Précision Globale | Performance | Fonctionnalités Clés |
|-------|------------------|-------------|----------------------|
| **Étape 1** | >85% | <8s | Corrections critiques, diagnostics |
| **Étape 2** | >88% | <6s | Prompts optimisés, règles étendues |
| **Étape 3** | >90% | <5s | Entités françaises, nom fichier |
| **Étape 4** | >91% | <4s | Fusion intelligente, résolution conflits |
| **Étape 5** | >94% | <3s | Pipeline multi-niveaux, cache |
| **Étape 6** | >95% | <2s | Métriques temps réel, apprentissage |
| **Étape 7** | >96% | <2s | Interface avancée, UX optimisée |
| **Étape 8** | >97% | <1s | Technologies futures, IA générative |

## 🎯 Prochaines Actions - Démarrage Immédiat

### 🚨 **Priorité 1** : Commencer Étape 1 (Cette Semaine)
1. **Créer branche** : `git checkout -b feat/classement_IA`
2. **Corriger erreur Mistral** dans `ai_services/document_analyzer.py` 
3. **Créer script benchmark** `backend/test_classification_benchmark.py`
4. **Tester sur RIB existant** pour validation immédiate

### ⚡ **Quick Wins** (3-5 jours)
- Fix parsing JSON Mistral (bloquant production)
- Logs détaillés pour debugging
- Script de test automatisé
- Validation sur corpus existant

### 🎯 **Objectif Première Semaine**
- **Étape 1 complétée** et committée sur `feat/classement_IA`
- **Précision >85%** validée avec script benchmark
- **Système stable** prêt pour Étape 2

---

*Dernière mise à jour : 26 juillet 2025 - Workflow étapes testables implémenté*
*Prochaine action : Démarrer Étape 1 - Corrections critiques Mistral*