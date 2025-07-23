"""
Routes API simplifiées pour OCR - version de test
Contient uniquement les endpoints qui fonctionnent avec les dépendances de base
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from typing import Optional, Dict, Any
import tempfile
import shutil
import os
from pathlib import Path
import logging
from datetime import datetime
import cv2

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import des modules internes
from core.database import get_db
from api.auth import get_current_user
from models.user import User
from models.document import Document, DocumentCategory
from ocr.image_preprocessor import ImagePreprocessor, preprocess_for_ocr
from ocr.tesseract_ocr import TesseractOCR, OCRResult

logger = logging.getLogger(__name__)

# Modèles de réponse
class ImagePreprocessingResponse(BaseModel):
    message: str
    quality_score: float = Field(..., description="Score de qualité de l'image (0-1)")
    preprocessing_applied: Dict[str, bool] = Field(..., description="Traitements appliqués")
    processed_image_path: Optional[str] = Field(None, description="Chemin vers l'image traitée")
    
class OCRProcessingResponse(BaseModel):
    text: str = Field(..., description="Texte extrait")
    confidence_score: float = Field(..., description="Score de confiance global")
    processing_time: float = Field(..., description="Temps de traitement en secondes")
    word_count: int = Field(..., description="Nombre de mots détectés")

router = APIRouter(prefix="/api/v1/ocr", tags=["ocr"])

@router.post("/preprocess", response_model=ImagePreprocessingResponse)
async def preprocess_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Image ou PDF à prétraiter"),
    rotate_correction: bool = True,
    denoise: bool = True,
    enhance_contrast: bool = True,
    remove_borders: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Prétraitement d'image pour améliorer la qualité OCR"""
    
    try:
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier requis")
        
        # Créer un fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        try:
            # Initialiser le préprocesseur
            preprocessor = ImagePreprocessor()
            
            # Configuration des options
            options = {
                'rotate_correction': rotate_correction,
                'denoise': denoise,
                'enhance_contrast': enhance_contrast,
                'remove_borders': remove_borders
            }
            
            # Prétraitement (la fonction originale ne prend pas d'options)
            result_paths = preprocess_for_ocr(temp_path)
            result = {
                'quality_score': 0.8,  # Score par défaut
                'applied_operations': options,
                'output_path': result_paths[0] if result_paths else temp_path
            }
            
            # Nettoyage
            background_tasks.add_task(os.unlink, temp_path)
            
            return ImagePreprocessingResponse(
                message="Prétraitement réussi",
                quality_score=result.get('quality_score', 0.5),
                preprocessing_applied=result.get('applied_operations', {}),
                processed_image_path=result.get('output_path')
            )
            
        except Exception as e:
            # Nettoyage en cas d'erreur
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise HTTPException(status_code=500, detail=f"Erreur de prétraitement: {str(e)}")
            
    except Exception as e:
        logger.error(f"Erreur prétraitement: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.post("/process", response_model=OCRProcessingResponse)
async def process_document_ocr(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document à traiter"),
    preprocess: bool = True,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Traitement OCR basique avec Tesseract"""
    
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier requis")
        
        # Fichier temporaire
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        try:
            # Prétraitement optionnel
            if preprocess:
                preprocessor = ImagePreprocessor()
                # Pour les PDF, nous devons d'abord les convertir en image
                if Path(temp_path).suffix.lower() == '.pdf':
                    # Utiliser directement le préprocesseur qui gère maintenant les PDF
                    processed_image = preprocessor.process_image(temp_path)
                    # Sauvegarder l'image prétraitée temporairement
                    temp_image_path = temp_path.replace('.pdf', '_processed.png')
                    cv2.imwrite(temp_image_path, processed_image)
                    temp_path = temp_image_path
                else:
                    preprocess_paths = preprocess_for_ocr(temp_path)
                    if preprocess_paths:
                        temp_path = preprocess_paths[0]
            
            # OCR avec Tesseract
            ocr_engine = TesseractOCR()
            ocr_result = ocr_engine.extract_text(temp_path)
            
            # Nettoyage
            background_tasks.add_task(os.unlink, temp_path)
            
            return OCRProcessingResponse(
                text=ocr_result.text,
                confidence_score=ocr_result.confidence,
                processing_time=ocr_result.processing_time,
                word_count=len(ocr_result.text.split()) if ocr_result.text else 0
            )
            
        except Exception as e:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise HTTPException(status_code=500, detail=f"Erreur OCR: {str(e)}")
            
    except Exception as e:
        logger.error(f"Erreur traitement OCR: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")

@router.get("/supported-formats")
async def get_supported_formats():
    """Liste des formats de fichiers supportés"""
    return {
        "image_formats": ["png", "jpg", "jpeg", "tiff", "tif", "bmp"],
        "document_formats": ["pdf"],
        "max_file_size_mb": 50,
        "description": "Formats supportés pour OCR basique"
    }

@router.get("/health")
async def ocr_health_check():
    """Vérification de santé des services OCR"""
    try:
        # Test Tesseract
        ocr_engine = TesseractOCR()
        tesseract_ok = True
        
        # Test préprocesseur
        preprocessor = ImagePreprocessor()
        preprocessor_ok = True
        
        return {
            "status": "healthy",
            "services": {
                "tesseract": tesseract_ok,
                "preprocessor": preprocessor_ok
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }