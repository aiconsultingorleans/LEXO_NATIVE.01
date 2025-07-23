"""
Module OCR avancé utilisant TrOCR de Microsoft
Pipeline d'OCR basé sur les transformers pour une reconnaissance haute précision
"""

import logging
import time
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple
import tempfile
import os
from dataclasses import dataclass

import torch
import numpy as np
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
from huggingface_hub import hf_hub_download
import cv2

# Import des modules locaux
from .tesseract_ocr import TesseractOCR, OCRResult
from .image_preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


@dataclass
class TrOCRConfig:
    """Configuration pour TrOCR"""
    model_name: str = "microsoft/trocr-base-printed"
    batch_size: int = 4
    max_length: int = 512
    device: str = "auto"  # auto, cpu, cuda, mps
    cache_dir: Optional[str] = None
    use_gpu: bool = True
    fallback_to_tesseract: bool = True
    confidence_threshold: float = 0.8


class TrOCREngine:
    """
    Moteur OCR avancé basé sur TrOCR de Microsoft
    """
    
    def __init__(self, config: Optional[TrOCRConfig] = None):
        """
        Initialise le moteur TrOCR
        
        Args:
            config: Configuration personnalisée
        """
        self.config = config or TrOCRConfig()
        self.processor = None
        self.model = None
        self.device = None
        self.tesseract_fallback = None
        self.preprocessor = ImagePreprocessor()
        
        # Modèles disponibles avec leurs spécificités
        self.available_models = {
            "microsoft/trocr-base-printed": {
                "description": "Modèle de base pour texte imprimé",
                "best_for": "Documents standards, factures, lettres",
                "size": "~558MB",
                "accuracy": "94-96%"
            },
            "microsoft/trocr-large-printed": {
                "description": "Modèle large pour texte imprimé",
                "best_for": "Documents complexes, haute précision",
                "size": "~1.4GB", 
                "accuracy": "96-98%"
            },
            "microsoft/trocr-base-handwritten": {
                "description": "Modèle pour écriture manuscrite",
                "best_for": "Notes manuscrites, formulaires remplis à la main",
                "size": "~558MB",
                "accuracy": "85-90%"
            }
        }
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialise le modèle TrOCR"""
        try:
            logger.info(f"Initialisation TrOCR avec le modèle: {self.config.model_name}")
            
            # Détection automatique du device
            if self.config.device == "auto":
                if torch.cuda.is_available() and self.config.use_gpu:
                    self.device = torch.device("cuda")
                    logger.info("GPU CUDA détecté et activé")
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() and self.config.use_gpu:
                    self.device = torch.device("mps") 
                    logger.info("GPU Metal (Apple Silicon) détecté et activé")
                else:
                    self.device = torch.device("cpu")
                    logger.info("Utilisation du CPU")
            else:
                self.device = torch.device(self.config.device)
            
            # Chargement du processeur et du modèle
            logger.info("Téléchargement du processeur TrOCR...")
            self.processor = TrOCRProcessor.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir
            )
            
            logger.info("Téléchargement du modèle TrOCR...")
            self.model = VisionEncoderDecoderModel.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir
            )
            
            # Déplacer le modèle sur le device approprié
            self.model.to(self.device)
            self.model.eval()  # Mode évaluation
            
            # Initialiser le fallback Tesseract si nécessaire
            if self.config.fallback_to_tesseract:
                self.tesseract_fallback = TesseractOCR()
                logger.info("Fallback Tesseract initialisé")
            
            logger.info(f"TrOCR initialisé avec succès sur {self.device}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de TrOCR: {str(e)}")
            raise RuntimeError(f"Impossible d'initialiser TrOCR: {str(e)}")
    
    def _convert_to_pil(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> Image.Image:
        """
        Convertit différents formats d'image vers PIL Image
        
        Args:
            image_input: Image au format chemin, numpy array ou PIL Image
            
        Returns:
            Image PIL
        """
        if isinstance(image_input, (str, Path)):
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Fichier image non trouvé: {image_input}")
            return Image.open(image_input).convert('RGB')
        
        elif isinstance(image_input, np.ndarray):
            # Conversion numpy vers PIL
            if len(image_input.shape) == 3:
                # BGR vers RGB si nécessaire
                if image_input.shape[2] == 3:
                    image_input = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
                return Image.fromarray(image_input)
            elif len(image_input.shape) == 2:
                return Image.fromarray(image_input).convert('RGB')
        
        elif isinstance(image_input, Image.Image):
            return image_input.convert('RGB')
        
        else:
            raise ValueError(f"Format d'image non supporté: {type(image_input)}")
    
    def extract_text(
        self, 
        image: Union[str, Path, np.ndarray, Image.Image],
        preprocess: bool = True,
        use_fallback: bool = None
    ) -> OCRResult:
        """
        Extrait le texte d'une image avec TrOCR
        
        Args:
            image: Image à traiter
            preprocess: Appliquer le prétraitement
            use_fallback: Utiliser Tesseract en fallback si échec
            
        Returns:
            OCRResult avec le texte extrait et les métadonnées
        """
        start_time = time.time()
        use_fallback = use_fallback if use_fallback is not None else self.config.fallback_to_tesseract
        
        try:
            # Conversion vers PIL
            pil_image = self._convert_to_pil(image)
            original_size = pil_image.size
            
            logger.info(f"Extraction TrOCR démarrée, taille: {original_size}")
            
            # Prétraitement si demandé
            if preprocess:
                logger.debug("Application du prétraitement...")
                # Convertir PIL vers numpy pour le préprocesseur
                np_image = np.array(pil_image)
                if len(np_image.shape) == 3:
                    np_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
                
                processed_image = self.preprocessor.process_image_array(np_image)
                
                # Reconvertir vers PIL
                if len(processed_image.shape) == 3:
                    processed_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(processed_image)
            
            # Préparation de l'image pour TrOCR
            pixel_values = self.processor(
                images=pil_image, 
                return_tensors="pt"
            ).pixel_values.to(self.device)
            
            # Génération du texte
            logger.debug("Génération du texte avec TrOCR...")
            with torch.no_grad():
                generated_ids = self.model.generate(
                    pixel_values,
                    max_length=self.config.max_length,
                    num_beams=4,
                    early_stopping=True
                )
            
            # Décodage du texte
            generated_text = self.processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            # Calcul des métriques
            processing_time = time.time() - start_time
            word_count = len(generated_text.split())
            line_count = len(generated_text.split('\n'))
            
            # Score de confiance approximatif (TrOCR ne fournit pas de score direct)
            confidence = self._estimate_confidence(generated_text, pil_image)
            
            # Extraction d'entités basique
            entities = self._extract_entities(generated_text)
            
            # Métriques de qualité
            quality_metrics = {
                "model_used": "TrOCR",
                "model_name": self.config.model_name,
                "device": str(self.device),
                "preprocessing_applied": preprocess,
                "original_size": original_size,
                "estimated_confidence": confidence
            }
            
            logger.info(f"TrOCR terminé: {word_count} mots, "
                       f"confiance estimée: {confidence:.3f}, "
                       f"temps: {processing_time:.2f}s")
            
            return OCRResult(
                text=generated_text,
                confidence=confidence,
                language="auto",  # TrOCR détecte automatiquement
                processing_time=processing_time,
                word_count=word_count,
                line_count=line_count,
                bbox_data=[],  # TrOCR ne fournit pas de bounding boxes
                detected_entities=entities,
                quality_metrics=quality_metrics
            )
            
        except Exception as e:
            logger.error(f"Erreur TrOCR: {str(e)}")
            
            # Fallback vers Tesseract si configuré
            if use_fallback and self.tesseract_fallback:
                logger.info("Fallback vers Tesseract...")
                try:
                    tesseract_result = self.tesseract_fallback.extract_text(image, preprocess=preprocess)
                    # Marquer que c'est un fallback
                    tesseract_result.quality_metrics["fallback_used"] = True
                    tesseract_result.quality_metrics["original_error"] = str(e)
                    return tesseract_result
                    
                except Exception as fallback_error:
                    logger.error(f"Fallback Tesseract également échoué: {fallback_error}")
            
            # Aucun fallback ou fallback échoué
            processing_time = time.time() - start_time
            return OCRResult(
                text="",
                confidence=0.0,
                language="unknown",
                processing_time=processing_time,
                word_count=0,
                line_count=0,
                bbox_data=[],
                detected_entities={},
                quality_metrics={"error": str(e), "model_used": "TrOCR_failed"}
            )
    
    def extract_text_batch(
        self, 
        images: List[Union[str, Path, np.ndarray, Image.Image]],
        preprocess: bool = True
    ) -> List[OCRResult]:
        """
        Traite plusieurs images en batch pour de meilleures performances
        
        Args:
            images: Liste d'images à traiter
            preprocess: Appliquer le prétraitement
            
        Returns:
            Liste des résultats OCR
        """
        logger.info(f"Traitement batch de {len(images)} images")
        
        results = []
        
        # Traiter par batch pour optimiser l'utilisation GPU
        for i in range(0, len(images), self.config.batch_size):
            batch = images[i:i + self.config.batch_size]
            
            for image in batch:
                try:
                    result = self.extract_text(image, preprocess=preprocess)
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Erreur sur image {i}: {e}")
                    # Ajouter un résultat d'erreur
                    results.append(OCRResult(
                        text="",
                        confidence=0.0,
                        language="unknown",
                        processing_time=0.0,
                        word_count=0,
                        line_count=0,
                        bbox_data=[],
                        detected_entities={},
                        quality_metrics={"error": str(e)}
                    ))
        
        logger.info(f"Batch terminé: {len(results)} résultats")
        return results
    
    def _estimate_confidence(self, text: str, image: Image.Image) -> float:
        """
        Estime un score de confiance pour TrOCR
        (TrOCR ne fournit pas de score de confiance natif)
        
        Args:
            text: Texte extrait
            image: Image source
            
        Returns:
            Score de confiance estimé (0-1)
        """
        confidence = 0.8  # Score de base élevé pour TrOCR
        
        # Ajustements basés sur des heuristiques
        
        # Longueur du texte (très court = suspect)
        if len(text.strip()) < 5:
            confidence -= 0.3
        elif len(text.strip()) < 20:
            confidence -= 0.1
        
        # Caractères spéciaux ou aberrants
        special_chars = sum(1 for c in text if not c.isalnum() and c not in ' .,!?;:\n-()[]{}')
        if special_chars > len(text) * 0.2:  # Plus de 20% de caractères spéciaux
            confidence -= 0.2
        
        # Cohérence linguistique basique
        words = text.split()
        if words:
            # Mots très courts ou très longs suspects
            weird_words = sum(1 for word in words if len(word) < 2 or len(word) > 20)
            if weird_words > len(words) * 0.3:
                confidence -= 0.2
        
        # Résolution de l'image
        width, height = image.size
        total_pixels = width * height
        if total_pixels < 100000:  # Moins de 100k pixels
            confidence -= 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extraction d'entités basique du texte
        
        Args:
            text: Texte à analyser
            
        Returns:
            Dictionnaire des entités trouvées
        """
        import re
        
        entities = {
            'dates': [],
            'amounts': [],
            'emails': [],
            'phones': [],
            'numbers': []
        }
        
        # Patterns regex pour différentes entités
        patterns = {
            'dates': [
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # 23/07/2025
                r'\d{1,2}\s+\w+\s+\d{4}',          # 23 juillet 2025
            ],
            'amounts': [
                r'\d+[,\s]*\d*[.,]\d{2}\s*[€$£]',  # 1,234.56 €
                r'[€$£]\s*\d+[,\s]*\d*[.,]\d{2}',  # € 1,234.56
            ],
            'emails': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'phones': [
                r'\b(?:\+33|0)[1-9](?:[.\s-]?\d{2}){4}\b',  # Français
                r'\b\d{2}[.\s-]?\d{2}[.\s-]?\d{2}[.\s-]?\d{2}[.\s-]?\d{2}\b'
            ],
            'numbers': [
                r'\b\d+\b'
            ]
        }
        
        for entity_type, pattern_list in patterns.items():
            for pattern in pattern_list:
                matches = re.findall(pattern, text, re.IGNORECASE)
                entities[entity_type].extend(matches)
        
        # Nettoyer les doublons
        for entity_type in entities:
            entities[entity_type] = list(set(entities[entity_type]))
        
        return entities
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Retourne les informations sur le modèle actuel
        
        Returns:
            Informations détaillées sur le modèle
        """
        model_info = self.available_models.get(self.config.model_name, {})
        
        return {
            "model_name": self.config.model_name,
            "device": str(self.device),
            "batch_size": self.config.batch_size,
            "max_length": self.config.max_length,
            "fallback_enabled": self.config.fallback_to_tesseract,
            **model_info
        }
    
    def benchmark_performance(self, test_images: List[str]) -> Dict[str, Any]:
        """
        Effectue un benchmark de performance sur des images de test
        
        Args:
            test_images: Liste des chemins d'images de test
            
        Returns:
            Statistiques de performance
        """
        logger.info(f"Début du benchmark TrOCR sur {len(test_images)} images")
        
        results = []
        processing_times = []
        total_words = 0
        errors = 0
        
        start_benchmark = time.time()
        
        for i, image_path in enumerate(test_images):
            try:
                logger.debug(f"Traitement image {i+1}/{len(test_images)}: {image_path}")
                
                result = self.extract_text(image_path)
                results.append(result)
                processing_times.append(result.processing_time)
                total_words += result.word_count
                
            except Exception as e:
                logger.error(f"Erreur sur image {image_path}: {e}")
                errors += 1
        
        total_benchmark_time = time.time() - start_benchmark
        
        stats = {
            "model_used": "TrOCR",
            "model_name": self.config.model_name,
            "device": str(self.device),
            "total_images": len(test_images),
            "successful_images": len(results),
            "errors": errors,
            "total_benchmark_time": total_benchmark_time,
            "processing_times": processing_times,
            "avg_processing_time": sum(processing_times) / len(processing_times) if processing_times else 0.0,
            "min_processing_time": min(processing_times) if processing_times else 0.0,
            "max_processing_time": max(processing_times) if processing_times else 0.0,
            "total_words": total_words,
            "avg_confidence": sum(r.confidence for r in results) / len(results) if results else 0.0,
            "throughput_images_per_second": len(results) / total_benchmark_time if total_benchmark_time > 0 else 0.0,
            "throughput_words_per_second": total_words / sum(processing_times) if sum(processing_times) > 0 else 0.0
        }
        
        logger.info(f"Benchmark terminé: {stats['successful_images']}/{stats['total_images']} réussies, "
                   f"vitesse: {stats['throughput_words_per_second']:.1f} mots/sec")
        
        return stats


def extract_text_with_trocr(
    image: Union[str, Path, np.ndarray, Image.Image],
    model_name: str = "microsoft/trocr-base-printed",
    preprocess: bool = True
) -> str:
    """
    Fonction simple pour extraire du texte avec TrOCR
    
    Args:
        image: Image à traiter
        model_name: Nom du modèle TrOCR à utiliser
        preprocess: Appliquer le prétraitement
        
    Returns:
        Texte extrait
    """
    config = TrOCRConfig(model_name=model_name)
    trocr = TrOCREngine(config)
    result = trocr.extract_text(image, preprocess=preprocess)
    return result.text


# Configuration des modèles recommandés selon le type de document
RECOMMENDED_MODELS = {
    "printed_documents": "microsoft/trocr-base-printed",
    "high_accuracy": "microsoft/trocr-large-printed", 
    "handwritten": "microsoft/trocr-base-handwritten",
    "general": "microsoft/trocr-base-printed"
}


def get_recommended_model(document_type: str = "general") -> str:
    """
    Retourne le modèle TrOCR recommandé pour un type de document
    
    Args:
        document_type: Type de document (printed_documents, high_accuracy, handwritten, general)
        
    Returns:
        Nom du modèle recommandé
    """
    return RECOMMENDED_MODELS.get(document_type, RECOMMENDED_MODELS["general"])