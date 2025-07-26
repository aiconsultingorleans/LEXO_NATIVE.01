#!/usr/bin/env python3
"""
🔍 LEXO v1 - Validation du Cache Local des Modèles ML
===================================================

Script de validation pour vérifier que tous les modèles ML requis
sont présents et fonctionnels dans le cache local.

Usage:
    python validate_models_cache.py [--load-test] [--verbose]
    
Arguments:
    --load-test : Test de chargement réel des modèles
    --verbose   : Affichage détaillé
"""

import os
import sys
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

class ModelCacheValidator:
    """Validateur du cache local des modèles ML"""
    
    def __init__(self, verbose: bool = False, load_test: bool = False):
        """
        Initialise le validateur
        
        Args:
            verbose: Affichage détaillé
            load_test: Effectuer des tests de chargement réels
        """
        self.verbose = verbose
        self.load_test = load_test
        
        # Chemins
        self.project_root = Path(__file__).parent.parent
        self.ml_models_dir = self.project_root / 'ml_models'
        self.transformers_cache = self.ml_models_dir / 'transformers'
        self.spacy_cache = self.ml_models_dir / 'spacy'
        
        # Modèles requis
        self.required_models = {
            'transformers': {
                'trocr-base-printed': {
                    'files': ['config.json', 'model.safetensors', 'tokenizer_config.json'],
                    'optional_files': ['pytorch_model.bin'],
                    'description': 'TrOCR pour OCR texte imprimé'
                },
                'paraphrase-multilingual-MiniLM-L12-v2': {
                    'files': ['config.json', 'model.safetensors'],
                    'optional_files': ['pytorch_model.bin'],
                    'description': 'Embeddings multilingues pour RAG'
                }
            },
            'spacy': {
                'fr_core_news_sm': {
                    'files': ['meta.json'],
                    'optional_files': [],
                    'description': 'Modèle français pour NER'
                }
            }
        }
        
        # Stats de validation
        self.stats = {
            'models_found': 0,
            'models_missing': 0,
            'models_tested': 0,
            'load_tests_passed': 0,
            'total_size': 0,
            'errors': []
        }
    
    def check_environment_vars(self) -> bool:
        """Vérifie les variables d'environnement de cache"""
        logger.info("🔧 Vérification des variables d'environnement...")
        
        required_vars = {
            'TRANSFORMERS_CACHE': '/Users/stephaneansel/Documents/LEXO_v1/IA_Administratif/ml_models/transformers',
            'HF_MODELS_CACHE': '/Users/stephaneansel/Documents/LEXO_v1/IA_Administratif/ml_models/transformers',
            'HF_HUB_CACHE': '/Users/stephaneansel/Documents/LEXO_v1/IA_Administratif/ml_models/transformers',
            'HF_OFFLINE': '1',
            'TRANSFORMERS_OFFLINE': '1'
        }
        
        all_good = True
        
        for var_name, expected_value in required_vars.items():
            actual_value = os.getenv(var_name)
            
            if not actual_value:
                logger.warning(f"  ⚠️  Variable manquante: {var_name}")
                if self.verbose:
                    logger.info(f"     💡 Ajouter: export {var_name}={expected_value}")
                all_good = False
            elif actual_value != expected_value and var_name not in ['HF_OFFLINE', 'TRANSFORMERS_OFFLINE']:
                logger.warning(f"  ⚠️  Variable incorrecte: {var_name}={actual_value}")
                logger.info(f"     💡 Attendu: {expected_value}")
                all_good = False
            else:
                if self.verbose:
                    logger.info(f"  ✅ {var_name}={actual_value}")
        
        if all_good:
            logger.info("  ✅ Toutes les variables d'environnement sont configurées")
        
        return all_good
    
    def get_directory_size(self, path: Path) -> int:
        """Calcule la taille d'un répertoire"""
        if not path.exists():
            return 0
        
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except (OSError, PermissionError):
                    pass
        return total_size
    
    def format_size(self, size_bytes: int) -> str:
        """Formate une taille en format lisible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f}{unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f}TB"
    
    def validate_model_files(self, model_path: Path, required_files: List[str], 
                           optional_files: List[str] = None) -> Tuple[bool, List[str]]:
        """
        Valide la présence des fichiers d'un modèle
        
        Returns:
            (is_valid, missing_files)
        """
        optional_files = optional_files or []
        missing_files = []
        
        # Vérifier fichiers obligatoires
        for file_name in required_files:
            if not (model_path / file_name).exists():
                missing_files.append(file_name)
        
        # Au moins un fichier optionnel doit être présent
        if optional_files:
            optional_found = any((model_path / f).exists() for f in optional_files)
            if not optional_found and missing_files:
                missing_files.extend([f"(aucun de: {', '.join(optional_files)})"])
        
        return len(missing_files) == 0, missing_files
    
    def validate_transformers_models(self) -> bool:
        """Valide les modèles Transformers"""
        logger.info("🤖 Validation des modèles Transformers...")
        
        if not self.transformers_cache.exists():
            logger.error(f"❌ Répertoire Transformers manquant: {self.transformers_cache}")
            return False
        
        all_valid = True
        
        for model_name, model_info in self.required_models['transformers'].items():
            model_path = self.transformers_cache / model_name
            description = model_info['description']
            
            logger.info(f"📦 Validation: {description}")
            
            if not model_path.exists():
                logger.error(f"  ❌ Modèle manquant: {model_name}")
                self.stats['models_missing'] += 1
                all_valid = False
                continue
            
            # Valider fichiers
            is_valid, missing_files = self.validate_model_files(
                model_path, 
                model_info['files'],
                model_info.get('optional_files', [])
            )
            
            if not is_valid:
                logger.error(f"  ❌ Fichiers manquants dans {model_name}: {', '.join(missing_files)}")
                self.stats['models_missing'] += 1
                all_valid = False
                continue
            
            # Calculer taille
            model_size = self.get_directory_size(model_path)
            self.stats['total_size'] += model_size
            
            logger.info(f"  ✅ Modèle valide: {model_name}")
            if self.verbose:
                logger.info(f"     📊 Taille: {self.format_size(model_size)}")
                logger.info(f"     📁 Chemin: {model_path}")
            
            self.stats['models_found'] += 1
            
            # Test de chargement si demandé
            if self.load_test:
                if self.test_load_transformers_model(model_name, model_path):
                    self.stats['load_tests_passed'] += 1
                    self.stats['models_tested'] += 1
        
        return all_valid
    
    def validate_spacy_models(self) -> bool:
        """Valide les modèles spaCy"""
        logger.info("🔤 Validation des modèles spaCy...")
        
        # spaCy est optionnel pour le moment
        if not self.spacy_cache.exists():
            logger.warning("⚠️  Répertoire spaCy manquant (optionnel)")
            return True
        
        for model_name, model_info in self.required_models['spacy'].items():
            model_path = self.spacy_cache / model_name
            description = model_info['description']
            
            logger.info(f"📦 Validation: {description}")
            
            if not model_path.exists():
                logger.warning(f"  ⚠️  Modèle spaCy manquant: {model_name}")
                logger.info(f"     💡 Installer avec: python -m spacy download {model_name}")
                continue
            
            # Test basique de présence
            if self.verbose:
                model_size = self.get_directory_size(model_path)
                logger.info(f"  ✅ Modèle spaCy: {model_name} ({self.format_size(model_size)})")
            else:
                logger.info(f"  ✅ Modèle spaCy: {model_name}")
        
        return True
    
    def test_load_transformers_model(self, model_name: str, model_path: Path) -> bool:
        """Test de chargement d'un modèle Transformers"""
        if not self.load_test:
            return True
        
        logger.info(f"  🧪 Test de chargement: {model_name}...")
        
        try:
            start_time = time.time()
            
            # Test spécifique selon le modèle
            if 'trocr' in model_name.lower():
                from transformers import TrOCRProcessor, VisionEncoderDecoderModel
                
                processor = TrOCRProcessor.from_pretrained(
                    str(model_path),
                    local_files_only=True
                )
                model = VisionEncoderDecoderModel.from_pretrained(
                    str(model_path),
                    local_files_only=True
                )
                
                # Test basique
                assert processor is not None
                assert model is not None
                
            elif 'paraphrase' in model_name.lower():
                try:
                    from sentence_transformers import SentenceTransformer
                    model = SentenceTransformer(str(model_path), local_files_only=True)
                    assert model is not None
                except ImportError:
                    # Fallback avec transformers standard
                    from transformers import AutoModel, AutoTokenizer
                    
                    tokenizer = AutoTokenizer.from_pretrained(
                        str(model_path),
                        local_files_only=True
                    )
                    model = AutoModel.from_pretrained(
                        str(model_path),
                        local_files_only=True
                    )
                    assert tokenizer is not None
                    assert model is not None
            
            load_time = time.time() - start_time
            logger.info(f"  ✅ Chargement réussi: {model_name} ({load_time:.2f}s)")
            return True
            
        except Exception as e:
            error_msg = f"Erreur chargement {model_name}: {str(e)}"
            logger.error(f"  ❌ {error_msg}")
            self.stats['errors'].append(error_msg)
            return False
    
    def generate_report(self) -> None:
        """Génère le rapport de validation"""
        logger.info("=" * 60)
        logger.info("📊 RAPPORT DE VALIDATION DU CACHE ML")
        logger.info("=" * 60)
        
        logger.info(f"📦 Modèles trouvés: {self.stats['models_found']}")
        logger.info(f"❌ Modèles manquants: {self.stats['models_missing']}")
        logger.info(f"💾 Taille totale cache: {self.format_size(self.stats['total_size'])}")
        
        if self.load_test:
            logger.info(f"🧪 Tests de chargement: {self.stats['load_tests_passed']}/{self.stats['models_tested']}")
        
        if self.stats['errors']:
            logger.info(f"❌ Erreurs: {len(self.stats['errors'])}")
            for error in self.stats['errors']:
                logger.info(f"   - {error}")
        
        # Recommandations
        if self.stats['models_missing'] > 0:
            logger.info("")
            logger.info("💡 RECOMMANDATIONS:")
            logger.info("   1. Exécuter: python migrate_models_to_local_cache.py")
            logger.info("   2. Vérifier que les modèles système sont téléchargés")
            logger.info("   3. Relancer la validation avec --load-test")
        
        success = (self.stats['models_missing'] == 0 and 
                  len(self.stats['errors']) == 0)
        
        if success:
            logger.info("")
            logger.info("🎉 VALIDATION RÉUSSIE!")
            logger.info("✅ Cache local prêt pour démarrage rapide")
        else:
            logger.info("")
            logger.info("❌ VALIDATION ÉCHOUÉE")
            logger.info("⚠️  Corriger les problèmes avant utilisation")
    
    def run_validation(self) -> bool:
        """Exécute la validation complète"""
        logger.info("🔍 LEXO v1 - Validation du Cache Local des Modèles ML")
        logger.info("=" * 60)
        
        if self.verbose:
            logger.info(f"📁 Répertoire ML: {self.ml_models_dir}")
            logger.info(f"🧪 Tests de chargement: {'Activés' if self.load_test else 'Désactivés'}")
        
        # Vérifications
        env_ok = self.check_environment_vars()
        transformers_ok = self.validate_transformers_models()
        spacy_ok = self.validate_spacy_models()
        
        # Rapport
        self.generate_report()
        
        return env_ok and transformers_ok and spacy_ok


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description='Validation du cache local des modèles ML LEXO v1'
    )
    parser.add_argument(
        '--load-test',
        action='store_true',
        help='Effectuer des tests de chargement réels des modèles'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Affichage détaillé'
    )
    
    args = parser.parse_args()
    
    validator = ModelCacheValidator(
        verbose=args.verbose,
        load_test=args.load_test
    )
    
    try:
        success = validator.run_validation()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Validation interrompue par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erreur fatale: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()