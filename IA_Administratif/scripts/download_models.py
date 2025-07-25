#!/usr/bin/env python3
"""
Script de pré-téléchargement des modèles ML pour LEXO v1
Télécharge tous les modèles nécessaires dans le cache local
Usage: python download_models.py [--cache-dir /path/to/cache]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional
import time

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Définition des modèles à télécharger
MODELS_CONFIG = {
    "transformers": [
        {
            "name": "microsoft/trocr-base-printed",
            "type": "TrOCR",
            "size": "558MB",
            "description": "OCR pour texte imprimé"
        },
        {
            "name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 
            "type": "Embeddings",
            "size": "120MB",
            "description": "Embeddings multilingues"
        }
    ],
    "spacy": [
        {
            "name": "fr_core_news_sm",
            "type": "spaCy",
            "size": "15MB", 
            "description": "Modèle français pour NER"
        }
    ],
    "mlx": [
        {
            "name": "mlx-community/Mistral-7B-Instruct-v0.3-4bit",
            "type": "MLX LLM",
            "size": "2.1GB",
            "description": "Modèle Mistral quantifié pour MLX"
        }
    ]
}


class ModelDownloader:
    """Gestionnaire de téléchargement des modèles"""
    
    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialise le téléchargeur
        
        Args:
            cache_dir: Répertoire de cache personnalisé
        """
        # Déterminer le répertoire de cache
        if cache_dir:
            self.base_cache_dir = Path(cache_dir)
        else:
            # Utiliser le répertoire ml_models du projet
            project_root = Path(__file__).parent.parent
            self.base_cache_dir = project_root / "ml_models"
        
        # Créer les sous-répertoires
        self.transformers_cache = self.base_cache_dir / "transformers"
        self.spacy_cache = self.base_cache_dir / "spacy"
        self.mlx_cache = self.base_cache_dir / "mistral_7b_mlx"
        
        # Créer les répertoires
        for cache_dir in [self.transformers_cache, self.spacy_cache, self.mlx_cache]:
            cache_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Cache de base configuré: {self.base_cache_dir}")
    
    def download_transformers_models(self) -> bool:
        """Télécharge les modèles HuggingFace Transformers"""
        logger.info("📥 Téléchargement des modèles Transformers...")
        
        try:
            from transformers import (
                TrOCRProcessor, 
                VisionEncoderDecoderModel,
                AutoTokenizer,
                AutoModel
            )
            
            # Configurer le cache HuggingFace
            os.environ['TRANSFORMERS_CACHE'] = str(self.transformers_cache)
            
            success_count = 0
            
            for model_config in MODELS_CONFIG["transformers"]:
                model_name = model_config["name"]
                logger.info(f"  ⬇️  {model_config['description']} ({model_config['size']})")
                logger.info(f"      {model_name}")
                
                try:
                    start_time = time.time()
                    
                    if "trocr" in model_name.lower():
                        # Modèle TrOCR spécifique
                        processor = TrOCRProcessor.from_pretrained(
                            model_name, 
                            cache_dir=self.transformers_cache
                        )
                        model = VisionEncoderDecoderModel.from_pretrained(
                            model_name,
                            cache_dir=self.transformers_cache
                        )
                        logger.info(f"      ✅ TrOCR téléchargé en {time.time() - start_time:.1f}s")
                        
                    elif "sentence-transformers" in model_name:
                        # Modèle d'embeddings
                        try:
                            from sentence_transformers import SentenceTransformer
                            model = SentenceTransformer(
                                model_name,
                                cache_folder=str(self.transformers_cache)
                            )
                            logger.info(f"      ✅ Embeddings téléchargé en {time.time() - start_time:.1f}s")
                        except ImportError:
                            logger.warning("      sentence-transformers non installé, utilisation d'AutoModel")
                            tokenizer = AutoTokenizer.from_pretrained(
                                model_name,
                                cache_dir=self.transformers_cache
                            )
                            model = AutoModel.from_pretrained(
                                model_name,
                                cache_dir=self.transformers_cache
                            )
                            logger.info(f"      ✅ Modèle téléchargé en {time.time() - start_time:.1f}s")
                    
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"      ❌ Erreur: {e}")
                    continue
            
            logger.info(f"✅ Transformers: {success_count}/{len(MODELS_CONFIG['transformers'])} modèles téléchargés")
            return success_count > 0
            
        except ImportError as e:
            logger.error(f"❌ Transformers non disponible: {e}")
            return False
    
    def download_spacy_models(self) -> bool:
        """Télécharge les modèles spaCy"""
        logger.info("📥 Téléchargement des modèles spaCy...")
        
        try:
            import spacy
            from spacy.cli import download
            import subprocess
            
            # Configurer le répertoire spaCy
            os.environ['SPACY_DATA'] = str(self.spacy_cache)
            
            success_count = 0
            
            for model_config in MODELS_CONFIG["spacy"]:
                model_name = model_config["name"]
                logger.info(f"  ⬇️  {model_config['description']} ({model_config['size']})")
                logger.info(f"      {model_name}")
                
                try:
                    start_time = time.time()
                    
                    # Vérifier si le modèle est déjà installé
                    try:
                        nlp = spacy.load(model_name)
                        logger.info(f"      ✅ Déjà installé")
                        success_count += 1
                        continue
                    except OSError:
                        pass
                    
                    # Télécharger le modèle
                    cmd = [sys.executable, "-m", "spacy", "download", model_name]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        logger.info(f"      ✅ spaCy téléchargé en {time.time() - start_time:.1f}s")
                        success_count += 1
                    else:
                        logger.error(f"      ❌ Erreur spaCy: {result.stderr}")
                
                except Exception as e:
                    logger.error(f"      ❌ Erreur: {e}")
                    continue
            
            logger.info(f"✅ spaCy: {success_count}/{len(MODELS_CONFIG['spacy'])} modèles téléchargés")
            return success_count > 0
            
        except ImportError as e:
            logger.error(f"❌ spaCy non disponible: {e}")
            return False
    
    def download_mlx_models(self) -> bool:
        """Télécharge les modèles MLX"""
        logger.info("📥 Téléchargement des modèles MLX...")
        
        try:
            # MLX nécessite import spécifique
            try:
                import mlx
                import mlx.core as mx
                from mlx_lm import load
            except ImportError:
                logger.warning("❌ MLX non disponible (normal sur non-Apple Silicon)")
                return False
            
            success_count = 0
            
            for model_config in MODELS_CONFIG["mlx"]:
                model_name = model_config["name"]
                logger.info(f"  ⬇️  {model_config['description']} ({model_config['size']})")
                logger.info(f"      {model_name}")
                
                try:
                    start_time = time.time()
                    
                    # Utiliser mlx_lm pour télécharger
                    model_path = self.mlx_cache / model_name.replace("/", "_")
                    
                    # Télécharger le modèle MLX
                    model, tokenizer = load(model_name, model_path=str(model_path))
                    
                    logger.info(f"      ✅ MLX téléchargé en {time.time() - start_time:.1f}s")
                    success_count += 1
                
                except Exception as e:
                    logger.error(f"      ❌ Erreur MLX: {e}")
                    continue
            
            logger.info(f"✅ MLX: {success_count}/{len(MODELS_CONFIG['mlx'])} modèles téléchargés")
            return success_count > 0
            
        except ImportError as e:
            logger.error(f"❌ MLX non disponible: {e}")
            return False
    
    def check_cache_sizes(self):
        """Affiche les tailles des caches"""
        logger.info("📊 Tailles des caches:")
        
        def get_dir_size(path: Path) -> float:
            """Calcule la taille d'un répertoire en MB"""
            if not path.exists():
                return 0.0
            
            total_size = 0
            for file_path in path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            
            return total_size / (1024 * 1024)  # Convertir en MB
        
        caches = {
            "Transformers": self.transformers_cache,
            "spaCy": self.spacy_cache, 
            "MLX": self.mlx_cache
        }
        
        total_size = 0
        for cache_name, cache_path in caches.items():
            size_mb = get_dir_size(cache_path)
            total_size += size_mb
            logger.info(f"  {cache_name}: {size_mb:.1f} MB ({cache_path})")
        
        logger.info(f"  Total: {total_size:.1f} MB")
    
    def download_all(self) -> bool:
        """Télécharge tous les modèles"""
        logger.info("🚀 Début du téléchargement de tous les modèles LEXO v1")
        logger.info(f"📁 Cache de base: {self.base_cache_dir}")
        
        start_time = time.time()
        results = []
        
        # Télécharger chaque type de modèle
        results.append(self.download_transformers_models())
        results.append(self.download_spacy_models())
        results.append(self.download_mlx_models())
        
        # Vérifier les tailles
        self.check_cache_sizes()
        
        total_time = time.time() - start_time
        success_count = sum(results)
        
        logger.info(f"🎉 Téléchargement terminé en {total_time:.1f}s")
        logger.info(f"✅ {success_count}/3 types de modèles téléchargés avec succès")
        
        if success_count >= 2:  # Au moins Transformers + spaCy
            logger.info("🎯 Configuration minimale atteinte pour LEXO v1")
            return True
        else:
            logger.warning("⚠️  Configuration incomplète, certaines fonctionnalités seront limitées")
            return False


def main():
    """Point d'entrée principal"""
    parser = argparse.ArgumentParser(
        description="Télécharge tous les modèles ML pour LEXO v1"
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        help="Répertoire de cache personnalisé (défaut: ./ml_models)"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Vérifier les caches existants sans télécharger"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        choices=["transformers", "spacy", "mlx"],
        help="Types de modèles à télécharger (défaut: tous)"
    )
    
    args = parser.parse_args()
    
    # Créer le downloader
    downloader = ModelDownloader(args.cache_dir)
    
    if args.check_only:
        # Vérification seulement
        downloader.check_cache_sizes()
        return 0
    
    # Téléchargement
    if args.models:
        # Téléchargement sélectif
        results = []
        if "transformers" in args.models:
            results.append(downloader.download_transformers_models())
        if "spacy" in args.models:
            results.append(downloader.download_spacy_models())
        if "mlx" in args.models:
            results.append(downloader.download_mlx_models())
        
        success = any(results)
    else:
        # Téléchargement complet
        success = downloader.download_all()
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())