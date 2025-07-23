# 📄 PRD - Application SaaS de Gestion Administrative Intelligente (OCR + RAG)

## 1. Objectif

Développer une application **SaaS** locale basée sur html et tout autre framework qui permette d'avoir un design moderne qui automatise la **gestion des documents administratifs** pour les professions libérales. L'application doit pouvoir **scanner, identifier, lire et classer automatiquement** tout type de document déposé dans un dossier nommé `OCR`, situé dans le dossier `~/Documents/LEXO_v1`. L'analyse des documents permettra de les indexer dans une **base de connaissances sémantique (RAG)** basée sur **ChromaDB**, interrogeable via interface et commande vocale. Le llm local devra pouvoir être utilisé pour toute tâche administrative du type résumer un texte, faire une facture etc.. (propose des fonctionalités). Il faudra que le modèle puisse devenir plus performant avec le temps.

## 2. Public cible

- Professions libérales (avocats, médecins, comptables, architectes, etc.)
- TPE ou indépendants cherchant à **automatiser** leur gestion documentaire.

## 3. Environnement cible

- Plateforme : macOS (Mac mini M4 – 32 Go RAM unifiée)
- Langage principal : Python (backend + traitement)
- Frameworks front : **Next.js**, **React**, **Tailwind CSS**
- RAG : **ChromaDB**
- LLM : **Mistral 7B MLX**
- OCR : modèles spécialisés Hugging Face (à rechercher)
- STT/Vocal (dernière étape) : Voxtral ou équivalent compatible MLX

## 4. Fonctionnalités principales

### 4.1. 📥 Scan et lecture automatique de documents

- **Dossier surveillé** : `~/Documents/OCR`
- Tous les fichiers déposés (pdf, png, jpg, docx, xlsx...) seront :
  - **Identifiés** par type (métadonnées ou reconnaissance heuristique).Si pas identifiés le document sera découpé par blocs logiques et demandera à l'utilisateur de qualifier le bloc. L'applicatioin devra pouvoir retenir ces informations quand un document du même type lui sera proposé.
  - **Tournés automatiquement** si nécessaire (OCR d’images inclinées ou retournées)
  - **Interprétés** par un pipeline OCR + analyse sémantique (ex : un RIB contient logo + texte, les deux doivent être lus)
  - **Classés automatiquement** dans un sous-dossier `/OCR/[catégorie]` : ex. `factures`, `relevés`, `impôts`, etc.

> ❗ Tous les cas particuliers devront être testés : PDF image sans couche texte, image avec angle de rotation, texte + logo, etc.

### 4.2. 🧠 Indexation intelligente

- Une fois le document lu, les données seront :
  - **Indexées dans ChromaDB** avec tous les métadonnées (nom, date, auteur, source, etc.)
  - **Reliées au modèle Mistral MLX** pour permettre les requêtes RAG
  - Un score de confiance devra être généré pour chaque document

### 4.3. 🔐 Authentification utilisateur

- Page de login avec :
  - Email / mot de passe
  - Backend PostgreSQL
  - Session sécurisée (JWT)
- Préparer architecture multicomptes (versioning utilisateur)

### 4.4. 📊 Dashboard d’administration

- Nombre total de documents
- Documents lus / non lus
- Taux de réussite OCR
- Documents classés par catégorie
- Activité récente

### 4.5. 📁 Classement des documents

- Tous les fichiers analysés sont déplacés dans `/OCR/[catégorie]/nom_du_fichier`
- Le classement est **automatique** mais peut être **corrigé manuellement** (avec apprentissage supervisé)

### 4.6. 📧 Intégration Gmail et Google Calendar

- Connexion à un ou plusieurs comptes Gmail
- Extraction automatique des pièces jointes
- Lecture du contenu de l’email
- Intégration des événements du **Google Calendar** dans le modèle de compréhension du contexte

### 4.7. 🔍 Recherche vocale dans la base documentaire (étape finale)

- L'utilisateur pourra **poser une question à voix haute**
- Le système utilisera :
  - STT (Speech-to-Text, ex : Voxtral)
  - Requête RAG sur ChromaDB + Mistral MLX
  - TTS (Text-to-Speech) pour la réponse (ex : XTTS, Kyutai ou Coqui)

## 5. Recherche de modèles spécialisés

Une recherche approfondie sur **Hugging Face** est obligatoire pour :

- OCR français (Tesseract+layoutLM ? Donut ? TrOCR ?)
- Classificateurs documentaires (ex. DocFormer, LayoutXLM)
- Détection de logo / image dans document
- Modèles OCR robustes aux documents complexes (rotation, bruit, qualité faible)

## 6. Arborescence des fichiers

```plaintext
~/Documents/LEXO_v1
├── OCR/
│   ├── factures/
│   ├── impots/
│   ├── pièces_identité/
│   ├── rib/
│   └── non_classés/
├── IA_Administratif/
│   ├── chromadb/
│   ├── mistral_mlx/
│   ├── postgres/
│   ├── frontend/
│   ├── backend/
│   └── logs/