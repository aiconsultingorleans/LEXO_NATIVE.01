"""
LEXO v1 - FastAPI Backend
Assistant IA pour la gestion administrative intelligente
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import time
from contextlib import asynccontextmanager

from api.auth import router as auth_router
from api.documents import router as documents_router
from api.health import router as health_router
from api.ocr_routes_simple import router as ocr_router
from api.document_intelligence import router as intelligence_router
from api.batch_processing import router as batch_router
from api.rag_clear import router as rag_clear_router
from api.classification import router as classification_router
from api.monitoring import router as monitoring_router
# from api.rag_routes import router as rag_router  # Temporairement désactivé
from core.config import settings
from core.database import init_db
from services.ocr_watcher import start_ocr_watcher, stop_ocr_watcher, get_watcher_status

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cycle de vie de l'application avec démarrage rapide"""
    # Startup rapide
    logger.info("🚀 Démarrage rapide de LEXO v1 Backend")
    await init_db()
    logger.info("✅ Base de données initialisée")
    
    # L'API est maintenant prête - OCR se chargera à la demande
    logger.info("✅ API prête - OCR se chargera lors du premier usage")
    
    # Démarrer le service de surveillance OCR en arrière-plan (optionnel)
    try:
        # Note: Le watcher initialisera l'OCR lors du premier fichier détecté
        watcher = start_ocr_watcher("/app/ocr_data")
        logger.info("✅ Service de surveillance OCR démarré (lazy loading)")
    except Exception as e:
        logger.error(f"❌ Échec démarrage surveillance OCR: {e}")
    
    yield
    
    # Shutdown
    logger.info("🛑 Arrêt de LEXO v1 Backend")
    
    # Arrêter le service de surveillance OCR
    try:
        stop_ocr_watcher()
        logger.info("✅ Service de surveillance OCR arrêté")
    except Exception as e:
        logger.error(f"❌ Erreur arrêt surveillance OCR: {e}")


# Création de l'app FastAPI
app = FastAPI(
    title="LEXO v1 API",
    description="Assistant IA pour la gestion administrative intelligente",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware de logging des requêtes avec métriques"""
    start_time = time.time()
    
    # Compter les requêtes
    from api.monitoring import increment_metric, record_error
    increment_metric("request_count")
    
    # Compter les opérations spécifiques
    if "/ocr/" in request.url.path:
        increment_metric("ocr_operations")
    elif "/intelligence/" in request.url.path:
        increment_metric("mistral_operations") 
    elif "/classification/" in request.url.path:
        increment_metric("classification_operations")
    
    response = await call_next(request)
    
    # Compter les erreurs
    if response.status_code >= 400:
        record_error()
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s"
    )
    
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Gestionnaire global des exceptions"""
    logger.error(f"Erreur non gérée: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Erreur interne du serveur",
            "message": str(exc) if settings.DEBUG else "Une erreur s'est produite"
        }
    )


# Routes principales
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])
app.include_router(classification_router, prefix="/api/v1/classification", tags=["Classification"])
app.include_router(ocr_router, tags=["OCR"])
app.include_router(intelligence_router, tags=["Intelligence"])
app.include_router(batch_router, tags=["Batch Processing"])
app.include_router(rag_clear_router, prefix="/api/v1/rag", tags=["RAG"])
app.include_router(monitoring_router, tags=["Monitoring"])
# app.include_router(rag_router, tags=["RAG"])  # Temporairement désactivé


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "message": "LEXO v1 API",
        "version": "1.0.0",
        "status": "🚀 Opérationnel"
    }


@app.get("/api/v1/watcher/status")
async def watcher_status():
    """Statut du service de surveillance OCR"""
    return get_watcher_status()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )