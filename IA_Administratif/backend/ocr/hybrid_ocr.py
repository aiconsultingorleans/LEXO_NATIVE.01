"""
Pipeline OCR hybride combinant TrOCR et Tesseract
Utilise TrOCR pour la précision et Tesseract comme fallback fiable
"""

import logging
import time
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

import numpy as np
from PIL import Image

# Import des modules OCR
from .trocr_ocr import TrOCREngine, TrOCRConfig
from .tesseract_ocr import TesseractOCR, OCRResult
from .image_preprocessor import ImagePreprocessor
from .ocr_cache import OCRCacheManager, ImageHasher
from .memory_optimizer import MemoryOptimizer, memory_optimized

logger = logging.getLogger(__name__)


class OCRStrategy(Enum):
    """Stratégies de sélection du moteur OCR"""
    TROCR_ONLY = "trocr_only"
    TESSERACT_ONLY = "tesseract_only"
    TROCR_FALLBACK = "trocr_fallback"  # TrOCR -> Tesseract si échec
    BEST_CONFIDENCE = "best_confidence"  # Les deux, garde le meilleur
    ENSEMBLE = "ensemble"  # Combine les résultats des deux


@dataclass
class HybridOCRConfig:
    """Configuration pour le pipeline OCR hybride"""
    # Configuration TrOCR
    trocr_model: str = "microsoft/trocr-base-printed"
    trocr_confidence_threshold: float = 0.8
    trocr_enabled: bool = True
    
    # Configuration Tesseract
    tesseract_lang: str = "fra+eng"
    tesseract_confidence_threshold: float = 0.7
    tesseract_enabled: bool = True
    
    # Configuration hybride
    strategy: OCRStrategy = OCRStrategy.TROCR_FALLBACK
    min_text_length: int = 10  # Longueur minimale pour considérer un résultat valide
    preprocess_images: bool = True
    
    # Performance
    max_processing_time: float = 30.0  # Timeout en secondes
    enable_benchmarking: bool = False
    
    # Cache
    cache_results: bool = True
    cache_dir: Optional[str] = None


class HybridOCREngine:
    """
    Moteur OCR hybride combinant TrOCR et Tesseract
    """
    
    def __init__(self, config: Optional[HybridOCRConfig] = None):
        """
        Initialise le moteur OCR hybride avec lazy loading
        
        Args:
            config: Configuration personnalisée
        """
        self.config = config or HybridOCRConfig()
        self.preprocessor = ImagePreprocessor()
        
        # Initialisation différée des moteurs OCR (lazy loading)
        self.trocr_engine = None
        self.tesseract_engine = None
        self._engines_initialized = False
        self._initialization_in_progress = False
        
        # Cache OCR intelligent
        if self.config.cache_results:
            self.cache_manager = OCRCacheManager({
                'type': 'hybrid',
                'redis_url': 'redis://localhost:6379/0',
                'cache_dir': self.config.cache_dir,
                'max_size_mb': 200,
                'default_ttl': 24 * 3600  # 24 heures
            })
            logger.info("💾 Cache OCR intelligent activé")
        else:
            self.cache_manager = None
        
        # Optimiseur de mémoire
        self._memory_optimizer = MemoryOptimizer(
            max_ram_percent=85.0,
            max_gpu_percent=90.0,
            cleanup_threshold_mb=1000.0,  # 1GB
            auto_cleanup=True
        )
        logger.info("🧠 Optimiseur de mémoire activé")
        
        # Ne pas initialiser immédiatement - attendre le premier usage
        logger.info("🚀 HybridOCREngine initialisé avec lazy loading")
        
        # Statistiques étendues
        self.stats = {
            "total_processed": 0,
            "trocr_used": 0,
            "tesseract_used": 0,
            "fallback_used": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "avg_processing_time": 0.0,
            "success_rate": 0.0
        }
    
    def _ensure_engines_initialized(self):
        """Assure que les moteurs OCR sont initialisés (lazy loading)"""
        if self._engines_initialized:
            return
        
        if self._initialization_in_progress:
            # Attendre que l'initialisation en cours se termine
            import time
            max_wait = 30  # 30 secondes max
            waited = 0
            while self._initialization_in_progress and waited < max_wait:
                time.sleep(0.1)
                waited += 0.1
            
            if not self._engines_initialized:
                raise RuntimeError("Timeout lors de l'initialisation des moteurs OCR")
            return
        
        self._initialization_in_progress = True
        logger.info("🔄 Initialisation des moteurs OCR (première utilisation)...")
        
        try:
            self._initialize_engines()
            self._engines_initialized = True
            logger.info("✅ Moteurs OCR initialisés avec succès")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation OCR: {e}")
            raise
        finally:
            self._initialization_in_progress = False
    
    @memory_optimized(cleanup_after=False, model_id="hybrid_ocr_engines")
    def _initialize_engines(self):
        """Initialise les moteurs OCR selon la configuration"""
        try:
            # Log mémoire avant initialisation
            self._memory_optimizer.monitor.log_memory_stats("Avant init moteurs - ")
            
            # Initialisation TrOCR
            if self.config.trocr_enabled:
                logger.info("Initialisation du moteur TrOCR...")
                trocr_config = TrOCRConfig(
                    model_name=self.config.trocr_model,
                    confidence_threshold=self.config.trocr_confidence_threshold,
                    fallback_to_tesseract=False,  # On gère le fallback nous-mêmes
                    cache_dir=self.config.cache_dir
                )
                self.trocr_engine = TrOCREngine(trocr_config)
                
                # Enregistrer le modèle TrOCR pour monitoring mémoire
                self._memory_optimizer.register_model(
                    "trocr_engine", 
                    self.trocr_engine,
                    cleanup_callback=self._cleanup_trocr
                )
                logger.info("TrOCR initialisé avec succès")
            
            # Initialisation Tesseract
            if self.config.tesseract_enabled:
                logger.info("Initialisation du moteur Tesseract...")
                self.tesseract_engine = TesseractOCR(
                    default_lang=self.config.tesseract_lang
                )
                
                # Enregistrer Tesseract pour monitoring
                self._memory_optimizer.register_model(
                    "tesseract_engine",
                    self.tesseract_engine,
                    cleanup_callback=self._cleanup_tesseract
                )
                logger.info("Tesseract initialisé avec succès")
            
            # Vérification qu'au moins un moteur est disponible
            if not self.trocr_engine and not self.tesseract_engine:
                raise RuntimeError("Aucun moteur OCR n'a pu être initialisé")
            
            # Log mémoire après initialisation
            self._memory_optimizer.monitor.log_memory_stats("Après init moteurs - ")
                
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des moteurs OCR: {str(e)}")
            raise
    
    def extract_text(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        strategy: Optional[OCRStrategy] = None
    ) -> OCRResult:
        """
        Extrait le texte en utilisant la stratégie définie
        
        Args:
            image: Image à traiter
            strategy: Stratégie spécifique à utiliser (override la config)
            
        Returns:
            Résultat OCR optimal
        """
        start_time = time.time()
        strategy = strategy or self.config.strategy
        
        # Vérifier le cache d'abord
        if self.cache_manager:
            cached_result = self.cache_manager.get_cached_result(
                image, 
                f"hybrid_{strategy.value}",
                {"strategy": strategy.value}
            )
            if cached_result:
                self.stats["cache_hits"] += 1
                self.stats["total_processed"] += 1
                processing_time = time.time() - start_time
                cached_result.quality_metrics["from_cache"] = True
                cached_result.quality_metrics["cache_retrieval_time"] = processing_time
                logger.info(f"🎯 Cache hit pour stratégie {strategy} ({processing_time:.3f}s)")
                return cached_result
            else:
                self.stats["cache_misses"] += 1
        
        # Initialisation différée des moteurs OCR
        self._ensure_engines_initialized()
        
        logger.info(f"Extraction hybride avec stratégie: {strategy}")
        
        try:
            # Prétraitement si activé
            processed_image = self._preprocess_if_needed(image)
            
            # Sélection de la stratégie
            if strategy == OCRStrategy.TROCR_ONLY:
                result = self._extract_with_trocr_only(processed_image)
            elif strategy == OCRStrategy.TESSERACT_ONLY:
                result = self._extract_with_tesseract_only(processed_image)
            elif strategy == OCRStrategy.TROCR_FALLBACK:
                result = self._extract_with_fallback(processed_image)
            elif strategy == OCRStrategy.BEST_CONFIDENCE:
                result = self._extract_best_confidence(processed_image)
            elif strategy == OCRStrategy.ENSEMBLE:
                result = self._extract_ensemble(processed_image)
            else:
                raise ValueError(f"Stratégie non supportée: {strategy}")
            
            # Mise à jour des statistiques
            self._update_stats(result, time.time() - start_time)
            
            # Mettre en cache le résultat si le cache est activé
            if self.cache_manager and result.confidence > 0.1:  # Ne cacher que les résultats valides
                try:
                    self.cache_manager.cache_result(
                        image,
                        f"hybrid_{strategy.value}",
                        result,
                        {"strategy": strategy.value}
                    )
                    logger.debug(f"💾 Résultat mis en cache pour stratégie {strategy}")
                except Exception as cache_error:
                    logger.warning(f"Erreur mise en cache: {cache_error}")
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de l'extraction hybride: {str(e)}")
            
            # Fallback d'urgence vers Tesseract si disponible
            if self.tesseract_engine and strategy != OCRStrategy.TESSERACT_ONLY:
                try:
                    logger.info("Fallback d'urgence vers Tesseract")
                    result = self.tesseract_engine.extract_text(image, preprocess=False)
                    result.quality_metrics["emergency_fallback"] = True
                    result.quality_metrics["original_error"] = str(e)
                    return result
                except:
                    pass
            
            # Retour d'un résultat vide si tout échoue
            return OCRResult(
                text="",
                confidence=0.0,
                language="unknown",
                processing_time=time.time() - start_time,
                word_count=0,
                line_count=0,
                bbox_data=[],
                detected_entities={},
                quality_metrics={"error": str(e), "strategy": str(strategy)}
            )
    
    def _preprocess_if_needed(self, image: Union[str, Path, np.ndarray, Image.Image]) -> Union[str, Path, np.ndarray, Image.Image]:
        """Applique le prétraitement si configuré"""
        if not self.config.preprocess_images:
            return image
        
        try:
            # Pour l'instant, on retourne l'image originale
            # Le prétraitement sera fait individuellement par chaque moteur
            return image
        except Exception as e:
            logger.warning(f"Erreur prétraitement, utilisation image originale: {e}")
            return image
    
    def _extract_with_trocr_only(self, image) -> OCRResult:
        """Extraction avec TrOCR uniquement"""
        if not self.trocr_engine:
            raise RuntimeError("TrOCR non disponible")
        
        logger.debug("Extraction TrOCR uniquement")
        result = self.trocr_engine.extract_text(image, preprocess=self.config.preprocess_images)
        result.quality_metrics["strategy_used"] = "trocr_only"
        self.stats["trocr_used"] += 1
        
        return result
    
    def _extract_with_tesseract_only(self, image) -> OCRResult:
        """Extraction avec Tesseract uniquement"""
        if not self.tesseract_engine:
            raise RuntimeError("Tesseract non disponible")
        
        logger.debug("Extraction Tesseract uniquement")
        result = self.tesseract_engine.extract_text(image, preprocess=self.config.preprocess_images)
        result.quality_metrics["strategy_used"] = "tesseract_only"
        self.stats["tesseract_used"] += 1
        
        return result
    
    def _extract_with_fallback(self, image) -> OCRResult:
        """Extraction TrOCR avec fallback Tesseract"""
        logger.debug("Extraction avec fallback TrOCR → Tesseract")
        
        # Essayer TrOCR d'abord
        if self.trocr_engine:
            try:
                trocr_result = self.trocr_engine.extract_text(
                    image, 
                    preprocess=self.config.preprocess_images,
                    use_fallback=False
                )
                
                # Vérifier si le résultat TrOCR est acceptable
                if self._is_result_acceptable(trocr_result, "trocr"):
                    trocr_result.quality_metrics["strategy_used"] = "trocr_primary"
                    self.stats["trocr_used"] += 1
                    return trocr_result
                
                logger.info(f"Résultat TrOCR non satisfaisant (confiance: {trocr_result.confidence:.3f}), "
                           f"fallback vers Tesseract")
                
            except Exception as e:
                logger.warning(f"Erreur TrOCR: {e}, fallback vers Tesseract")
        
        # Fallback vers Tesseract
        if self.tesseract_engine:
            try:
                tesseract_result = self.tesseract_engine.extract_text(
                    image, 
                    preprocess=self.config.preprocess_images
                )
                tesseract_result.quality_metrics["strategy_used"] = "tesseract_fallback"
                tesseract_result.quality_metrics["fallback_reason"] = "trocr_insufficient"
                self.stats["tesseract_used"] += 1
                self.stats["fallback_used"] += 1
                
                return tesseract_result
                
            except Exception as e:
                logger.error(f"Fallback Tesseract également échoué: {e}")
        
        # Si tout échoue
        raise RuntimeError("Tous les moteurs OCR ont échoué")
    
    def _extract_best_confidence(self, image) -> OCRResult:
        """Extraction avec les deux moteurs, retourne le meilleur"""
        logger.debug("Extraction avec sélection du meilleur résultat")
        
        results = []
        
        # Essayer TrOCR
        if self.trocr_engine:
            try:
                trocr_result = self.trocr_engine.extract_text(image, preprocess=self.config.preprocess_images)
                trocr_result.quality_metrics["engine"] = "trocr"
                results.append(trocr_result)
                self.stats["trocr_used"] += 1
            except Exception as e:
                logger.warning(f"Erreur TrOCR: {e}")
        
        # Essayer Tesseract
        if self.tesseract_engine:
            try:
                tesseract_result = self.tesseract_engine.extract_text(image, preprocess=self.config.preprocess_images)
                tesseract_result.quality_metrics["engine"] = "tesseract"
                results.append(tesseract_result)
                self.stats["tesseract_used"] += 1
            except Exception as e:
                logger.warning(f"Erreur Tesseract: {e}")
        
        if not results:
            raise RuntimeError("Aucun moteur OCR n'a réussi")
        
        # Sélectionner le meilleur résultat
        best_result = max(results, key=lambda r: self._calculate_result_score(r))
        best_result.quality_metrics["strategy_used"] = "best_confidence"
        best_result.quality_metrics["alternatives_count"] = len(results) - 1
        
        logger.info(f"Meilleur résultat: {best_result.quality_metrics.get('engine', 'unknown')} "
                   f"(score: {self._calculate_result_score(best_result):.3f})")
        
        return best_result
    
    def _extract_ensemble(self, image) -> OCRResult:
        """Extraction ensemble combinant TrOCR et Tesseract"""
        logger.debug("Extraction ensemble (combinaison des résultats)")
        
        results = []
        
        # Exécuter les deux moteurs
        if self.trocr_engine:
            try:
                trocr_result = self.trocr_engine.extract_text(image, preprocess=self.config.preprocess_images)
                results.append(("trocr", trocr_result))
                self.stats["trocr_used"] += 1
            except Exception as e:
                logger.warning(f"Erreur TrOCR: {e}")
        
        if self.tesseract_engine:
            try:
                tesseract_result = self.tesseract_engine.extract_text(image, preprocess=self.config.preprocess_images)
                results.append(("tesseract", tesseract_result))
                self.stats["tesseract_used"] += 1
            except Exception as e:
                logger.warning(f"Erreur Tesseract: {e}")
        
        if not results:
            raise RuntimeError("Aucun moteur OCR n'a réussi")
        
        # Combiner les résultats
        if len(results) == 1:
            # Un seul résultat disponible
            engine, result = results[0]
            result.quality_metrics["strategy_used"] = f"ensemble_single_{engine}"
            return result
        
        # Combiner plusieurs résultats
        combined_result = self._combine_results(results)
        combined_result.quality_metrics["strategy_used"] = "ensemble_combined"
        
        return combined_result
    
    def _is_result_acceptable(self, result: OCRResult, engine: str) -> bool:
        """Vérifie si un résultat OCR est acceptable"""
        # Vérification du seuil de confiance
        threshold = (self.config.trocr_confidence_threshold if engine == "trocr" 
                    else self.config.tesseract_confidence_threshold)
        
        if result.confidence < threshold:
            return False
        
        # Vérification de la longueur minimale
        if len(result.text.strip()) < self.config.min_text_length:
            return False
        
        # Vérification basique de cohérence
        if result.word_count == 0:
            return False
        
        return True
    
    def _calculate_result_score(self, result: OCRResult) -> float:
        """Calcule un score composite pour évaluer la qualité d'un résultat"""
        score = 0.0
        
        # Score de confiance (poids: 40%)
        score += result.confidence * 0.4
        
        # Longueur du texte (poids: 20%)
        text_length_score = min(1.0, len(result.text.strip()) / 100.0)  # Normaliser à 100 caractères
        score += text_length_score * 0.2
        
        # Nombre de mots (poids: 20%)
        word_count_score = min(1.0, result.word_count / 50.0)  # Normaliser à 50 mots
        score += word_count_score * 0.2
        
        # Cohérence du texte (poids: 20%)
        coherence_score = self._calculate_text_coherence(result.text)
        score += coherence_score * 0.2
        
        return score
    
    def _calculate_text_coherence(self, text: str) -> float:
        """Calcule un score de cohérence du texte"""
        if not text.strip():
            return 0.0
        
        score = 0.8  # Score de base
        
        # Pénalité pour trop de caractères spéciaux
        special_chars = sum(1 for c in text if not c.isalnum() and c not in ' .,!?;:\n-()[]{}')
        if len(text) > 0:
            special_ratio = special_chars / len(text)
            if special_ratio > 0.3:
                score -= 0.3
        
        # Bonus pour la présence de mots cohérents
        words = text.split()
        if words:
            # Mots de longueur raisonnable
            reasonable_words = sum(1 for word in words if 2 <= len(word) <= 15)
            if len(words) > 0:
                reasonable_ratio = reasonable_words / len(words)
                score += (reasonable_ratio - 0.5) * 0.2  # Bonus si >50% de mots raisonnables
        
        return max(0.0, min(1.0, score))
    
    def _combine_results(self, results: List[Tuple[str, OCRResult]]) -> OCRResult:
        """Combine plusieurs résultats OCR"""
        if len(results) == 1:
            return results[0][1]
        
        # Pour l'instant, sélectionner le résultat avec la meilleure confiance
        # TODO: Implémenter une vraie logique d'ensemble
        best_engine, best_result = max(results, key=lambda x: x[1].confidence)
        
        # Ajouter des métadonnées sur la combinaison
        best_result.quality_metrics["ensemble_engines"] = [engine for engine, _ in results]
        best_result.quality_metrics["ensemble_confidences"] = {
            engine: result.confidence for engine, result in results
        }
        best_result.quality_metrics["selected_engine"] = best_engine
        
        return best_result
    
    def _update_stats(self, result: OCRResult, processing_time: float):
        """Met à jour les statistiques globales"""
        self.stats["total_processed"] += 1
        
        # Moyenne mobile du temps de traitement
        n = self.stats["total_processed"]
        self.stats["avg_processing_time"] = (
            (self.stats["avg_processing_time"] * (n - 1) + processing_time) / n
        )
        
        # Taux de succès
        success = len(result.text.strip()) > 0 and result.confidence > 0.1
        current_success_rate = self.stats["success_rate"]
        self.stats["success_rate"] = ((current_success_rate * (n - 1) + (1.0 if success else 0.0)) / n)
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du moteur hybride"""
        stats = self.stats.copy()
        
        # Ajouter les statistiques de cache si disponible
        if self.cache_manager:
            cache_stats = self.cache_manager.get_cache_stats()
            stats["cache_stats"] = cache_stats
            
            # Calculer le taux de hit du cache
            total_cache_requests = stats["cache_hits"] + stats["cache_misses"]
            if total_cache_requests > 0:
                stats["cache_hit_rate"] = round(stats["cache_hits"] / total_cache_requests * 100, 1)
            else:
                stats["cache_hit_rate"] = 0.0
        
        return stats
    
    def _cleanup_trocr(self):
        """Callback de nettoyage pour TrOCR"""
        if hasattr(self, 'trocr_engine') and self.trocr_engine:
            try:
                # Libérer les ressources TrOCR
                if hasattr(self.trocr_engine, 'model') and self.trocr_engine.model:
                    self.trocr_engine.model = None
                if hasattr(self.trocr_engine, 'processor') and self.trocr_engine.processor:
                    self.trocr_engine.processor = None
                self.trocr_engine = None
                logger.info("🧹 TrOCR engine libéré")
            except Exception as e:
                logger.warning(f"Erreur nettoyage TrOCR: {e}")
    
    def _cleanup_tesseract(self):
        """Callback de nettoyage pour Tesseract"""
        if hasattr(self, 'tesseract_engine') and self.tesseract_engine:
            try:
                self.tesseract_engine = None
                logger.info("🧹 Tesseract engine libéré")
            except Exception as e:
                logger.warning(f"Erreur nettoyage Tesseract: {e}")
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de mémoire détaillées"""
        if hasattr(self, '_memory_optimizer'):
            return self._memory_optimizer.get_memory_report()
        return {}
    
    def cleanup_memory(self, aggressive: bool = False) -> Dict[str, Any]:
        """
        Force un nettoyage de mémoire
        
        Args:
            aggressive: Nettoyage agressif (décharge les modèles)
            
        Returns:
            Statistiques du nettoyage
        """
        if hasattr(self, '_memory_optimizer'):
            return self._memory_optimizer.cleanup_memory(aggressive)
        return {}
    
    def __del__(self):
        """Destructeur avec nettoyage automatique"""
        try:
            if hasattr(self, '_memory_optimizer'):
                self._memory_optimizer.stop_monitoring()
                if hasattr(self, 'trocr_engine') or hasattr(self, 'tesseract_engine'):
                    self._memory_optimizer.cleanup_memory(aggressive=True)
        except:
            pass
    
    def get_engine_info(self) -> Dict[str, Any]:
        """Retourne les informations sur les moteurs disponibles"""
        info = {
            "strategy": str(self.config.strategy),
            "preprocessing_enabled": self.config.preprocess_images,
            "engines": {}
        }
        
        if self.trocr_engine:
            info["engines"]["trocr"] = self.trocr_engine.get_model_info()
        
        if self.tesseract_engine:
            info["engines"]["tesseract"] = {
                "default_language": self.tesseract_engine.default_lang,
                "supported_languages": list(self.tesseract_engine.supported_languages)
            }
        
        return info
    
    def benchmark_performance(self, test_images: List[str]) -> Dict[str, Any]:
        """Effectue un benchmark complet du système hybride"""
        logger.info(f"Benchmark hybride démarré sur {len(test_images)} images")
        
        results = []
        strategy_stats = {strategy: 0 for strategy in OCRStrategy}
        
        start_time = time.time()
        
        for image_path in test_images:
            try:
                result = self.extract_text(image_path)
                results.append(result)
                
                # Compter les stratégies utilisées
                strategy_used = result.quality_metrics.get("strategy_used", "unknown")
                if strategy_used in [s.value for s in OCRStrategy]:
                    strategy_stats[OCRStrategy(strategy_used)] += 1
                    
            except Exception as e:
                logger.error(f"Erreur benchmark sur {image_path}: {e}")
        
        total_time = time.time() - start_time
        
        benchmark_stats = {
            "hybrid_ocr_benchmark": True,
            "strategy_configured": str(self.config.strategy),
            "total_images": len(test_images),
            "successful_extractions": len(results),
            "total_benchmark_time": total_time,
            "avg_confidence": sum(r.confidence for r in results) / len(results) if results else 0.0,
            "total_words": sum(r.word_count for r in results),
            "strategy_usage": {str(k): v for k, v in strategy_stats.items()},
            "global_stats": self.get_stats(),
            "throughput": len(results) / total_time if total_time > 0 else 0.0
        }
        
        logger.info(f"Benchmark terminé: {len(results)}/{len(test_images)} réussies")
        return benchmark_stats


# Fonction utilitaire pour extraction simple
def extract_text_hybrid(
    image: Union[str, Path, np.ndarray, Image.Image],
    strategy: OCRStrategy = OCRStrategy.TROCR_FALLBACK,
    trocr_model: str = "microsoft/trocr-base-printed"
) -> str:
    """
    Fonction simple pour extraction de texte hybride
    
    Args:
        image: Image à traiter
        strategy: Stratégie OCR à utiliser
        trocr_model: Modèle TrOCR à utiliser
        
    Returns:
        Texte extrait
    """
    config = HybridOCRConfig(
        strategy=strategy,
        trocr_model=trocr_model
    )
    
    engine = HybridOCREngine(config)
    result = engine.extract_text(image)
    return result.text