#!/usr/bin/env python3
"""
🚀 LEXO v1 - Migration des Modèles ML vers Cache Local
====================================================

Ce script migre tous les modèles ML depuis le cache HuggingFace système
vers le cache local LEXO pour éliminer les téléchargements au démarrage.

Usage:
    python migrate_models_to_local_cache.py [--dry-run] [--force]
    
Arguments:
    --dry-run    : Simulation sans copie réelle
    --force      : Écraser les modèles existants
"""

import os
import sys
import shutil
import hashlib
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ModelCacheMigrator:
    """Gestionnaire de migration du cache des modèles ML"""
    
    # Modèles requis par LEXO v1
    REQUIRED_MODELS = {
        'transformers': [
            {
                'hf_name': 'microsoft--trocr-base-printed',
                'local_name': 'trocr-base-printed',
                'description': 'OCR TrOCR pour texte imprimé',
                'size_expected': '1.2GB'
            },
            {
                'hf_name': 'sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2',
                'local_name': 'paraphrase-multilingual-MiniLM-L12-v2', 
                'description': 'Embeddings multilingues pour RAG',
                'size_expected': '458MB'
            }
        ],
        'spacy': [
            {
                'name': 'fr_core_news_sm',
                'description': 'Modèle spaCy français pour NER',
                'size_expected': '15MB'
            }
        ]
    }
    
    def __init__(self, dry_run: bool = False, force: bool = False):
        """
        Initialise le migrateur
        
        Args:
            dry_run: Mode simulation sans actions réelles
            force: Écraser les modèles existants
        """
        self.dry_run = dry_run
        self.force = force
        
        # Chemins de cache
        self.project_root = Path(__file__).parent.parent
        self.hf_cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
        self.local_cache_dir = self.project_root / 'ml_models'
        
        # Sous-répertoires
        self.transformers_cache = self.local_cache_dir / 'transformers'
        self.spacy_cache = self.local_cache_dir / 'spacy'
        
        # Stats de migration
        self.stats = {
            'models_found': 0,
            'models_migrated': 0,
            'total_size_copied': 0,
            'errors': []
        }
    
    def validate_environment(self) -> bool:
        """Valide l'environnement de migration"""
        logger.info("🔍 Validation de l'environnement...")
        
        # Vérifier cache HuggingFace système
        if not self.hf_cache_dir.exists():
            logger.error(f"❌ Cache HuggingFace non trouvé: {self.hf_cache_dir}")
            return False
        
        logger.info(f"✅ Cache HuggingFace système: {self.hf_cache_dir}")
        
        # Créer répertoires locaux si nécessaire
        if not self.dry_run:
            self.local_cache_dir.mkdir(exist_ok=True)
            self.transformers_cache.mkdir(exist_ok=True)
            self.spacy_cache.mkdir(exist_ok=True)
            logger.info(f"✅ Cache local préparé: {self.local_cache_dir}")
        
        return True
    
    def find_model_in_cache(self, hf_model_name: str) -> Optional[Path]:
        """Trouve un modèle dans le cache HuggingFace système"""
        model_path = self.hf_cache_dir / f"models--{hf_model_name}"
        
        if not model_path.exists():
            logger.warning(f"  ❌ Modèle manquant: {hf_model_name}")
            return None
        
        # Trouver le dernier snapshot
        snapshots_dir = model_path / "snapshots"
        if not snapshots_dir.exists():
            logger.warning(f"  ❌ Pas de snapshots pour: {hf_model_name}")
            return None
        
        # Prendre le premier (et généralement seul) snapshot
        snapshots = list(snapshots_dir.iterdir())
        if not snapshots:
            logger.warning(f"  ❌ Aucun snapshot disponible: {hf_model_name}")
            return None
        
        # Utiliser le snapshot le plus récent
        latest_snapshot = max(snapshots, key=lambda p: p.stat().st_mtime)
        logger.info(f"  ✅ Modèle trouvé: {hf_model_name} (snapshot: {latest_snapshot.name[:8]}...)")
        
        return latest_snapshot
    
    def get_directory_size(self, path: Path) -> int:
        """Calcule la taille totale d'un répertoire"""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def format_size(self, size_bytes: int) -> str:
        """Formate une taille en bytes en format lisible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"
    
    def copy_model_with_progress(self, source: Path, destination: Path, model_name: str) -> bool:
        """Copie un modèle avec barre de progression"""
        try:
            if destination.exists() and not self.force:
                logger.info(f"  ⚠️  Modèle déjà présent: {model_name} (utilisez --force pour écraser)")
                return True
            
            if self.dry_run:
                size = self.get_directory_size(source)
                logger.info(f"  🔄 [DRY-RUN] Copierait {model_name}: {self.format_size(size)}")
                return True
            
            # Supprimer destination si existe et force activé
            if destination.exists() and self.force:
                logger.info(f"  🗑️  Suppression ancienne version: {model_name}")
                shutil.rmtree(destination)
            
            # Créer répertoire parent
            destination.parent.mkdir(parents=True, exist_ok=True)
            
            # Copie avec timing
            start_time = time.time()
            logger.info(f"  🔄 Copie en cours: {model_name}...")
            
            shutil.copytree(source, destination)
            
            copy_time = time.time() - start_time
            size = self.get_directory_size(destination)
            
            logger.info(f"  ✅ Modèle copié: {model_name}")
            logger.info(f"     📊 Taille: {self.format_size(size)}")
            logger.info(f"     ⏱️  Temps: {copy_time:.2f}s")
            
            self.stats['total_size_copied'] += size
            return True
            
        except Exception as e:
            error_msg = f"Erreur copie {model_name}: {str(e)}"
            logger.error(f"  ❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
    
    def migrate_transformers_models(self) -> bool:
        """Migre les modèles HuggingFace/Transformers"""
        logger.info("🤖 Migration des modèles Transformers...")
        
        success_count = 0
        
        for model_info in self.REQUIRED_MODELS['transformers']:
            hf_name = model_info['hf_name']
            local_name = model_info['local_name']
            description = model_info['description']
            
            logger.info(f"📦 Traitement: {description}")
            
            # Trouver dans cache système
            source_path = self.find_model_in_cache(hf_name)
            if not source_path:
                continue
            
            # Définir destination
            destination_path = self.transformers_cache / local_name
            
            # Copier
            if self.copy_model_with_progress(source_path, destination_path, local_name):
                success_count += 1
                self.stats['models_migrated'] += 1
        
        logger.info(f"✅ Modèles Transformers migrés: {success_count}/{len(self.REQUIRED_MODELS['transformers'])}")
        return success_count == len(self.REQUIRED_MODELS['transformers'])
    
    def migrate_spacy_models(self) -> bool:
        """Migre les modèles spaCy"""
        logger.info("🔤 Migration des modèles spaCy...")
        
        try:
            import spacy
            
            # Trouver l'installation spaCy
            spacy_data_dir = Path(spacy.util.get_data_path())
            
            success_count = 0
            
            for model_info in self.REQUIRED_MODELS['spacy']:
                model_name = model_info['name']
                description = model_info['description']
                
                logger.info(f"📦 Traitement: {description}")
                
                # Trouver modèle spaCy
                source_path = spacy_data_dir / model_name
                
                if not source_path.exists():
                    logger.warning(f"  ❌ Modèle spaCy non trouvé: {model_name}")
                    logger.info(f"     💡 Installer avec: python -m spacy download {model_name}")
                    continue
                
                # Destination
                destination_path = self.spacy_cache / model_name
                
                # Copier
                if self.copy_model_with_progress(source_path, destination_path, model_name):
                    success_count += 1
                    self.stats['models_migrated'] += 1
            
            logger.info(f"✅ Modèles spaCy migrés: {success_count}/{len(self.REQUIRED_MODELS['spacy'])}")
            return success_count > 0
            
        except ImportError:
            logger.warning("⚠️  spaCy non installé - modèles spaCy ignorés")
            return True
        except Exception as e:
            logger.error(f"❌ Erreur migration spaCy: {e}")
            return False
    
    def verify_migrated_models(self) -> bool:
        """Vérifie l'intégrité des modèles migrés"""
        if self.dry_run:
            logger.info("🔍 [DRY-RUN] Vérification des modèles simulée")
            return True
        
        logger.info("🔍 Vérification des modèles migrés...")
        
        all_valid = True
        
        # Vérifier modèles Transformers
        for model_info in self.REQUIRED_MODELS['transformers']:
            local_name = model_info['local_name']
            model_path = self.transformers_cache / local_name
            
            if model_path.exists():
                # Vérifier fichiers essentiels (TrOCR utilise safetensors)
                essential_files = ['config.json']
                model_files = ['model.safetensors', 'pytorch_model.bin']  # L'un des deux doit être présent
                
                # Vérifier config obligatoire
                config_valid = (model_path / 'config.json').exists()
                if not config_valid:
                    logger.error(f"  ❌ config.json manquant: {local_name}")
                    all_valid = False
                    continue
                
                # Vérifier qu'au moins un fichier de modèle existe
                model_file_valid = any((model_path / f).exists() for f in model_files)
                if not model_file_valid:
                    logger.error(f"  ❌ Fichier de modèle manquant: {local_name} (cherché: {model_files})")
                    all_valid = False
                    continue
                
                logger.info(f"  ✅ Modèle valide: {local_name}")
            else:
                logger.error(f"  ❌ Modèle manquant: {local_name}")
                all_valid = False
        
        # Vérifier modèles spaCy
        for model_info in self.REQUIRED_MODELS['spacy']:
            model_name = model_info['name']
            model_path = self.spacy_cache / model_name
            
            if model_path.exists():
                logger.info(f"  ✅ Modèle spaCy: {model_name}")
            else:
                logger.warning(f"  ⚠️  Modèle spaCy manquant: {model_name}")
        
        return all_valid
    
    def generate_cache_config(self) -> None:
        """Génère la configuration de cache pour Docker"""
        if self.dry_run:
            logger.info("📝 [DRY-RUN] Configuration de cache simulée")
            return
        
        logger.info("📝 Génération de la configuration de cache...")
        
        config_content = f"""# 🚀 LEXO v1 - Configuration Cache ML Local
# Généré automatiquement par migrate_models_to_local_cache.py

# Variables d'environnement pour cache local uniquement
TRANSFORMERS_CACHE=/app/ml_models/transformers
HF_MODELS_CACHE=/app/ml_models/transformers
HF_HUB_CACHE=/app/ml_models/transformers
SPACY_DATA_DIR=/app/ml_models/spacy

# Forcer utilisation cache local (pas de téléchargement)
HF_OFFLINE=1
TRANSFORMERS_OFFLINE=1

# Désactiver télémétrie
HF_HUB_DISABLE_TELEMETRY=1
"""
        
        config_path = self.project_root / 'config' / 'ml_cache.env'
        config_path.parent.mkdir(exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)
        
        logger.info(f"✅ Configuration sauvée: {config_path}")
    
    def run_migration(self) -> bool:
        """Exécute la migration complète"""
        logger.info("🚀 LEXO v1 - Migration des Modèles ML vers Cache Local")
        logger.info("=" * 60)
        
        if self.dry_run:
            logger.info("🔍 MODE DRY-RUN: Simulation sans modification")
        
        # Validation environnement
        if not self.validate_environment():
            return False
        
        # Migration des modèles
        start_time = time.time()
        
        transformers_ok = self.migrate_transformers_models()
        spacy_ok = self.migrate_spacy_models()
        
        # Vérification
        if transformers_ok or spacy_ok:
            verification_ok = self.verify_migrated_models()
        else:
            verification_ok = False
        
        # Configuration
        if verification_ok and not self.dry_run:
            self.generate_cache_config()
        
        # Rapport final
        total_time = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info("📊 RAPPORT DE MIGRATION")
        logger.info(f"⏱️  Temps total: {total_time:.2f}s")
        logger.info(f"📦 Modèles migrés: {self.stats['models_migrated']}")
        logger.info(f"💾 Taille totale: {self.format_size(self.stats['total_size_copied'])}")
        
        if self.stats['errors']:
            logger.info(f"❌ Erreurs: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.info(f"   - {error}")
        
        success = verification_ok and len(self.stats['errors']) == 0
        
        if success:
            logger.info("✅ Migration réussie!")
            logger.info("💡 Prochaines étapes:")
            logger.info("   1. Modifier le code pour utiliser local_files_only=True")
            logger.info("   2. Mettre à jour docker-compose.yml")
            logger.info("   3. Tester le démarrage rapide")
        else:
            logger.error("❌ Migration échouée - Vérifier les erreurs ci-dessus")
        
        return success


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description='Migration des modèles ML vers cache local LEXO v1'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Mode simulation sans copie réelle'
    )
    parser.add_argument(
        '--force',
        action='store_true', 
        help='Écraser les modèles existants'
    )
    
    args = parser.parse_args()
    
    migrator = ModelCacheMigrator(dry_run=args.dry_run, force=args.force)
    
    try:
        success = migrator.run_migration()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Migration interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()