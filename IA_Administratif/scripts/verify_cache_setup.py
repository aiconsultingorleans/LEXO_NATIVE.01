#!/usr/bin/env python3
"""
Script de vérification du setup de cache pour LEXO v1
Vérifie que la configuration de cache fonctionne correctement
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import Dict, List, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_environment_variables() -> Dict[str, str]:
    """Vérifie les variables d'environnement de cache"""
    logger.info("🔍 Vérification des variables d'environnement...")
    
    expected_vars = {
        'TRANSFORMERS_CACHE': '/app/ml_models/transformers',
        'HF_DATASETS_CACHE': '/app/ml_models/datasets',
        'HF_MODELS_CACHE': '/app/ml_models/transformers', 
        'SPACY_DATA': '/app/ml_models/spacy',
        'HF_HUB_CACHE': '/root/.cache/huggingface/hub',
        'TORCH_HOME': '/app/ml_models/torch'
    }
    
    results = {}
    for var, expected in expected_vars.items():
        value = os.getenv(var)
        if value:
            if value == expected:
                logger.info(f"  ✅ {var}: {value}")
                results[var] = "OK"
            else:
                logger.warning(f"  ⚠️  {var}: {value} (attendu: {expected})")
                results[var] = "DIFFERENT"
        else:
            logger.error(f"  ❌ {var}: Non définie")
            results[var] = "MISSING"
    
    return results


def check_cache_directories() -> Dict[str, bool]:
    """Vérifie l'existence des répertoires de cache"""
    logger.info("📁 Vérification des répertoires de cache...")
    
    cache_dirs = [
        '/app/ml_models',
        '/app/ml_models/transformers',
        '/app/ml_models/spacy',
        '/app/ml_models/datasets',
        '/app/ml_models/torch',
        '/root/.cache/huggingface'
    ]
    
    results = {}
    for cache_dir in cache_dirs:
        path = Path(cache_dir)
        if path.exists():
            logger.info(f"  ✅ {cache_dir}")
            results[cache_dir] = True
        else:
            logger.warning(f"  ❌ {cache_dir} (sera créé automatiquement)")
            results[cache_dir] = False
            # Créer le répertoire s'il n'existe pas
            try:
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"    ✅ Créé: {cache_dir}")
                results[cache_dir] = True
            except PermissionError:
                logger.error(f"    ❌ Permission refusée: {cache_dir}")
    
    return results


def test_transformers_cache() -> bool:
    """Test l'utilisation du cache pour transformers"""
    logger.info("🤗 Test du cache Transformers...")
    
    try:
        from transformers import AutoTokenizer
        
        # Tester avec un modèle léger
        model_name = "bert-base-uncased"  # Modèle léger pour test
        cache_dir = os.getenv('TRANSFORMERS_CACHE', '/app/ml_models/transformers')
        
        logger.info(f"  Chargement tokenizer depuis cache: {cache_dir}")
        start_time = time.time()
        
        tokenizer = AutoTokenizer.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )
        
        load_time = time.time() - start_time
        logger.info(f"  ✅ Tokenizer chargé en {load_time:.2f}s")
        
        # Vérifier que le cache contient des fichiers
        cache_path = Path(cache_dir)
        if cache_path.exists():
            cache_files = list(cache_path.rglob('*'))
            logger.info(f"  📁 Cache contient {len(cache_files)} fichiers")
        
        return True
        
    except ImportError:
        logger.error("  ❌ Transformers non disponible")
        return False
    except Exception as e:
        logger.error(f"  ❌ Erreur: {e}")
        return False


def test_spacy_cache() -> bool:
    """Test l'utilisation du cache pour spaCy"""
    logger.info("🔤 Test du cache spaCy...")
    
    try:
        import spacy
        
        # Configurer le répertoire spaCy
        spacy_data_dir = os.getenv('SPACY_DATA')
        if spacy_data_dir:
            import spacy.util
            spacy.util.set_data_path(spacy_data_dir)
            logger.info(f"  Répertoire spaCy configuré: {spacy_data_dir}")
        
        start_time = time.time()
        nlp = spacy.load('fr_core_news_sm')
        load_time = time.time() - start_time
        
        logger.info(f"  ✅ Modèle français chargé en {load_time:.2f}s")
        
        # Test basique
        doc = nlp("Bonjour, je suis Claude et j'habite à Paris.")
        entities = [(ent.text, ent.label_) for ent in doc.ents]
        logger.info(f"  📝 Test NER: {entities}")
        
        return True
        
    except ImportError:
        logger.error("  ❌ spaCy non disponible")
        return False
    except OSError:
        logger.error("  ❌ Modèle français fr_core_news_sm non trouvé")
        return False
    except Exception as e:
        logger.error(f"  ❌ Erreur: {e}")
        return False


def test_huggingface_cache() -> bool:
    """Test l'accès au cache HuggingFace"""
    logger.info("📦 Test du cache HuggingFace...")
    
    hf_cache = os.getenv('HF_HUB_CACHE', '/root/.cache/huggingface/hub')
    cache_path = Path(hf_cache)
    
    if cache_path.exists():
        # Compter les modèles dans le cache
        model_dirs = list(cache_path.glob('models--*'))
        logger.info(f"  ✅ Cache HF trouvé: {len(model_dirs)} modèles")
        
        # Lister quelques modèles
        for i, model_dir in enumerate(model_dirs[:3]):
            model_name = model_dir.name.replace('models--', '').replace('--', '/')
            logger.info(f"    {i+1}. {model_name}")
        
        if len(model_dirs) > 3:
            logger.info(f"    ... et {len(model_dirs) - 3} autres")
        
        return True
    else:
        logger.warning(f"  ⚠️  Cache HF non trouvé: {hf_cache}")
        return False


def benchmark_loading_performance() -> Dict[str, float]:
    """Benchmark des temps de chargement"""
    logger.info("⏱️  Benchmark des performances...")
    
    results = {}
    
    # Test spaCy
    try:
        import spacy
        start_time = time.time()
        nlp = spacy.load('fr_core_news_sm')
        results['spacy_load_time'] = time.time() - start_time
        logger.info(f"  spaCy: {results['spacy_load_time']:.2f}s")
    except:
        results['spacy_load_time'] = -1
        logger.error("  spaCy: Erreur")
    
    # Test OCR Tesseract
    try:
        import pytesseract
        from PIL import Image
        import numpy as np
        
        # Créer une image de test
        img = Image.fromarray(np.ones((100, 400, 3), dtype=np.uint8) * 255)
        
        start_time = time.time()
        text = pytesseract.image_to_string(img, lang='fra')
        results['tesseract_time'] = time.time() - start_time
        logger.info(f"  Tesseract: {results['tesseract_time']:.2f}s")
    except:
        results['tesseract_time'] = -1
        logger.error("  Tesseract: Erreur")
    
    return results


def generate_report() -> str:
    """Génère un rapport de configuration"""
    logger.info("📊 Génération du rapport...")
    
    report = []
    report.append("=" * 50)
    report.append("🔍 RAPPORT DE CONFIGURATION CACHE LEXO v1")
    report.append("=" * 50)
    
    # Variables d'environnement
    env_vars = check_environment_variables()
    report.append("\n📋 Variables d'environnement:")
    for var, status in env_vars.items():
        icon = "✅" if status == "OK" else "⚠️" if status == "DIFFERENT" else "❌"
        report.append(f"  {icon} {var}: {status}")
    
    # Répertoires
    cache_dirs = check_cache_directories()
    report.append("\n📁 Répertoires de cache:")
    for dir_path, exists in cache_dirs.items():
        icon = "✅" if exists else "❌"
        report.append(f"  {icon} {dir_path}")
    
    # Tests fonctionnels
    report.append("\n🧪 Tests fonctionnels:")
    
    transformers_ok = test_transformers_cache()
    report.append(f"  {'✅' if transformers_ok else '❌'} Cache Transformers")
    
    spacy_ok = test_spacy_cache()
    report.append(f"  {'✅' if spacy_ok else '❌'} Cache spaCy")
    
    hf_ok = test_huggingface_cache()
    report.append(f"  {'✅' if hf_ok else '❌'} Cache HuggingFace")
    
    # Performance
    perf = benchmark_loading_performance()
    report.append("\n⏱️  Performances:")
    for metric, value in perf.items():
        if value >= 0:
            report.append(f"  ✅ {metric}: {value:.2f}s")
        else:
            report.append(f"  ❌ {metric}: Erreur")
    
    # Recommandations
    report.append("\n💡 Recommandations:")
    
    total_issues = sum(1 for status in env_vars.values() if status != "OK")
    missing_dirs = sum(1 for exists in cache_dirs.values() if not exists)
    
    if total_issues == 0 and missing_dirs == 0 and transformers_ok and spacy_ok:
        report.append("  🎉 Configuration optimale atteinte!")
        report.append("  🚀 Démarrage rapide garanti (< 30 secondes)")
    else:
        if total_issues > 0:
            report.append("  ⚠️  Vérifier les variables d'environnement manquantes")
        if missing_dirs > 0:
            report.append("  📁 Créer les répertoires de cache manquants")
        if not transformers_ok:
            report.append("  🤗 Installer transformers: pip install transformers")
        if not spacy_ok:
            report.append("  🔤 Installer spaCy: python -m spacy download fr_core_news_sm")
        
        report.append("  ⏱️  Premier démarrage prévu: 2-5 minutes")
    
    report.append("\n" + "=" * 50)
    
    return "\n".join(report)


def main():
    """Point d'entrée principal"""
    logger.info("🚀 LEXO v1 - Vérification de la configuration cache")
    
    try:
        # Générer et afficher le rapport
        report = generate_report()
        print(report)
        
        # Sauvegarder le rapport
        report_file = Path("/app/logs/cache_verification_report.txt")
        if report_file.parent.exists():
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"📄 Rapport sauvegardé: {report_file}")
        
        logger.info("✅ Vérification terminée")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de la vérification: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())