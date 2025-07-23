"""
API endpoints pour l'intelligence documentaire avec Mistral MLX
Intégration du service d'analyse documentaire natif dans le backend Docker
"""

import logging
import httpx
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel

from core.config import get_settings
from api.auth import get_current_user
from models.user import User

logger = logging.getLogger(__name__)

# Configuration du service MLX natif
DOCUMENT_ANALYZER_URL = "http://127.0.0.1:8004"
DOCUMENT_ANALYZER_TIMEOUT = 30.0

router = APIRouter(prefix="/api/v1/intelligence", tags=["Document Intelligence"])


class DocumentAnalysisRequest(BaseModel):
    """Requête d'analyse de document"""
    text: str
    analysis_types: List[str] = ["classification", "key_extraction"]
    document_context: Optional[str] = None


class DocumentAnalysisResponse(BaseModel):
    """Réponse d'analyse de document"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class DocumentIntelligenceService:
    """
    Service proxy pour communiquer avec le Document Analyzer MLX natif
    """
    
    def __init__(self):
        self.base_url = DOCUMENT_ANALYZER_URL
        self.timeout = DOCUMENT_ANALYZER_TIMEOUT
        self.logger = logging.getLogger("document_intelligence")
    
    async def check_service_health(self) -> bool:
        """Vérifie si le service MLX natif est disponible"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200 and response.json().get("status") == "healthy"
        except Exception as e:
            self.logger.warning(f"Service MLX non disponible : {e}")
            return False
    
    async def analyze_document(
        self, 
        text: str, 
        analysis_types: List[str] = None,
        document_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyse un document via le service MLX natif
        
        Args:
            text: Texte du document à analyser
            analysis_types: Types d'analyse à effectuer
            document_context: Contexte additionnel
            
        Returns:
            Résultat d'analyse structuré
        """
        if analysis_types is None:
            analysis_types = ["classification", "key_extraction"]
        
        try:
            # Vérifier que le service est disponible
            if not await self.check_service_health():
                raise HTTPException(
                    status_code=503, 
                    detail="Service d'analyse documentaire MLX non disponible"
                )
            
            # Préparer la requête
            request_data = {
                "text": text,
                "analysis_types": analysis_types,
                "document_context": document_context
            }
            
            # Appel au service MLX natif
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/analyze",
                    json=request_data
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Erreur service MLX : {response.text}"
                    )
                
                return response.json()
                
        except httpx.TimeoutException:
            self.logger.error("Timeout lors de l'analyse documentaire")
            raise HTTPException(status_code=504, detail="Timeout analyse documentaire")
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Erreur communication service MLX : {e}")
            raise HTTPException(status_code=500, detail=f"Erreur analyse : {str(e)}")
    
    async def get_supported_types(self) -> Dict[str, List[str]]:
        """Récupère les types supportés par le service MLX"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Types de documents
                doc_types_response = await client.get(f"{self.base_url}/document-types")
                doc_types = doc_types_response.json().get("document_types", [])
                
                # Types d'analyse
                analysis_types_response = await client.get(f"{self.base_url}/analysis-types")
                analysis_types = analysis_types_response.json().get("analysis_types", [])
                
                return {
                    "document_types": doc_types,
                    "analysis_types": analysis_types
                }
                
        except Exception as e:
            self.logger.error(f"Erreur récupération types supportés : {e}")
            return {"document_types": [], "analysis_types": []}


# Instance du service
intelligence_service = DocumentIntelligenceService()


@router.get("/health")
async def health_check():
    """Vérifie l'état du service d'intelligence documentaire"""
    service_available = await intelligence_service.check_service_health()
    
    return {
        "status": "healthy" if service_available else "degraded",
        "mlx_service_available": service_available,
        "service_url": DOCUMENT_ANALYZER_URL
    }


@router.post("/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(
    request: DocumentAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyse un document avec Mistral MLX
    
    Analyse sémantique avancée incluant :
    - Classification automatique du type de document
    - Extraction d'informations clés
    - Résumé intelligent
    - Analyse de conformité
    """
    try:
        result = await intelligence_service.analyze_document(
            text=request.text,
            analysis_types=request.analysis_types,
            document_context=request.document_context
        )
        
        return DocumentAnalysisResponse(
            success=True,
            result=result.get("result")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur endpoint analyze : {e}")
        return DocumentAnalysisResponse(
            success=False,
            error=str(e)
        )


@router.post("/analyze-file")
async def analyze_uploaded_file(
    file: UploadFile = File(...),
    analysis_types: str = "classification,key_extraction",
    current_user: User = Depends(get_current_user)
):
    """
    Analyse un fichier uploadé en combinant OCR + Intelligence documentaire
    
    Pipeline complet :
    1. OCR sur le fichier uploadé
    2. Analyse sémantique avec Mistral MLX
    3. Retour des résultats combinés
    """
    try:
        # TODO: Intégrer avec le pipeline OCR existant
        # 1. Extraire le texte via OCR (backend/ocr/)
        # 2. Passer le texte à l'analyse MLX
        # 3. Combiner les résultats
        
        return {
            "success": False,
            "error": "Analyse de fichier pas encore implémentée - nécessite intégration OCR"
        }
        
    except Exception as e:
        logger.error(f"Erreur analyse fichier : {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/supported-types")
async def get_supported_types():
    """Retourne les types de documents et d'analyses supportés"""
    return await intelligence_service.get_supported_types()


@router.get("/config")
async def get_intelligence_config():
    """Configuration du service d'intelligence documentaire"""
    service_health = await intelligence_service.check_service_health()
    
    return {
        "service_url": DOCUMENT_ANALYZER_URL,
        "timeout": DOCUMENT_ANALYZER_TIMEOUT,
        "service_available": service_health,
        "integration_status": "active" if service_health else "degraded"
    }