"""
Système de cache pour les résultats OCR
Cache intelligent avec gestion de l'expiration et persistance
"""

import logging
import json
import hashlib
import time
import pickle
from pathlib import Path
from typing import Optional, Dict, Any, Union, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import tempfile
import os

import redis
from PIL import Image
import numpy as np

# Import des modules OCR
from .tesseract_ocr import OCRResult

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entrée de cache OCR"""
    key: str
    result: OCRResult
    timestamp: float
    ttl: float  # Time to live en secondes
    metadata: Dict[str, Any]
    access_count: int = 0
    last_accessed: float = 0.0
    
    def is_expired(self) -> bool:
        """Vérifie si l'entrée est expirée"""
        return (time.time() - self.timestamp) > self.ttl
    
    def is_recently_accessed(self, threshold_hours: int = 24) -> bool:
        """Vérifie si l'entrée a été récemment accédée"""
        return (time.time() - self.last_accessed) < (threshold_hours * 3600)


class ImageHasher:
    """
    Générateur de hash pour images
    """
    
    @staticmethod
    def hash_image(image: Union[str, Path, np.ndarray, Image.Image]) -> str:
        """
        Génère un hash unique pour une image
        
        Args:
            image: Image à hasher
            
        Returns:
            Hash MD5 de l'image
        """
        try:
            # Gestion spéciale pour les fichiers
            if isinstance(image, (str, Path)):
                image_path = str(image)
                
                # Pour les PDFs, utiliser hash du fichier directement
                if image_path.lower().endswith('.pdf'):
                    with open(image_path, 'rb') as f:
                        file_content = f.read()
                        return hashlib.sha256(file_content).hexdigest()
                
                # Pour les autres fichiers, utiliser PIL
                pil_image = Image.open(image)
            elif isinstance(image, np.ndarray):
                pil_image = Image.fromarray(image)
            elif isinstance(image, Image.Image):
                pil_image = image
            else:
                raise ValueError(f"Type d'image non supporté: {type(image)}")
            
            # Convertir en bytes
            import io
            img_bytes = io.BytesIO()
            pil_image.save(img_bytes, format='PNG')
            img_bytes = img_bytes.getvalue()
            
            # Générer hash SHA256 (plus sûr que MD5)
            return hashlib.sha256(img_bytes).hexdigest()
            
        except Exception as e:
            logger.error(f"Erreur génération hash image: {e}")
            # Fallback: hash basé sur le timestamp
            return hashlib.md5(str(time.time()).encode()).hexdigest()
    
    @staticmethod
    def hash_ocr_params(params: Dict[str, Any]) -> str:
        """
        Génère un hash pour les paramètres OCR
        
        Args:
            params: Paramètres de configuration OCR
            
        Returns:
            Hash des paramètres
        """
        # Trier et sérialiser les paramètres
        sorted_params = json.dumps(params, sort_keys=True)
        return hashlib.md5(sorted_params.encode()).hexdigest()
    
    @staticmethod
    def generate_cache_key(
        image: Union[str, Path, np.ndarray, Image.Image],
        ocr_engine: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Génère une clé de cache unique
        
        Args:
            image: Image source
            ocr_engine: Nom du moteur OCR utilisé
            params: Paramètres OCR optionnels
            
        Returns:
            Clé de cache unique
        """
        image_hash = ImageHasher.hash_image(image)
        
        if params:
            params_hash = ImageHasher.hash_ocr_params(params)
            cache_key = f"ocr_{ocr_engine}_{image_hash}_{params_hash}"
        else:
            cache_key = f"ocr_{ocr_engine}_{image_hash}"
        
        return cache_key


class FileSystemCache:
    """
    Cache basé sur le système de fichiers
    """
    
    def __init__(self, cache_dir: str = None, max_size_mb: int = 500):
        """
        Initialise le cache fichier
        
        Args:
            cache_dir: Répertoire de cache (None = temp)
            max_size_mb: Taille maximale du cache en MB
        """
        if cache_dir is None:
            cache_dir = os.path.join(tempfile.gettempdir(), "lexo_ocr_cache")
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        
        # Fichier d'index pour les métadonnées
        self.index_file = self.cache_dir / "cache_index.json"
        self.index = self._load_index()
        
        logger.info(f"Cache fichier initialisé: {self.cache_dir} (max: {max_size_mb}MB)")
    
    def _load_index(self) -> Dict[str, Dict[str, Any]]:
        """Charge l'index du cache"""
        if self.index_file.exists():
            try:
                with open(self.index_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Erreur chargement index cache: {e}")
        return {}
    
    def _save_index(self):
        """Sauvegarde l'index du cache"""
        try:
            with open(self.index_file, 'w') as f:
                json.dump(self.index, f, indent=2)
        except Exception as e:
            logger.error(f"Erreur sauvegarde index cache: {e}")
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """
        Récupère une entrée du cache
        
        Args:
            key: Clé de cache
            
        Returns:
            Entrée de cache si trouvée et valide
        """
        if key not in self.index:
            return None
        
        cache_file = self.cache_dir / f"{key}.pkl"
        
        if not cache_file.exists():
            # Nettoyer l'index
            del self.index[key]
            self._save_index()
            return None
        
        try:
            with open(cache_file, 'rb') as f:
                entry = pickle.load(f)
            
            # Vérifier l'expiration
            if entry.is_expired():
                self.delete(key)
                return None
            
            # Mettre à jour les stats d'accès
            entry.access_count += 1
            entry.last_accessed = time.time()
            
            # Sauvegarder les stats mises à jour
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
            
            logger.debug(f"Cache hit: {key}")
            return entry
            
        except Exception as e:
            logger.error(f"Erreur lecture cache {key}: {e}")
            self.delete(key)
            return None
    
    def put(self, key: str, result: OCRResult, ttl: float = 86400, metadata: Optional[Dict[str, Any]] = None):
        """
        Stocke une entrée dans le cache
        
        Args:
            key: Clé de cache
            result: Résultat OCR à cacher
            ttl: Durée de vie en secondes (défaut: 24h)
            metadata: Métadonnées optionnelles
        """
        try:
            # Créer l'entrée de cache
            entry = CacheEntry(
                key=key,
                result=result,
                timestamp=time.time(),
                ttl=ttl,
                metadata=metadata or {},
                access_count=1,
                last_accessed=time.time()
            )
            
            # Sauvegarder l'entrée
            cache_file = self.cache_dir / f"{key}.pkl"
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
            
            # Mettre à jour l'index
            self.index[key] = {
                'timestamp': entry.timestamp,
                'ttl': entry.ttl,
                'size': cache_file.stat().st_size,
                'metadata': entry.metadata
            }
            
            # Vérifier la taille du cache
            self._cleanup_if_needed()
            
            self._save_index()
            logger.debug(f"Cache stored: {key}")
            
        except Exception as e:
            logger.error(f"Erreur écriture cache {key}: {e}")
    
    def delete(self, key: str):
        """Supprime une entrée du cache"""
        try:
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                cache_file.unlink()
            
            if key in self.index:
                del self.index[key]
                self._save_index()
            
            logger.debug(f"Cache deleted: {key}")
            
        except Exception as e:
            logger.error(f"Erreur suppression cache {key}: {e}")
    
    def clear(self):
        """Vide complètement le cache"""
        try:
            for cache_file in self.cache_dir.glob("*.pkl"):
                cache_file.unlink()
            
            self.index.clear()
            self._save_index()
            
            logger.info("Cache vidé complètement")
            
        except Exception as e:
            logger.error(f"Erreur vidage cache: {e}")
    
    def _cleanup_if_needed(self):
        """Nettoie le cache si nécessaire"""
        current_size = self._get_cache_size()
        
        if current_size > self.max_size_bytes:
            logger.info(f"Cache plein ({current_size/1024/1024:.1f}MB), nettoyage...")
            self._cleanup_old_entries()
    
    def _get_cache_size(self) -> int:
        """Calcule la taille actuelle du cache"""
        total_size = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            try:
                total_size += cache_file.stat().st_size
            except:
                continue
        return total_size
    
    def _cleanup_old_entries(self):
        """Nettoie les anciennes entrées"""
        # Trier par ancienneté (timestamp + dernière utilisation)
        entries_by_age = []
        
        for key, info in self.index.items():
            age_score = time.time() - info['timestamp']
            # Bonus pour les entrées récemment utilisées
            if 'last_accessed' in info:
                age_score -= (time.time() - info['last_accessed']) * 0.5
            
            entries_by_age.append((age_score, key))
        
        entries_by_age.sort(reverse=True)  # Plus ancien en premier
        
        # Supprimer les plus anciennes jusqu'à atteindre 80% de la taille max
        target_size = self.max_size_bytes * 0.8
        current_size = self._get_cache_size()
        
        for _, key in entries_by_age:
            if current_size <= target_size:
                break
            
            cache_file = self.cache_dir / f"{key}.pkl"
            if cache_file.exists():
                file_size = cache_file.stat().st_size
                self.delete(key)
                current_size -= file_size
        
        logger.info(f"Nettoyage terminé, taille: {current_size/1024/1024:.1f}MB")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        total_entries = len(self.index)
        total_size = self._get_cache_size()
        
        # Analyser les entrées
        expired_count = 0
        recent_access_count = 0
        
        for key, info in self.index.items():
            if (time.time() - info['timestamp']) > info['ttl']:
                expired_count += 1
            
            if info.get('last_accessed', 0) > (time.time() - 86400):
                recent_access_count += 1
        
        return {
            'total_entries': total_entries,
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'max_size_mb': round(self.max_size_bytes / 1024 / 1024, 2),
            'usage_percent': round((total_size / self.max_size_bytes) * 100, 1),
            'expired_entries': expired_count,
            'recent_access_count': recent_access_count,
            'cache_dir': str(self.cache_dir)
        }


class RedisCache:
    """
    Cache basé sur Redis
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", prefix: str = "lexo_ocr"):
        """
        Initialise le cache Redis
        
        Args:
            redis_url: URL de connexion Redis
            prefix: Préfixe pour les clés
        """
        self.prefix = prefix
        self.redis_client = None
        
        try:
            self.redis_client = redis.from_url(redis_url)
            # Test de connexion
            self.redis_client.ping()
            logger.info(f"Cache Redis initialisé: {redis_url}")
        except Exception as e:
            logger.warning(f"Redis non disponible: {e}")
            self.redis_client = None
    
    def _make_key(self, key: str) -> str:
        """Génère la clé Redis complète"""
        return f"{self.prefix}:{key}"
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """Récupère une entrée du cache Redis"""
        if not self.redis_client:
            return None
        
        try:
            redis_key = self._make_key(key)
            data = self.redis_client.get(redis_key)
            
            if data is None:
                return None
            
            entry = pickle.loads(data)
            
            # Mettre à jour les stats d'accès
            entry.access_count += 1
            entry.last_accessed = time.time()
            
            # Sauvegarder les stats mises à jour
            self.redis_client.set(redis_key, pickle.dumps(entry), ex=int(entry.ttl))
            
            logger.debug(f"Redis cache hit: {key}")
            return entry
            
        except Exception as e:
            logger.error(f"Erreur lecture Redis cache {key}: {e}")
            return None
    
    def put(self, key: str, result: OCRResult, ttl: float = 86400, metadata: Optional[Dict[str, Any]] = None):
        """Stocke une entrée dans Redis"""
        if not self.redis_client:
            return
        
        try:
            entry = CacheEntry(
                key=key,
                result=result,
                timestamp=time.time(),
                ttl=ttl,
                metadata=metadata or {},
                access_count=1,
                last_accessed=time.time()
            )
            
            redis_key = self._make_key(key)
            self.redis_client.set(redis_key, pickle.dumps(entry), ex=int(ttl))
            
            logger.debug(f"Redis cache stored: {key}")
            
        except Exception as e:
            logger.error(f"Erreur écriture Redis cache {key}: {e}")
    
    def delete(self, key: str):
        """Supprime une entrée de Redis"""
        if not self.redis_client:
            return
        
        try:
            redis_key = self._make_key(key)
            self.redis_client.delete(redis_key)
            logger.debug(f"Redis cache deleted: {key}")
        except Exception as e:
            logger.error(f"Erreur suppression Redis cache {key}: {e}")
    
    def clear(self):
        """Vide le cache Redis"""
        if not self.redis_client:
            return
        
        try:
            pattern = f"{self.prefix}:*"
            keys = self.redis_client.keys(pattern)
            if keys:
                self.redis_client.delete(*keys)
            logger.info("Cache Redis vidé")
        except Exception as e:
            logger.error(f"Erreur vidage Redis cache: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques Redis"""
        if not self.redis_client:
            return {"redis_available": False}
        
        try:
            info = self.redis_client.info()
            pattern = f"{self.prefix}:*"
            keys = self.redis_client.keys(pattern)
            
            return {
                "redis_available": True,
                "total_entries": len(keys),
                "memory_used_mb": round(info.get('used_memory', 0) / 1024 / 1024, 2),
                "connected_clients": info.get('connected_clients', 0),
                "prefix": self.prefix
            }
        except Exception as e:
            logger.error(f"Erreur stats Redis: {e}")
            return {"redis_available": False, "error": str(e)}


class HybridOCRCache:
    """
    Cache hybride combinant filesystem et Redis
    """
    
    def __init__(
        self,
        use_redis: bool = True,
        redis_url: str = "redis://localhost:6379",
        cache_dir: str = None,
        max_size_mb: int = 500
    ):
        """
        Initialise le cache hybride
        
        Args:
            use_redis: Utiliser Redis comme cache L1
            redis_url: URL Redis
            cache_dir: Répertoire cache fichier
            max_size_mb: Taille max cache fichier
        """
        # Cache L1: Redis (rapide, volatile)
        self.redis_cache = RedisCache(redis_url) if use_redis else None
        
        # Cache L2: Filesystem (persistant, plus lent)
        self.fs_cache = FileSystemCache(cache_dir, max_size_mb)
        
        self.stats = {
            'redis_hits': 0,
            'fs_hits': 0,
            'misses': 0,
            'stores': 0
        }
        
        logger.info("Cache hybride OCR initialisé")
    
    def get(self, key: str) -> Optional[CacheEntry]:
        """
        Récupère une entrée (Redis -> Filesystem)
        
        Args:
            key: Clé de cache
            
        Returns:
            Entrée de cache si trouvée
        """
        # Essayer Redis en premier
        if self.redis_cache:
            entry = self.redis_cache.get(key)
            if entry:
                self.stats['redis_hits'] += 1
                return entry
        
        # Fallback vers filesystem
        entry = self.fs_cache.get(key)
        if entry:
            self.stats['fs_hits'] += 1
            
            # Repopuler Redis si disponible
            if self.redis_cache:
                self.redis_cache.put(key, entry.result, entry.ttl, entry.metadata)
            
            return entry
        
        self.stats['misses'] += 1
        return None
    
    def put(
        self,
        key: str,
        result: OCRResult,
        ttl: float = 86400,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Stocke une entrée dans les deux caches
        
        Args:
            key: Clé de cache
            result: Résultat OCR
            ttl: Durée de vie
            metadata: Métadonnées
        """
        # Stocker dans les deux caches
        if self.redis_cache:
            self.redis_cache.put(key, result, ttl, metadata)
        
        self.fs_cache.put(key, result, ttl, metadata)
        
        self.stats['stores'] += 1
    
    def delete(self, key: str):
        """Supprime une entrée des deux caches"""
        if self.redis_cache:
            self.redis_cache.delete(key)
        
        self.fs_cache.delete(key)
    
    def clear(self):
        """Vide tous les caches"""
        if self.redis_cache:
            self.redis_cache.clear()
        
        self.fs_cache.clear()
        
        # Reset stats
        for key in self.stats:
            self.stats[key] = 0
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques complètes"""
        stats = {
            'hybrid_stats': self.stats.copy(),
            'filesystem_cache': self.fs_cache.get_stats()
        }
        
        if self.redis_cache:
            stats['redis_cache'] = self.redis_cache.get_stats()
        
        # Calculer des métriques dérivées
        total_requests = sum([self.stats['redis_hits'], self.stats['fs_hits'], self.stats['misses']])
        if total_requests > 0:
            stats['hybrid_stats']['hit_rate'] = round(
                (self.stats['redis_hits'] + self.stats['fs_hits']) / total_requests * 100, 1
            )
            stats['hybrid_stats']['redis_hit_rate'] = round(
                self.stats['redis_hits'] / total_requests * 100, 1
            )
        
        return stats


# Interface principale du cache OCR

class OCRCacheManager:
    """
    Gestionnaire principal du cache OCR
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le gestionnaire de cache
        
        Args:
            config: Configuration du cache
        """
        if config is None:
            config = {
                'type': 'hybrid',  # filesystem, redis, hybrid
                'redis_url': 'redis://localhost:6379',
                'cache_dir': None,
                'max_size_mb': 500,
                'default_ttl': 86400  # 24h
            }
        
        self.config = config
        self.default_ttl = config.get('default_ttl', 86400)
        
        # Initialiser le cache selon le type
        cache_type = config.get('type', 'hybrid')
        
        if cache_type == 'filesystem':
            self.cache = FileSystemCache(
                config.get('cache_dir'),
                config.get('max_size_mb', 500)
            )
        elif cache_type == 'redis':
            self.cache = RedisCache(config.get('redis_url', 'redis://localhost:6379'))
        elif cache_type == 'hybrid':
            self.cache = HybridOCRCache(
                use_redis=True,
                redis_url=config.get('redis_url', 'redis://localhost:6379'),
                cache_dir=config.get('cache_dir'),
                max_size_mb=config.get('max_size_mb', 500)
            )
        else:
            raise ValueError(f"Type de cache non supporté: {cache_type}")
        
        logger.info(f"OCRCacheManager initialisé (type: {cache_type})")
    
    def get_cached_result(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        ocr_engine: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[OCRResult]:
        """
        Récupère un résultat OCR depuis le cache
        
        Args:
            image: Image source
            ocr_engine: Nom du moteur OCR
            params: Paramètres OCR
            
        Returns:
            Résultat OCR si trouvé dans le cache
        """
        cache_key = ImageHasher.generate_cache_key(image, ocr_engine, params)
        
        entry = self.cache.get(cache_key)
        return entry.result if entry else None
    
    def cache_result(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        ocr_engine: str,
        result: OCRResult,
        params: Optional[Dict[str, Any]] = None,
        ttl: Optional[float] = None
    ):
        """
        Met en cache un résultat OCR
        
        Args:
            image: Image source
            ocr_engine: Nom du moteur OCR
            result: Résultat OCR à cacher
            params: Paramètres OCR
            ttl: Durée de vie personnalisée
        """
        cache_key = ImageHasher.generate_cache_key(image, ocr_engine, params)
        
        metadata = {
            'ocr_engine': ocr_engine,
            'params': params or {},
            'word_count': result.word_count,
            'confidence': result.confidence,
            'processing_time': result.processing_time
        }
        
        effective_ttl = ttl or self.default_ttl
        self.cache.put(cache_key, result, effective_ttl, metadata)
    
    def invalidate_cache(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        ocr_engine: str,
        params: Optional[Dict[str, Any]] = None
    ):
        """Invalide une entrée de cache spécifique"""
        cache_key = ImageHasher.generate_cache_key(image, ocr_engine, params)
        self.cache.delete(cache_key)
    
    def clear_all_cache(self):
        """Vide complètement le cache"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        if hasattr(self.cache, 'get_comprehensive_stats'):
            return self.cache.get_comprehensive_stats()
        else:
            return self.cache.get_stats()


# Fonctions utilitaires

def create_ocr_cache(cache_type: str = "hybrid", **kwargs) -> OCRCacheManager:
    """
    Crée un gestionnaire de cache OCR
    
    Args:
        cache_type: Type de cache (filesystem, redis, hybrid)
        **kwargs: Arguments de configuration
        
    Returns:
        Gestionnaire de cache configuré
    """
    config = {'type': cache_type, **kwargs}
    return OCRCacheManager(config)


def cached_ocr_decorator(cache_manager: OCRCacheManager):
    """
    Décorateur pour ajouter automatiquement le cache aux fonctions OCR
    
    Args:
        cache_manager: Gestionnaire de cache à utiliser
        
    Returns:
        Décorateur
    """
    def decorator(ocr_function):
        def wrapper(image, engine_name="default", **kwargs):
            # Vérifier le cache
            cached_result = cache_manager.get_cached_result(image, engine_name, kwargs)
            if cached_result:
                logger.debug(f"Cache hit pour {engine_name}")
                return cached_result
            
            # Exécuter la fonction OCR
            result = ocr_function(image, **kwargs)
            
            # Mettre en cache le résultat
            cache_manager.cache_result(image, engine_name, result, kwargs)
            
            return result
        
        return wrapper
    return decorator