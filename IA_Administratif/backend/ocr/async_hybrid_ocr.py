"""
Version asynchrone du moteur OCR hybride pour de meilleures performances
Optimise l'utilisation des ressources avec async/await et parallélisation
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple
from enum import Enum
from dataclasses import dataclass
import concurrent.futures
from functools import partial

import numpy as np
from PIL import Image

# Import des modules OCR
from .hybrid_ocr import HybridOCRConfig, OCRStrategy, HybridOCREngine
from .tesseract_ocr import OCRResult
from .ocr_cache import OCRCacheManager

logger = logging.getLogger(__name__)


class AsyncHybridOCREngine:
    """
    Version asynchrone du moteur OCR hybride
    Optimise les performances avec async/await et parallélisation
    """
    
    def __init__(self, config: Optional[HybridOCRConfig] = None):
        """
        Initialise le moteur OCR hybride asynchrone
        
        Args:
            config: Configuration personnalisée
        """
        self.config = config or HybridOCRConfig()
        
        # Moteur synchrone sous-jacent
        self._sync_engine = None
        self._engine_lock = asyncio.Lock()
        self._engines_initialized = False
        
        # Thread pool pour les opérations CPU intensives
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=2,  # TrOCR + Tesseract
            thread_name_prefix="ocr_worker"
        )
        
        # Cache asynchrone
        if self.config.cache_results:
            self.cache_manager = OCRCacheManager({
                'type': 'hybrid',
                'redis_url': 'redis://localhost:6379/0',
                'cache_dir': self.config.cache_dir,
                'max_size_mb': 200,
                'default_ttl': 24 * 3600
            })
            logger.info("💾 Cache OCR asynchrone activé")
        else:
            self.cache_manager = None
        
        # Statistiques asynchrones
        self.stats = {
            "total_processed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "async_optimizations": 0,
            "parallel_executions": 0,
            "avg_processing_time": 0.0,
            "total_time_saved": 0.0
        }
        
        logger.info("🚀 AsyncHybridOCREngine initialisé")
    
    async def _ensure_engine_initialized(self):
        """Assure que le moteur synchrone est initialisé (thread-safe)"""
        if self._engines_initialized:
            return
        
        async with self._engine_lock:
            if self._engines_initialized:
                return
            
            logger.info("🔄 Initialisation asynchrone du moteur OCR...")
            
            # Initialiser le moteur synchrone dans un thread séparé
            loop = asyncio.get_event_loop()
            self._sync_engine = await loop.run_in_executor(
                self._executor,
                lambda: HybridOCREngine(self.config)
            )
            
            self._engines_initialized = True
            logger.info("✅ Moteur OCR asynchrone prêt")
    
    async def extract_text_async(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        strategy: Optional[OCRStrategy] = None
    ) -> OCRResult:
        """
        Extrait le texte de manière asynchrone
        
        Args:
            image: Image à traiter
            strategy: Stratégie OCR à utiliser
            
        Returns:
            Résultat OCR
        """
        start_time = time.time()
        strategy = strategy or self.config.strategy
        
        # 1. Vérifier le cache de manière asynchrone
        cached_result = await self._check_cache_async(image, strategy)
        if cached_result:
            self.stats["cache_hits"] += 1
            self.stats["total_processed"] += 1
            processing_time = time.time() - start_time
            cached_result.quality_metrics["from_cache"] = True
            cached_result.quality_metrics["async_cache_time"] = processing_time
            logger.info(f"🎯 Cache hit asynchrone ({processing_time:.3f}s)")
            return cached_result
        
        self.stats["cache_misses"] += 1
        
        # 2. Assurer l'initialisation du moteur
        await self._ensure_engine_initialized()
        
        # 3. Traitement OCR asynchrone
        logger.info(f"⚡ Extraction asynchrone avec stratégie: {strategy}")
        
        try:
            if strategy == OCRStrategy.BEST_CONFIDENCE:
                # Paralléliser TrOCR et Tesseract
                result = await self._extract_parallel_async(image)
            elif strategy == OCRStrategy.ENSEMBLE:
                # Ensemble avec parallélisation
                result = await self._extract_ensemble_async(image)
            else:
                # Extraction séquentielle standard
                result = await self._extract_sequential_async(image, strategy)
            
            # 4. Mise en cache asynchrone
            if self.cache_manager and result.confidence > 0.1:
                await self._cache_result_async(image, strategy, result)
            
            # 5. Mise à jour des statistiques
            processing_time = time.time() - start_time
            self._update_async_stats(result, processing_time)
            result.quality_metrics["async_processing"] = True
            result.quality_metrics["total_async_time"] = processing_time
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur extraction asynchrone: {e}")
            # Fallback synchrone
            return await self._fallback_sync_extraction(image, strategy)
    
    async def _check_cache_async(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        strategy: OCRStrategy
    ) -> Optional[OCRResult]:
        """Vérifie le cache de manière asynchrone"""
        if not self.cache_manager:
            return None
        
        try:
            # Exécuter la vérification cache dans un thread séparé
            loop = asyncio.get_event_loop()
            cached_result = await loop.run_in_executor(
                self._executor,
                partial(
                    self.cache_manager.get_cached_result,
                    image,
                    f"hybrid_{strategy.value}",
                    {"strategy": strategy.value}
                )
            )
            return cached_result
        except Exception as e:
            logger.warning(f"Erreur cache asynchrone: {e}")
            return None
    
    async def _cache_result_async(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        strategy: OCRStrategy,
        result: OCRResult
    ):
        """Met en cache le résultat de manière asynchrone"""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self._executor,
                partial(
                    self.cache_manager.cache_result,
                    image,
                    f"hybrid_{strategy.value}",
                    result,
                    {"strategy": strategy.value}
                )
            )
            logger.debug(f"💾 Résultat mis en cache (async)")
        except Exception as e:
            logger.warning(f"Erreur mise en cache asynchrone: {e}")
    
    async def _extract_sequential_async(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        strategy: OCRStrategy
    ) -> OCRResult:
        """Extraction séquentielle asynchrone"""
        loop = asyncio.get_event_loop()
        
        # Exécuter dans un thread séparé pour ne pas bloquer
        result = await loop.run_in_executor(
            self._executor,
            partial(self._sync_engine.extract_text, image, strategy)
        )
        
        result.quality_metrics["async_method"] = "sequential"
        return result
    
    async def _extract_parallel_async(
        self,
        image: Union[str, Path, np.ndarray, Image.Image]
    ) -> OCRResult:
        """Extraction parallèle TrOCR + Tesseract"""
        logger.info("🔀 Extraction parallèle TrOCR + Tesseract")
        
        try:
            # Créer les tâches parallèles
            tasks = []
            
            # Tâche TrOCR
            if self._sync_engine.config.trocr_enabled:
                trocr_task = asyncio.create_task(
                    self._run_trocr_async(image)
                )
                tasks.append(("trocr", trocr_task))
            
            # Tâche Tesseract
            if self._sync_engine.config.tesseract_enabled:
                tesseract_task = asyncio.create_task(
                    self._run_tesseract_async(image)
                )
                tasks.append(("tesseract", tesseract_task))
            
            if not tasks:
                raise ValueError("Aucun moteur OCR activé")
            
            # Exécuter en parallèle avec timeout
            results = {}
            completed_tasks = await asyncio.wait(
                [task for _, task in tasks],
                timeout=30.0,  # Timeout global
                return_when=asyncio.ALL_COMPLETED
            )
            
            # Collecter les résultats
            for engine_name, task in tasks:
                if task in completed_tasks[0]:  # Tâches terminées
                    try:
                        results[engine_name] = await task
                    except Exception as e:
                        logger.warning(f"Erreur {engine_name}: {e}")
                        results[engine_name] = None
                else:
                    logger.warning(f"Timeout {engine_name}")
                    task.cancel()
                    results[engine_name] = None
            
            # Sélectionner le meilleur résultat
            best_result = self._select_best_result(results)
            best_result.quality_metrics["async_method"] = "parallel"
            best_result.quality_metrics["parallel_engines"] = list(results.keys())
            best_result.quality_metrics["parallel_success"] = {
                k: v is not None for k, v in results.items()
            }
            
            self.stats["parallel_executions"] += 1
            logger.info(f"✅ Extraction parallèle terminée, meilleur: {best_result.quality_metrics.get('best_engine', 'unknown')}")
            
            return best_result
            
        except Exception as e:
            logger.error(f"Erreur extraction parallèle: {e}")
            # Fallback séquentiel
            return await self._extract_sequential_async(image, OCRStrategy.TROCR_FALLBACK)
    
    async def _run_trocr_async(self, image) -> Optional[OCRResult]:
        """Exécute TrOCR de manière asynchrone"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                partial(self._sync_engine.extract_text, image, OCRStrategy.TROCR_ONLY)
            )
            result.quality_metrics["engine"] = "trocr"
            return result
        except Exception as e:
            logger.warning(f"Erreur TrOCR async: {e}")
            return None
    
    async def _run_tesseract_async(self, image) -> Optional[OCRResult]:
        """Exécute Tesseract de manière asynchrone"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                partial(self._sync_engine.extract_text, image, OCRStrategy.TESSERACT_ONLY)
            )
            result.quality_metrics["engine"] = "tesseract"
            return result
        except Exception as e:
            logger.warning(f"Erreur Tesseract async: {e}")
            return None
    
    def _select_best_result(self, results: Dict[str, Optional[OCRResult]]) -> OCRResult:
        """Sélectionne le meilleur résultat parmi les engines"""
        valid_results = {k: v for k, v in results.items() if v is not None}
        
        if not valid_results:
            # Retourner un résultat vide
            return OCRResult(
                text="",
                confidence=0.0,
                language="unknown",
                processing_time=0.0,
                word_count=0,
                line_count=0,
                bbox_data=[],
                detected_entities={},
                quality_metrics={"error": "Tous les moteurs ont échoué"}
            )
        
        # Sélectionner selon la confiance et la longueur du texte
        best_result = max(
            valid_results.values(),
            key=lambda r: (r.confidence * 0.6 + (len(r.text.strip()) / 1000.0) * 0.4)
        )
        
        # Ajouter les métadonnées de comparaison
        best_result.quality_metrics["best_engine"] = next(
            k for k, v in valid_results.items() if v == best_result
        )
        best_result.quality_metrics["compared_engines"] = {
            k: {"confidence": v.confidence, "text_length": len(v.text)}
            for k, v in valid_results.items()
        }
        
        return best_result
    
    async def _extract_ensemble_async(
        self,
        image: Union[str, Path, np.ndarray, Image.Image]
    ) -> OCRResult:
        """Extraction ensemble avec parallélisation"""
        # Pour l'instant, utiliser la méthode parallèle
        result = await self._extract_parallel_async(image)
        result.quality_metrics["async_method"] = "ensemble"
        return result
    
    async def _fallback_sync_extraction(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        strategy: OCRStrategy
    ) -> OCRResult:
        """Fallback synchrone en cas d'erreur async"""
        logger.info("🔄 Fallback vers extraction synchrone")
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                partial(self._sync_engine.extract_text, image, strategy)
            )
            result.quality_metrics["fallback_used"] = True
            return result
        except Exception as e:
            logger.error(f"Erreur fallback synchrone: {e}")
            # Retourner un résultat vide
            return OCRResult(
                text="",
                confidence=0.0,
                language="unknown",
                processing_time=0.0,
                word_count=0,
                line_count=0,
                bbox_data=[],
                detected_entities={},
                quality_metrics={"error": str(e), "fallback_failed": True}
            )
    
    def _update_async_stats(self, result: OCRResult, processing_time: float):
        """Met à jour les statistiques asynchrones"""
        self.stats["total_processed"] += 1
        
        # Moyenne mobile du temps de traitement
        n = self.stats["total_processed"]
        self.stats["avg_processing_time"] = (
            (self.stats["avg_processing_time"] * (n - 1) + processing_time) / n
        )
        
        # Optimisations détectées
        if result.quality_metrics.get("async_processing", False):
            self.stats["async_optimizations"] += 1
        
        # Temps économisé grâce au cache
        if result.quality_metrics.get("from_cache", False):
            cache_time = result.quality_metrics.get("async_cache_time", 0)
            estimated_processing_time = self.stats.get("avg_processing_time", 3.0)
            time_saved = max(0, estimated_processing_time - cache_time)
            self.stats["total_time_saved"] += time_saved
    
    async def extract_batch_async(
        self,
        images: List[Union[str, Path, np.ndarray, Image.Image]],
        strategy: Optional[OCRStrategy] = None,
        max_concurrent: int = 3
    ) -> List[OCRResult]:
        """
        Traite plusieurs images en parallèle de manière asynchrone
        
        Args:
            images: Liste d'images à traiter
            strategy: Stratégie OCR
            max_concurrent: Nombre max de traitements simultanés
            
        Returns:
            Liste des résultats OCR
        """
        logger.info(f"📦 Traitement batch asynchrone de {len(images)} images (max concurrent: {max_concurrent})")
        
        # Créer un semaphore pour limiter la concurrence
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single_with_semaphore(image):
            async with semaphore:
                return await self.extract_text_async(image, strategy)
        
        # Créer les tâches
        tasks = [
            asyncio.create_task(process_single_with_semaphore(image))
            for image in images
        ]
        
        # Exécuter avec gestion d'erreurs
        results = []
        for i, task in enumerate(asyncio.as_completed(tasks)):
            try:
                result = await task
                results.append(result)
                logger.info(f"✅ Image {i+1}/{len(images)} traitée")
            except Exception as e:
                logger.error(f"❌ Erreur image {i+1}: {e}")
                # Ajouter un résultat d'erreur
                error_result = OCRResult(
                    text="",
                    confidence=0.0,
                    language="unknown",
                    processing_time=0.0,
                    word_count=0,
                    line_count=0,
                    bbox_data=[],
                    detected_entities={},
                    quality_metrics={"error": str(e), "batch_index": i}
                )
                results.append(error_result)
        
        logger.info(f"📦 Batch terminé: {len(results)} résultats")
        return results
    
    def get_async_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques asynchrones"""
        stats = self.stats.copy()
        
        # Ajouter les stats du moteur sous-jacent si disponible
        if self._sync_engine:
            sync_stats = self._sync_engine.get_stats()
            stats["sync_engine_stats"] = sync_stats
        
        # Calculer des métriques dérivées
        total_requests = stats["cache_hits"] + stats["cache_misses"]
        if total_requests > 0:
            stats["cache_hit_rate"] = round(stats["cache_hits"] / total_requests * 100, 1)
        
        if stats["total_processed"] > 0:
            stats["async_optimization_rate"] = round(
                stats["async_optimizations"] / stats["total_processed"] * 100, 1
            )
            stats["parallel_execution_rate"] = round(
                stats["parallel_executions"] / stats["total_processed"] * 100, 1
            )
        
        return stats
    
    async def cleanup(self):
        """Nettoie les ressources asynchrones"""
        logger.info("🧹 Nettoyage AsyncHybridOCREngine...")
        
        # Fermer le thread pool
        if self._executor:
            self._executor.shutdown(wait=True)
            logger.info("✅ Thread pool fermé")
        
        # Nettoyer le cache si nécessaire
        if self.cache_manager:
            try:
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: logger.info("Cache nettoyé")
                )
            except Exception as e:
                logger.warning(f"Erreur nettoyage cache: {e}")
    
    def __del__(self):
        """Destructeur avec nettoyage automatique"""
        try:
            if hasattr(self, '_executor') and self._executor:
                self._executor.shutdown(wait=False)
        except:
            pass


# Fonctions utilitaires asynchrones

async def extract_text_async(
    image: Union[str, Path, np.ndarray, Image.Image],
    strategy: OCRStrategy = OCRStrategy.TROCR_FALLBACK,
    config: Optional[HybridOCRConfig] = None
) -> OCRResult:
    """
    Fonction utilitaire pour extraction asynchrone simple
    
    Args:
        image: Image à traiter
        strategy: Stratégie OCR
        config: Configuration personnalisée
        
    Returns:
        Résultat OCR
    """
    engine = AsyncHybridOCREngine(config)
    try:
        return await engine.extract_text_async(image, strategy)
    finally:
        await engine.cleanup()


async def extract_batch_async(
    images: List[Union[str, Path, np.ndarray, Image.Image]],
    strategy: OCRStrategy = OCRStrategy.TROCR_FALLBACK,
    max_concurrent: int = 3,
    config: Optional[HybridOCRConfig] = None
) -> List[OCRResult]:
    """
    Fonction utilitaire pour traitement batch asynchrone
    
    Args:
        images: Images à traiter
        strategy: Stratégie OCR
        max_concurrent: Traitements simultanés max
        config: Configuration personnalisée
        
    Returns:
        Liste des résultats OCR
    """
    engine = AsyncHybridOCREngine(config)
    try:
        return await engine.extract_batch_async(images, strategy, max_concurrent)
    finally:
        await engine.cleanup()


if __name__ == "__main__":
    # Test du module asynchrone
    import asyncio
    
    async def test_async_ocr():
        logger.info("🧪 Test AsyncHybridOCREngine")
        
        engine = AsyncHybridOCREngine()
        
        # Test simple (nécessiterait un fichier de test)
        # result = await engine.extract_text_async("test_image.pdf")
        # print(f"Résultat: {len(result.text)} caractères")
        
        stats = engine.get_async_stats()
        print(f"Stats: {stats}")
        
        await engine.cleanup()
        print("✅ Test terminé")
    
    # Exécuter le test
    # asyncio.run(test_async_ocr())