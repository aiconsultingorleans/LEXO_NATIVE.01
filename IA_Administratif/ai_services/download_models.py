#!/usr/bin/env python3
"""
Script de téléchargement des modèles DONUT + CamemBERT pour usage local
Optimisé Apple Silicon M4 - Étape 2 Infrastructure
"""

import os
from pathlib import Path
from transformers import AutoTokenizer, AutoModel, DonutProcessor, VisionEncoderDecoderModel
from loguru import logger

# Configuration des chemins
MODELS_DIR = Path(__file__).parent / "models" / "donut"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Modèles validés Étape 1
MODELS_CONFIG = {
    "donut": {
        "name": "naver-clova-ix/donut-base-finetuned-cord-v2",
        "local_path": MODELS_DIR / "donut-base-finetuned-cord-v2",
        "size_gb": 2.31,
        "description": "DONUT OCR-free document understanding"
    },
    "camembert": {
        "name": "almanach/camembert-base", 
        "local_path": MODELS_DIR / "camembert-base",
        "size_gb": 1.41,
        "description": "CamemBERT français pour classification"
    },
    "camembert_ner": {
        "name": "Jean-Baptiste/camembert-ner",
        "local_path": MODELS_DIR / "camembert-ner", 
        "size_gb": 1.48,
        "description": "NER français pour extraction émetteurs"
    }
}

def download_model(model_key: str, config: dict) -> bool:
    """Télécharge un modèle HuggingFace localement"""
    try:
        logger.info(f"📥 Téléchargement {config['description']} ({config['size_gb']:.2f}GB)")
        logger.info(f"   Modèle: {config['name']}")
        logger.info(f"   Destination: {config['local_path']}")
        
        if model_key == "donut":
            # DONUT nécessite VisionEncoderDecoderModel et DonutProcessor
            processor = DonutProcessor.from_pretrained(config['name'])
            model = VisionEncoderDecoderModel.from_pretrained(config['name'])
            
            processor.save_pretrained(config['local_path'])
            model.save_pretrained(config['local_path'])
            
        else:
            # CamemBERT et variants utilisent AutoModel/AutoTokenizer
            tokenizer = AutoTokenizer.from_pretrained(config['name'])
            model = AutoModel.from_pretrained(config['name'])
            
            tokenizer.save_pretrained(config['local_path'])
            model.save_pretrained(config['local_path'])
        
        logger.success(f"✅ {config['description']} téléchargé avec succès")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur téléchargement {config['description']}: {e}")
        return False

def verify_local_models() -> dict:
    """Vérifie la présence des modèles téléchargés localement"""
    results = {}
    
    for model_key, config in MODELS_CONFIG.items():
        local_path = config['local_path']
        
        # Vérifier présence fichiers essentiels
        config_file = local_path / "config.json"
        model_files = list(local_path.glob("*.safetensors")) or list(local_path.glob("pytorch_model.bin"))
        
        if config_file.exists() and model_files:
            size_mb = sum(f.stat().st_size for f in local_path.rglob("*") if f.is_file()) / (1024**2)
            results[model_key] = {
                "status": "OK",
                "path": str(local_path),
                "size_mb": round(size_mb, 1),
                "files_count": len(list(local_path.rglob("*")))
            }
            logger.success(f"✅ {config['description']}: {size_mb:.1f}MB, {len(model_files)} fichiers modèle")
        else:
            results[model_key] = {
                "status": "MISSING",
                "path": str(local_path),
                "size_mb": 0,
                "files_count": 0
            }
            logger.warning(f"⚠️  {config['description']}: Non trouvé dans {local_path}")
    
    return results

def main():
    """Téléchargement principal des modèles DONUT"""
    logger.info("🍩 DONUT - Téléchargement modèles locaux Étape 2")
    logger.info(f"📁 Dossier destination: {MODELS_DIR}")
    
    # Vérification état actuel
    logger.info("🔍 Vérification modèles existants...")
    current_status = verify_local_models()
    
    total_downloaded = 0
    total_size_gb = 0
    
    # Téléchargement des modèles manquants
    for model_key, config in MODELS_CONFIG.items():
        if current_status[model_key]["status"] == "MISSING":
            logger.info(f"\n📦 Téléchargement {model_key}...")
            if download_model(model_key, config):
                total_downloaded += 1
                total_size_gb += config['size_gb']
        else:
            logger.info(f"✓ {config['description']} déjà présent ({current_status[model_key]['size_mb']}MB)")
    
    # Vérification finale
    logger.info("\n🔍 Vérification finale...")
    final_status = verify_local_models()
    
    # Rapport de téléchargement
    logger.info(f"\n📊 Rapport téléchargement:")
    logger.info(f"   Modèles téléchargés: {total_downloaded}")
    logger.info(f"   Taille totale: {total_size_gb:.2f}GB")
    logger.info(f"   Dossier: {MODELS_DIR}")
    
    # Validation finale
    all_ok = all(status["status"] == "OK" for status in final_status.values())
    if all_ok:
        logger.success("🎉 Tous les modèles DONUT sont prêts pour Étape 3!")
        return True
    else:
        missing = [k for k, v in final_status.items() if v["status"] == "MISSING"]
        logger.error(f"❌ Modèles manquants: {missing}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)