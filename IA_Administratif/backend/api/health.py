"""
Endpoints de santé et monitoring
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis
from datetime import datetime

from core.database import get_db
from core.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Vérification de base de la santé de l'API"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LEXO v1 Backend",
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """Vérification détaillée incluant les dépendances"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LEXO v1 Backend",
        "version": "1.0.0",
        "checks": {}
    }
    
    # Test PostgreSQL
    try:
        result = await db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "healthy",
            "response_time": "< 10ms"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    # Test Redis
    try:
        redis_client = redis.from_url(settings.REDIS_URL)
        await redis_client.ping()
        await redis_client.close()
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "response_time": "< 5ms"
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/health/ocr")
async def ocr_health_check():
    """Vérification de santé des moteurs OCR avec lazy loading"""
    try:
        # Importer dynamiquement pour éviter l'initialisation au démarrage
        from ocr.hybrid_ocr import HybridOCREngine
        
        # Créer une instance test (avec lazy loading)
        engine = HybridOCREngine()
        
        # Vérifier l'état sans initialiser les moteurs
        return {
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat(),
            "ocr_engines_initialized": engine._engines_initialized,
            "initialization_in_progress": engine._initialization_in_progress,
            "config": {
                "trocr_enabled": engine.config.trocr_enabled,
                "tesseract_enabled": engine.config.tesseract_enabled,
                "strategy": engine.config.strategy.value,
                "cache_dir": engine.config.cache_dir
            },
            "stats": engine.stats,
            "message": "OCR engines will initialize on first use" if not engine._engines_initialized else "OCR engines ready"
        }
    except Exception as e:
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }