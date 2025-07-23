# 🗄️ Migrations Alembic pour LEXO v1

## 📋 Vue d'ensemble

Ce dossier contient les migrations de base de données pour LEXO v1 utilisant Alembic.

## 🔧 Configuration

- **Base de données** : PostgreSQL
- **ORM** : SQLAlchemy 2.0 (async)
- **Driver Alembic** : psycopg2 (sync)
- **Modèles** : Définis dans `alembic_models.py`

## 📚 Commandes Alembic

### Créer une nouvelle migration
```bash
# Migration automatique (nécessite DB active)
alembic revision --autogenerate -m "Description de la migration"

# Migration manuelle
alembic revision -m "Description de la migration"
```

### Appliquer les migrations
```bash
# Vers la dernière version
alembic upgrade head

# Vers une version spécifique
alembic upgrade <revision_id>

# Une version en avant
alembic upgrade +1
```

### Revenir en arrière
```bash
# Une version en arrière
alembic downgrade -1

# Vers une version spécifique
alembic downgrade <revision_id>

# Vers la base (ATTENTION: supprime tout)
alembic downgrade base
```

### Informations
```bash
# Version actuelle
alembic current

# Historique des migrations
alembic history

# Montrer les différences
alembic show <revision_id>
```

### Générer du SQL (sans appliquer)
```bash
# Pour voir le SQL qui sera exécuté
alembic upgrade head --sql

# Pour une migration spécifique
alembic upgrade <revision_id> --sql
```

## 📝 Structure des migrations

### Migration initiale
- **ID**: `b342af89685a`
- **Description**: Tables `users` et `documents`
- **Contenu**:
  - Table `users` avec authentification et rôles
  - Table `documents` avec métadonnées OCR
  - Index pour optimiser les requêtes

### Modèles inclus
1. **User** : Utilisateurs avec rôles (admin, user, readonly)
2. **Document** : Documents avec OCR et classification

## 🔍 Validation des migrations

### Avant de créer une migration
1. Vérifier que PostgreSQL est démarré
2. Tester la connexion : `alembic current`
3. Comparer avec les modèles actuels

### Après création
1. Vérifier le fichier de migration généré
2. Tester upgrade : `alembic upgrade head`
3. Tester downgrade : `alembic downgrade -1`
4. Tester upgrade final : `alembic upgrade head`

## ⚠️ Bonnes pratiques

### DO ✅
- Toujours créer des migrations pour les changements de schéma
- Tester les migrations sur une copie de production
- Inclure les migrations dans les commits Git
- Commenter les migrations complexes
- Faire des sauvegardes avant les migrations importantes

### DON'T ❌
- Ne jamais éditer une migration déjà déployée
- Ne pas supprimer les fichiers de migration
- Ne pas faire de migrations avec données en production sans backup
- Ne pas oublier de créer les index nécessaires

## 🚀 Workflow de développement

### Nouveau modèle
1. Créer/modifier le modèle dans `models/`
2. Mettre à jour `alembic_models.py` 
3. Créer la migration : `alembic revision --autogenerate -m "Add model"`
4. Vérifier et ajuster la migration générée
5. Appliquer : `alembic upgrade head`

### Modification de modèle
1. Modifier le modèle
2. Mettre à jour `alembic_models.py`
3. Créer la migration
4. **IMPORTANT** : Gérer la migration des données existantes
5. Tester thoroughly avant déploiement

## 🐛 Dépannage

### "No such table" errors
```bash
# Vérifier l'état actuel  
alembic current

# Si pas de migration appliquée
alembic upgrade head
```

### "Revision not found"
```bash
# Vérifier l'historique
alembic history

# Reset vers une version connue
alembic stamp <revision_id>
```

### Erreurs de connexion DB
1. Vérifier que PostgreSQL est démarré
2. Vérifier la config dans `core/config.py`
3. Tester la connexion manuellement

### Conflits de migration
```bash
# Merger les branches de migration
alembic merge <rev1> <rev2> -m "Merge migrations"
```

## 📊 Monitoring

### Logs à surveiller
- Temps d'exécution des migrations
- Erreurs de contraintes
- Warnings sur les types de données

### Métriques importantes
- Taille des tables après migration
- Performance des nouvelles requêtes  
- Impact sur les index existants

---

**Note** : Ce système de migration est critical pour la production. Toujours tester sur un environnement de staging avant le déploiement.