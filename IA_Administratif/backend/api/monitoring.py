"""
Endpoints de monitoring et performance pour LEXO v1
"""

from fastapi import APIRouter, Depends
from api.auth import get_current_user
from models.user import User
from utils.mistral_cache import get_mistral_cache
import logging
import psutil
import time
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/monitoring", tags=["Monitoring"])

# Stockage des métriques de performance en mémoire (simple)
_performance_metrics = {
    "start_time": time.time(),
    "request_count": 0,
    "ocr_operations": 0,
    "mistral_operations": 0,
    "classification_operations": 0,
    "errors": 0
}


@router.get("/performance")
async def get_performance_metrics(current_user: User = Depends(get_current_user)):
    """Retourne les métriques de performance du système"""
    
    uptime_seconds = time.time() - _performance_metrics["start_time"]
    uptime_hours = uptime_seconds / 3600
    
    # Statistiques système
    memory = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=1)
    
    # Statistiques Mistral cache
    mistral_cache = get_mistral_cache()
    cache_stats = mistral_cache.get_stats()
    
    return {
        "system": {
            "uptime_hours": round(uptime_hours, 2),
            "memory_usage_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "cpu_usage_percent": cpu_percent
        },
        "api": {
            "total_requests": _performance_metrics["request_count"],
            "ocr_operations": _performance_metrics["ocr_operations"],
            "mistral_operations": _performance_metrics["mistral_operations"],
            "classification_operations": _performance_metrics["classification_operations"],
            "error_count": _performance_metrics["errors"],
            "requests_per_hour": round(_performance_metrics["request_count"] / max(uptime_hours, 0.1), 1)
        },
        "mistral_cache": cache_stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health-detailed")
async def get_detailed_health():
    """Health check détaillé avec toutes les dépendances"""
    
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }
    
    # Test des services externes
    try:
        import httpx
        
        # Test Mistral service
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get("http://localhost:8004/health")
                mistral_healthy = response.status_code == 200
                mistral_data = response.json() if mistral_healthy else {}
                
                health_status["services"]["mistral"] = {
                    "status": "healthy" if mistral_healthy else "unhealthy",
                    "model_loaded": mistral_data.get("model_loaded", False),
                    "response_time_ms": response.elapsed.total_seconds() * 1000 if mistral_healthy else None
                }
            except Exception as e:
                health_status["services"]["mistral"] = {
                    "status": "error",
                    "error": str(e)
                }
        
        # Test Database (simple check)
        try:
            from core.database import AsyncSessionLocal
            from sqlalchemy import text
            
            async with AsyncSessionLocal() as db:
                result = await db.execute(text("SELECT 1"))
                db_healthy = result.scalar() == 1
                
            health_status["services"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy"
            }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "error", 
                "error": str(e)
            }
        
        # Test OCR modules
        try:
            from ocr.hybrid_ocr import HybridOCREngine
            ocr_engine = HybridOCREngine()
            
            health_status["services"]["ocr"] = {
                "status": "healthy",
                "engines_available": ["tesseract", "trocr", "hybrid"]
            }
        except Exception as e:
            health_status["services"]["ocr"] = {
                "status": "error",
                "error": str(e)
            }
        
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["error"] = str(e)
    
    # Déterminer le statut global
    service_statuses = [service.get("status") for service in health_status["services"].values()]
    if "error" in service_statuses:
        health_status["status"] = "degraded"
    elif "unhealthy" in service_statuses:
        health_status["status"] = "degraded"
    
    return health_status


@router.post("/cache/clear")
async def clear_mistral_cache(current_user: User = Depends(get_current_user)):
    """Vide le cache Mistral"""
    mistral_cache = get_mistral_cache()
    mistral_cache.clear()
    
    return {
        "success": True,
        "message": "Cache Mistral vidé avec succès"
    }


@router.get("/cache/stats")
async def get_cache_stats(current_user: User = Depends(get_current_user)):
    """Retourne les statistiques détaillées du cache"""
    mistral_cache = get_mistral_cache()
    stats = mistral_cache.get_stats()
    
    return {
        "mistral_cache": stats,
        "recommendations": _get_cache_recommendations(stats)
    }


def _get_cache_recommendations(stats: dict) -> list:
    """Génère des recommandations basées sur les stats de cache"""
    recommendations = []
    
    hit_rate = float(stats["cache_hit_potential"].rstrip('%'))
    
    if hit_rate < 30:
        recommendations.append("Cache hit rate faible - considérer augmenter TTL")
    elif hit_rate > 80:
        recommendations.append("Excellent taux de cache hit")
    
    if stats["expired_entries"] > stats["valid_entries"]:
        recommendations.append("Beaucoup d'entrées expirées - nettoyage recommandé")
    
    if stats["total_entries"] > 1000:
        recommendations.append("Cache volumineux - surveiller la mémoire")
    
    return recommendations


def increment_metric(metric_name: str):
    """Incrémente une métrique de performance"""
    if metric_name in _performance_metrics:
        _performance_metrics[metric_name] += 1


def record_error():
    """Enregistre une erreur"""
    _performance_metrics["errors"] += 1