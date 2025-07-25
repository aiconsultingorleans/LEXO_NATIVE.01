"""
Optimiseur de mémoire pour les moteurs OCR
Gestion intelligente de la mémoire GPU/CPU et cleanup automatique
"""

import gc
import logging
import time
import threading
import psutil
import os
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from functools import wraps
import weakref

logger = logging.getLogger(__name__)

# Essayer d'importer les modules GPU disponibles
GPU_AVAILABLE = False
try:
    import torch
    GPU_AVAILABLE = torch.cuda.is_available() or (
        hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()
    )
except ImportError:
    torch = None


@dataclass
class MemoryStats:
    """Statistiques de mémoire système"""
    total_ram_gb: float
    available_ram_gb: float
    used_ram_gb: float
    ram_percent: float
    gpu_available: bool
    gpu_memory_total_gb: float = 0.0
    gpu_memory_used_gb: float = 0.0
    gpu_memory_free_gb: float = 0.0
    process_memory_mb: float = 0.0


class MemoryMonitor:
    """
    Moniteur de mémoire système et GPU
    """
    
    def __init__(self):
        self.process = psutil.Process()
        self._last_check = 0
        self._cache_duration = 1.0  # Cache stats for 1 second
        self._cached_stats = None
    
    def get_memory_stats(self, force_refresh: bool = False) -> MemoryStats:
        """
        Obtient les statistiques de mémoire actuelles
        
        Args:
            force_refresh: Forcer le rafraîchissement du cache
            
        Returns:
            Statistiques de mémoire
        """
        current_time = time.time()
        
        # Utiliser le cache si disponible et récent
        if (not force_refresh and 
            self._cached_stats and 
            current_time - self._last_check < self._cache_duration):
            return self._cached_stats
        
        # Statistiques système
        memory = psutil.virtual_memory()
        process_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        stats = MemoryStats(
            total_ram_gb=memory.total / 1024**3,
            available_ram_gb=memory.available / 1024**3,
            used_ram_gb=memory.used / 1024**3,
            ram_percent=memory.percent,
            gpu_available=GPU_AVAILABLE,
            process_memory_mb=process_memory
        )
        
        # Statistiques GPU si disponible
        if GPU_AVAILABLE and torch:
            try:
                if torch.cuda.is_available():
                    device = torch.cuda.current_device()
                    gpu_memory = torch.cuda.get_device_properties(device).total_memory
                    gpu_allocated = torch.cuda.memory_allocated(device)
                    gpu_reserved = torch.cuda.memory_reserved(device)
                    
                    stats.gpu_memory_total_gb = gpu_memory / 1024**3
                    stats.gpu_memory_used_gb = gpu_allocated / 1024**3
                    stats.gpu_memory_free_gb = (gpu_memory - gpu_reserved) / 1024**3
                    
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    # Pour Apple Silicon, utiliser les stats système
                    # (PyTorch MPS ne fournit pas de stats détaillées)
                    stats.gpu_memory_total_gb = stats.total_ram_gb * 0.6  # Estimation
                    stats.gpu_memory_used_gb = 0.0  # Non disponible
                    stats.gpu_memory_free_gb = stats.gpu_memory_total_gb
            except Exception as e:
                logger.debug(f"Erreur stats GPU: {e}")
        
        # Mettre en cache
        self._cached_stats = stats
        self._last_check = current_time
        
        return stats
    
    def log_memory_stats(self, prefix: str = ""):
        """Affiche les statistiques de mémoire dans les logs"""
        stats = self.get_memory_stats()
        
        logger.info(f"{prefix}Mémoire système:")
        logger.info(f"  RAM: {stats.used_ram_gb:.1f}GB/{stats.total_ram_gb:.1f}GB ({stats.ram_percent:.1f}%)")
        logger.info(f"  Processus: {stats.process_memory_mb:.1f}MB")
        
        if stats.gpu_available:
            logger.info(f"  GPU: {stats.gpu_memory_used_gb:.1f}GB/{stats.gpu_memory_total_gb:.1f}GB")


class MemoryOptimizer:
    """
    Optimiseur de mémoire pour les modèles ML
    """
    
    def __init__(
        self,
        max_ram_percent: float = 80.0,
        max_gpu_percent: float = 90.0,
        cleanup_threshold_mb: float = 500.0,
        auto_cleanup: bool = True
    ):
        """
        Initialise l'optimiseur de mémoire
        
        Args:
            max_ram_percent: Pourcentage max de RAM avant nettoyage
            max_gpu_percent: Pourcentage max de GPU avant nettoyage
            cleanup_threshold_mb: Seuil de mémoire processus avant nettoyage (MB)
            auto_cleanup: Activer le nettoyage automatique
        """
        self.max_ram_percent = max_ram_percent
        self.max_gpu_percent = max_gpu_percent
        self.cleanup_threshold_mb = cleanup_threshold_mb
        self.auto_cleanup = auto_cleanup
        
        self.monitor = MemoryMonitor()
        
        # Registre des modèles chargés (weak references)
        self._loaded_models = weakref.WeakValueDictionary()
        self._cleanup_callbacks = {}
        
        # Thread de monitoring
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        
        if auto_cleanup:
            self.start_monitoring()
        
        logger.info(f"MemoryOptimizer initialisé - RAM: {max_ram_percent}%, GPU: {max_gpu_percent}%")
    
    def register_model(
        self, 
        model_id: str, 
        model_object: Any, 
        cleanup_callback: Optional[Callable] = None
    ):
        """
        Enregistre un modèle pour le monitoring de mémoire
        
        Args:
            model_id: Identifiant unique du modèle
            model_object: Objet modèle à monitorer
            cleanup_callback: Fonction de nettoyage personnalisée
        """
        self._loaded_models[model_id] = model_object
        if cleanup_callback:
            self._cleanup_callbacks[model_id] = cleanup_callback
        
        logger.debug(f"Modèle enregistré: {model_id}")
    
    def unregister_model(self, model_id: str):
        """Désenregistre un modèle"""
        if model_id in self._loaded_models:
            del self._loaded_models[model_id]
        if model_id in self._cleanup_callbacks:
            del self._cleanup_callbacks[model_id]
        
        logger.debug(f"Modèle désenregistré: {model_id}")
    
    def check_memory_pressure(self) -> Dict[str, bool]:
        """
        Vérifie si la mémoire est sous pression
        
        Returns:
            Dict avec les statuts de pression mémoire
        """
        stats = self.monitor.get_memory_stats()
        
        ram_pressure = stats.ram_percent > self.max_ram_percent
        gpu_pressure = False
        process_pressure = stats.process_memory_mb > self.cleanup_threshold_mb
        
        if stats.gpu_available and stats.gpu_memory_total_gb > 0:
            gpu_usage_percent = (stats.gpu_memory_used_gb / stats.gpu_memory_total_gb) * 100
            gpu_pressure = gpu_usage_percent > self.max_gpu_percent
        
        return {
            "ram_pressure": ram_pressure,
            "gpu_pressure": gpu_pressure,
            "process_pressure": process_pressure,
            "any_pressure": ram_pressure or gpu_pressure or process_pressure
        }
    
    def cleanup_memory(self, aggressive: bool = False) -> Dict[str, Any]:
        """
        Effectue un nettoyage de mémoire
        
        Args:
            aggressive: Nettoyage agressif (décharge tous les modèles)
            
        Returns:
            Statistiques du nettoyage
        """
        stats_before = self.monitor.get_memory_stats()
        cleanup_stats = {
            "models_unloaded": 0,
            "torch_cleanup": False,
            "gc_collections": 0,
            "memory_freed_mb": 0.0
        }
        
        logger.info(f"🧹 Nettoyage mémoire {'agressif' if aggressive else 'standard'}...")
        
        # 1. Nettoyage des modèles si agressif
        if aggressive:
            cleanup_stats["models_unloaded"] = self._unload_models()
        
        # 2. Nettoyage PyTorch si disponible
        if GPU_AVAILABLE and torch:
            cleanup_stats["torch_cleanup"] = self._cleanup_torch()
        
        # 3. Garbage collection Python
        cleanup_stats["gc_collections"] = self._force_gc()
        
        # 4. Calculer la mémoire libérée
        stats_after = self.monitor.get_memory_stats()
        cleanup_stats["memory_freed_mb"] = (
            stats_before.process_memory_mb - stats_after.process_memory_mb
        )
        
        logger.info(f"✅ Nettoyage terminé - Mémoire libérée: {cleanup_stats['memory_freed_mb']:.1f}MB")
        
        return cleanup_stats
    
    def _unload_models(self) -> int:
        """Décharge tous les modèles enregistrés"""
        unloaded = 0
        
        # Exécuter les callbacks de nettoyage
        for model_id, callback in list(self._cleanup_callbacks.items()):
            try:
                callback()
                unloaded += 1
                logger.debug(f"Modèle déchargé via callback: {model_id}")
            except Exception as e:
                logger.warning(f"Erreur callback cleanup {model_id}: {e}")
        
        # Vider les registres
        self._loaded_models.clear()
        self._cleanup_callbacks.clear()
        
        return unloaded
    
    def _cleanup_torch(self) -> bool:
        """Nettoyage spécifique PyTorch"""
        try:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.debug("Cache CUDA vidé")
            
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                # Pour Apple Silicon
                if hasattr(torch.mps, 'empty_cache'):
                    torch.mps.empty_cache()
                    logger.debug("Cache MPS vidé")
            
            return True
        except Exception as e:
            logger.warning(f"Erreur nettoyage PyTorch: {e}")
            return False
    
    def _force_gc(self) -> int:
        """Force le garbage collection Python"""
        collections = 0
        
        # Plusieurs passes de GC
        for i in range(3):
            collected = gc.collect()
            if collected > 0:
                collections += 1
                logger.debug(f"GC pass {i+1}: {collected} objets collectés")
            else:
                break
        
        return collections
    
    def start_monitoring(self, interval: float = 30.0):
        """
        Démarre le monitoring automatique de mémoire
        
        Args:
            interval: Intervalle de vérification en secondes
        """
        if self._monitoring_thread and self._monitoring_thread.is_alive():
            return
        
        def monitor_loop():
            while not self._stop_monitoring.wait(interval):
                try:
                    pressure = self.check_memory_pressure()
                    
                    if pressure["any_pressure"]:
                        logger.warning("⚠️ Pression mémoire détectée")
                        self.monitor.log_memory_stats("Avant nettoyage - ")
                        
                        # Nettoyage automatique
                        self.cleanup_memory(aggressive=pressure["process_pressure"])
                        
                        self.monitor.log_memory_stats("Après nettoyage - ")
                        
                except Exception as e:
                    logger.error(f"Erreur monitoring mémoire: {e}")
        
        self._monitoring_thread = threading.Thread(
            target=monitor_loop,
            name="MemoryMonitor",
            daemon=True
        )
        self._monitoring_thread.start()
        
        logger.info(f"🔍 Monitoring mémoire démarré (intervalle: {interval}s)")
    
    def stop_monitoring(self):
        """Arrête le monitoring automatique"""
        if self._monitoring_thread:
            self._stop_monitoring.set()
            self._monitoring_thread.join(timeout=5.0)
            self._monitoring_thread = None
            logger.info("🛑 Monitoring mémoire arrêté")
    
    def get_memory_report(self) -> Dict[str, Any]:
        """Génère un rapport complet de mémoire"""
        stats = self.monitor.get_memory_stats()
        pressure = self.check_memory_pressure()
        
        return {
            "timestamp": time.time(),
            "memory_stats": {
                "ram_total_gb": stats.total_ram_gb,
                "ram_used_gb": stats.used_ram_gb,
                "ram_available_gb": stats.available_ram_gb,
                "ram_percent": stats.ram_percent,
                "process_memory_mb": stats.process_memory_mb,
                "gpu_available": stats.gpu_available,
                "gpu_memory_total_gb": stats.gpu_memory_total_gb,
                "gpu_memory_used_gb": stats.gpu_memory_used_gb,
                "gpu_memory_free_gb": stats.gpu_memory_free_gb
            },
            "pressure_indicators": pressure,
            "loaded_models": list(self._loaded_models.keys()),
            "optimizer_config": {
                "max_ram_percent": self.max_ram_percent,
                "max_gpu_percent": self.max_gpu_percent,
                "cleanup_threshold_mb": self.cleanup_threshold_mb,
                "auto_cleanup": self.auto_cleanup
            }
        }
    
    def __del__(self):
        """Destructeur avec arrêt du monitoring"""
        try:
            self.stop_monitoring()
        except:
            pass


def memory_optimized(
    cleanup_after: bool = True,
    aggressive_cleanup: bool = False,
    model_id: Optional[str] = None
):
    """
    Décorateur pour optimiser automatiquement la mémoire des fonctions
    
    Args:
        cleanup_after: Nettoyer après l'exécution
        aggressive_cleanup: Nettoyage agressif
        model_id: ID du modèle à enregistrer/désenregistrer
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Obtenir l'optimiseur depuis les args si possible
            optimizer = None
            for arg in args:
                if hasattr(arg, '_memory_optimizer'):
                    optimizer = arg._memory_optimizer
                    break
            
            if not optimizer:
                optimizer = MemoryOptimizer()
            
            # Statistiques avant
            stats_before = optimizer.monitor.get_memory_stats()
            
            try:
                # Exécuter la fonction
                result = func(*args, **kwargs)
                
                # Enregistrer le modèle si spécifié
                if model_id and hasattr(result, '__dict__'):
                    optimizer.register_model(model_id, result)
                
                return result
                
            finally:
                # Nettoyage après exécution
                if cleanup_after:
                    pressure = optimizer.check_memory_pressure()
                    if pressure["any_pressure"] or aggressive_cleanup:
                        optimizer.cleanup_memory(aggressive=aggressive_cleanup)
                
                # Statistiques après
                stats_after = optimizer.monitor.get_memory_stats()
                memory_diff = stats_after.process_memory_mb - stats_before.process_memory_mb
                
                if memory_diff > 50:  # Log si augmentation significative
                    logger.info(f"💾 {func.__name__}: {memory_diff:+.1f}MB mémoire")
        
        return wrapper
    return decorator


# Instance globale d'optimiseur
_global_optimizer = None


def get_memory_optimizer() -> MemoryOptimizer:
    """Retourne l'instance globale d'optimiseur de mémoire"""
    global _global_optimizer
    if _global_optimizer is None:
        _global_optimizer = MemoryOptimizer()
    return _global_optimizer


def cleanup_memory(aggressive: bool = False) -> Dict[str, Any]:
    """Fonction utilitaire pour nettoyer la mémoire"""
    optimizer = get_memory_optimizer()
    return optimizer.cleanup_memory(aggressive)


def get_memory_stats() -> MemoryStats:
    """Fonction utilitaire pour obtenir les statistiques de mémoire"""
    optimizer = get_memory_optimizer()
    return optimizer.monitor.get_memory_stats()


def log_memory_usage(prefix: str = ""):
    """Fonction utilitaire pour logger l'usage mémoire"""
    optimizer = get_memory_optimizer()
    optimizer.monitor.log_memory_stats(prefix)


if __name__ == "__main__":
    # Test du module
    logging.basicConfig(level=logging.INFO)
    
    print("🧪 Test MemoryOptimizer")
    
    optimizer = MemoryOptimizer()
    
    # Afficher les stats initiales
    optimizer.monitor.log_memory_stats("Initiales - ")
    
    # Test de nettoyage
    cleanup_stats = optimizer.cleanup_memory()
    print(f"📊 Stats nettoyage: {cleanup_stats}")
    
    # Rapport complet
    report = optimizer.get_memory_report()
    print(f"📋 Rapport: {report['memory_stats']}")
    
    print("✅ Test terminé")