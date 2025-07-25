"""
Rate limiting middleware et utilitaires
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
import redis
import json
import logging

from .config import settings

logger = logging.getLogger(__name__)

# Client Redis pour le rate limiting
redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """Retourne le client Redis, en l'initialisant si nécessaire"""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True
        )
    return redis_client


class RateLimiter:
    """Gestionnaire de rate limiting basé sur Redis"""
    
    def __init__(
        self, 
        max_requests: int = 10, 
        window_seconds: int = 60,
        key_prefix: str = "rate_limit"
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.key_prefix = key_prefix
    
    async def _get_key(self, request: Request, identifier: Optional[str] = None) -> str:
        """Génère la clé Redis pour le rate limiting"""
        if identifier:
            return f"{self.key_prefix}:{identifier}"
        
        # Utiliser l'IP client comme identifiant par défaut
        client_ip = request.client.host if request.client else "unknown"
        return f"{self.key_prefix}:{client_ip}"
    
    async def check_rate_limit(
        self, 
        request: Request, 
        identifier: Optional[str] = None
    ) -> Dict[str, Any]:
        """Vérifie si la requête dépasse la limite"""
        redis_conn = get_redis_client()
        key = await self._get_key(request, identifier)
        
        try:
            # Incrémenter le compteur
            current_count = redis_conn.incr(key)
            
            # Définir l'expiration si c'est la première requête
            if current_count == 1:
                redis_conn.expire(key, self.window_seconds)
            
            # Obtenir le TTL pour calculer le reset time
            ttl = redis_conn.ttl(key)
            reset_time = datetime.now() + timedelta(seconds=ttl if ttl > 0 else self.window_seconds)
            
            # Informations de rate limit
            rate_limit_info = {
                "limit": self.max_requests,
                "remaining": max(0, self.max_requests - current_count),
                "reset": int(reset_time.timestamp()),
                "retry_after": ttl if current_count > self.max_requests else None
            }
            
            # Vérifier si la limite est dépassée
            if current_count > self.max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Try again in {ttl} seconds.",
                    headers={
                        "X-RateLimit-Limit": str(self.max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(rate_limit_info["reset"]),
                        "Retry-After": str(ttl)
                    }
                )
            
            return rate_limit_info
            
        except redis.RedisError as e:
            logger.error(f"Redis error in rate limiter: {e}")
            # En cas d'erreur Redis, permettre la requête mais logger
            return {
                "limit": self.max_requests,
                "remaining": self.max_requests,
                "reset": int((datetime.now() + timedelta(seconds=self.window_seconds)).timestamp())
            }
    
    def __call__(self, request: Request, response: Response):
        """Décorateur pour appliquer le rate limiting à un endpoint"""
        async def check_limit():
            rate_limit_info = await self.check_rate_limit(request)
            
            # Ajouter les headers de rate limit à la réponse
            response.headers["X-RateLimit-Limit"] = str(rate_limit_info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(rate_limit_info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(rate_limit_info["reset"])
            
        return check_limit


# Instances de rate limiters pour différents use cases
auth_rate_limiter = RateLimiter(
    max_requests=50,  # 50 tentatives (augmenté pour les tests)
    window_seconds=300,  # par 5 minutes
    key_prefix="auth"
)

api_rate_limiter = RateLimiter(
    max_requests=100,  # 100 requêtes
    window_seconds=60,  # par minute
    key_prefix="api"
)

upload_rate_limiter = RateLimiter(
    max_requests=10,  # 10 uploads
    window_seconds=300,  # par 5 minutes
    key_prefix="upload"
)