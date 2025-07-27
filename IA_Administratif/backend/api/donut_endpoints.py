"""
Endpoints API pour pipeline DONUT alternatif
Étape 5.1 - Intégration backend non-destructive

Architecture: Proxy vers service DONUT port 8005
Approche: 100% non-destructive, coexistence avec pipeline Mistral existant
"""

import httpx
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File, status, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from api.auth import get_current_user
from models.user import User

# Configuration
DONUT_SERVICE_URL = "http://localhost:8005"
DONUT_TIMEOUT = 30.0

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["DONUT Pipeline"])

# État global du pipeline (Mistral par défaut)
current_pipeline = {"active": "mistral", "last_switch": datetime.now()}

# Schemas
class DonutAnalysisResponse(BaseModel):
    """Réponse d'analyse DONUT compatible avec format existant"""
    success: bool
    document_id: Optional[str] = None
    filename: str
    category: str
    confidence_score: float
    ocr_text: Optional[str] = None
    entities: list = []
    folder_path: Optional[str] = None
    processing_time: float
    pipeline_used: str = "donut"

class PipelineSwitchRequest(BaseModel):
    """Requête de basculement pipeline"""
    pipeline: str = Field(..., pattern="^(mistral|donut)$")

class PipelineStatusResponse(BaseModel):
    """État actuel du pipeline"""
    active_pipeline: str
    available_pipelines: list
    last_switch: datetime
    donut_service_status: str
    mistral_service_status: str

# Helper functions
async def check_donut_service() -> bool:
    """Vérifier disponibilité service DONUT"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{DONUT_SERVICE_URL}/health")
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Service DONUT inaccessible: {e}")
        return False

async def proxy_to_donut(endpoint: str, method: str = "GET", **kwargs) -> Dict[str, Any]:
    """Proxy générique vers service DONUT"""
    try:
        async with httpx.AsyncClient(timeout=DONUT_TIMEOUT) as client:
            url = f"{DONUT_SERVICE_URL}/{endpoint.lstrip('/')}"
            
            if method.upper() == "POST":
                response = await client.post(url, **kwargs)
            elif method.upper() == "GET":
                response = await client.get(url, **kwargs)
            else:
                raise HTTPException(status_code=400, detail=f"Méthode {method} non supportée")
            
            response.raise_for_status()
            return response.json()
            
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504, 
            detail="Timeout service DONUT - Basculement automatique vers Mistral recommandé"
        )
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Erreur service DONUT: {e.response.text}"
        )
    except Exception as e:
        logger.error(f"Erreur proxy DONUT: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur interne service DONUT"
        )

@router.post("/documents/analyze-donut", response_model=DonutAnalysisResponse)
async def analyze_document_with_donut(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Analyser un document avec pipeline DONUT alternatif
    
    - **file**: Document à analyser (PDF, PNG, JPG, TIFF)
    - **return**: Analyse complète avec classification dynamique + organisation
    
    Note: Alternative au pipeline Mistral MLX existant
    """
    start_time = datetime.now()
    
    # Vérification préalable service DONUT
    if not await check_donut_service():
        raise HTTPException(
            status_code=503,
            detail="Service DONUT indisponible - Utilisez le pipeline Mistral"
        )
    
    try:
        # Validation format fichier
        allowed_types = ["application/pdf", "image/png", "image/jpeg", "image/tiff"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Format non supporté: {file.content_type}. Formats acceptés: PDF, PNG, JPG, TIFF"
            )
        
        # Préparation fichier pour DONUT
        file_content = await file.read()
        files = {"file": (file.filename, file_content, file.content_type)}
        
        # Proxy vers service DONUT analyse complète
        donut_response = await proxy_to_donut(
            "analyze/complete",
            method="POST",
            files=files,
            data={"user_id": str(current_user.id)}
        )
        
        # Calcul temps traitement
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Format réponse compatible API existante
        return DonutAnalysisResponse(
            success=donut_response.get("success", True),
            document_id=donut_response.get("document_id"),
            filename=file.filename,
            category=donut_response.get("category", "non_classes"),
            confidence_score=donut_response.get("confidence_score", 0.0),
            ocr_text=donut_response.get("extracted_text"),
            entities=donut_response.get("entities", []),
            folder_path=donut_response.get("organization_path"),
            processing_time=processing_time,
            pipeline_used="donut"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse DONUT pour {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur traitement document: {str(e)}"
        )

@router.post("/models/switch", response_model=PipelineStatusResponse)
async def switch_pipeline(
    request: PipelineSwitchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Basculer entre pipelines Mistral et DONUT
    
    - **pipeline**: "mistral" ou "donut"
    - **return**: État nouveau pipeline actif
    
    Note: Basculement instantané sans redémarrage services
    """
    global current_pipeline
    
    # Validation pipeline demandé
    if request.pipeline not in ["mistral", "donut"]:
        raise HTTPException(
            status_code=400,
            detail="Pipeline non valide. Choix: 'mistral' ou 'donut'"
        )
    
    # Vérification disponibilité si DONUT demandé
    if request.pipeline == "donut":
        if not await check_donut_service():
            raise HTTPException(
                status_code=503,
                detail="Pipeline DONUT indisponible - Conservation pipeline Mistral"
            )
    
    # Basculement pipeline
    previous_pipeline = current_pipeline["active"]
    current_pipeline = {
        "active": request.pipeline,
        "last_switch": datetime.now()
    }
    
    logger.info(f"Basculement pipeline: {previous_pipeline} → {request.pipeline} (utilisateur: {current_user.email})")
    
    # État services pour réponse
    donut_status = "available" if await check_donut_service() else "unavailable"
    mistral_status = "available"  # Mistral toujours disponible (service principal)
    
    return PipelineStatusResponse(
        active_pipeline=current_pipeline["active"],
        available_pipelines=["mistral", "donut"],
        last_switch=current_pipeline["last_switch"],
        donut_service_status=donut_status,
        mistral_service_status=mistral_status
    )

@router.get("/models/status", response_model=PipelineStatusResponse)
async def get_pipeline_status():
    """
    Obtenir l'état actuel des pipelines
    
    - **return**: Pipeline actif + disponibilité services
    """
    # Vérification état services
    donut_status = "available" if await check_donut_service() else "unavailable"
    mistral_status = "available"  # Mistral toujours disponible
    
    return PipelineStatusResponse(
        active_pipeline=current_pipeline["active"],
        available_pipelines=["mistral", "donut"],
        last_switch=current_pipeline["last_switch"],
        donut_service_status=donut_status,
        mistral_service_status=mistral_status
    )

@router.get("/folders/structure")
async def get_donut_folder_structure(
    current_user: User = Depends(get_current_user)
):
    """
    Obtenir l'arborescence intelligente créée par DONUT
    
    - **return**: Structure hiérarchique JSON des dossiers auto-créés
    
    Note: Fonction spécifique au pipeline DONUT (organisation dynamique)
    """
    if not await check_donut_service():
        raise HTTPException(
            status_code=503,
            detail="Service DONUT requis pour visualisation arborescence"
        )
    
    try:
        # Proxy vers service DONUT pour structure
        structure = await proxy_to_donut("organization/structure", method="GET")
        
        # Retourner directement la structure DONUT sans wrapper
        return JSONResponse(content=structure)
        
    except Exception as e:
        logger.error(f"Erreur récupération structure DONUT: {e}")
        raise HTTPException(
            status_code=500,
            detail="Erreur récupération arborescence DONUT"
        )

@router.get("/donut/health")
async def donut_health_check():
    """
    Health check spécifique service DONUT
    
    - **return**: État détaillé service + modèles DONUT
    """
    try:
        health_data = await proxy_to_donut("health", method="GET")
        
        return JSONResponse(content={
            "donut_service": "available",
            "backend_proxy": "operational",
            **health_data
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={
                "donut_service": "unavailable",
                "backend_proxy": "operational",
                "error": str(e),
                "fallback": "mistral_pipeline_available"
            }
        )