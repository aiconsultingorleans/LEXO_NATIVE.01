"""
Cache intelligent pour les analyses Mistral
Évite les appels répétitifs à l'API MLX pour les mêmes contenus
"""

import hashlib
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MistralCache:
    """Cache en mémoire pour les analyses Mistral"""
    
    def __init__(self, ttl_seconds: int = 3600):
        """
        Args:
            ttl_seconds: Durée de vie du cache en secondes (par défaut 1h)
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_seconds = ttl_seconds
        
    def _get_cache_key(self, text: str, analysis_types: list) -> str:
        """Génère une clé de cache basée sur le contenu et le type d'analyse"""
        # Nettoyer et normaliser le texte
        clean_text = text.strip().lower()[:1000]  # Prendre les 1000 premiers caractères
        
        # Créer une signature unique
        content = f"{clean_text}:{','.join(sorted(analysis_types))}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, text: str, analysis_types: list) -> Optional[Dict[str, Any]]:
        """Récupère un résultat depuis le cache"""
        cache_key = self._get_cache_key(text, analysis_types)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            
            # Vérifier l'expiration
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                logger.info(f"🎯 Cache hit for Mistral analysis: {cache_key[:8]}...")
                return entry['data']
            else:
                # Supprimer l'entrée expirée
                del self.cache[cache_key]
                logger.info(f"⏰ Cache expired for: {cache_key[:8]}...")
        
        return None
    
    def set(self, text: str, analysis_types: list, data: Dict[str, Any]) -> None:
        """Stocke un résultat dans le cache"""
        cache_key = self._get_cache_key(text, analysis_types)
        
        self.cache[cache_key] = {
            'data': data,
            'timestamp': time.time()
        }
        
        logger.info(f"💾 Cached Mistral analysis: {cache_key[:8]}... (cache size: {len(self.cache)})")
        
        # Nettoyage périodique
        self._cleanup_expired()
    
    def _cleanup_expired(self) -> None:
        """Nettoie les entrées expirées du cache"""
        current_time = time.time()
        expired_keys = [
            key for key, entry in self.cache.items()
            if current_time - entry['timestamp'] >= self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            logger.info(f"🧹 Cleaned {len(expired_keys)} expired cache entries")
    
    def clear(self) -> None:
        """Vide complètement le cache"""
        self.cache.clear()
        logger.info("🗑️ Mistral cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques du cache"""
        current_time = time.time()
        
        # Compter les entrées valides vs expirées
        valid_entries = 0
        expired_entries = 0
        
        for entry in self.cache.values():
            if current_time - entry['timestamp'] < self.ttl_seconds:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            'total_entries': len(self.cache),
            'valid_entries': valid_entries,
            'expired_entries': expired_entries,
            'ttl_seconds': self.ttl_seconds,
            'cache_hit_potential': f"{(valid_entries / max(1, len(self.cache))) * 100:.1f}%"
        }


# Instance globale du cache
_mistral_cache: Optional[MistralCache] = None


def get_mistral_cache() -> MistralCache:
    """Récupère l'instance globale du cache Mistral"""
    global _mistral_cache
    
    if _mistral_cache is None:
        _mistral_cache = MistralCache(ttl_seconds=3600)  # 1 heure par défaut
        logger.info("🚀 Mistral cache initialized")
    
    return _mistral_cache


async def cached_mistral_analysis(
    text: str, 
    analysis_types: list,
    mistral_analysis_func
) -> Dict[str, Any]:
    """
    Wrapper pour les analyses Mistral avec cache intelligent
    
    Args:
        text: Texte à analyser
        analysis_types: Types d'analyse à effectuer
        mistral_analysis_func: Fonction d'analyse Mistral (async)
    
    Returns:
        Résultat de l'analyse (depuis le cache ou fraîchement calculé)
    """
    cache = get_mistral_cache()
    
    # Tentative de récupération depuis le cache
    cached_result = cache.get(text, analysis_types)
    if cached_result is not None:
        return cached_result
    
    # Pas en cache, appeler Mistral
    try:
        result = await mistral_analysis_func(text, analysis_types)
        
        # Stocker en cache si succès
        if result.get('success'):
            cache.set(text, analysis_types, result)
        
        return result
        
    except Exception as e:
        logger.error(f"Erreur analyse Mistral cachée: {e}")
        return {"success": False, "error": str(e)}