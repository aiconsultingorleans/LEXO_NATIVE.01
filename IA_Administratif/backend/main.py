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
from core.config import settings
from core.database import init_db

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cycle de vie de l'application"""
    # Startup
    logger.info("🚀 Démarrage de LEXO v1 Backend")
    await init_db()
    logger.info("✅ Base de données initialisée")
    
    yield
    
    # Shutdown
    logger.info("🛑 Arrêt de LEXO v1 Backend")


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
    """Middleware de logging des requêtes"""
    start_time = time.time()
    
    response = await call_next(request)
    
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
app.include_router(ocr_router, tags=["OCR"])


@app.get("/")
async def root():
    """Endpoint racine"""
    return {
        "message": "LEXO v1 API",
        "version": "1.0.0",
        "status": "🚀 Opérationnel"
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )