"""
API de classification et correction de documents
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from core.database import get_db
from models.user import User
from models.document import Document
from api.auth import get_current_user
from services.document_classifier import get_document_classifier, DocumentCategory

router = APIRouter()
logger = logging.getLogger(__name__)


# Schemas
class ClassificationRequest(BaseModel):
    filename: str
    ocr_text: str
    entities: List[Any] = []


class ClassificationResponse(BaseModel):
    category: str
    confidence: float
    score: float
    matched_rules: List[str] = []
    reasoning: str
    all_scores: Dict[str, float] = {}


class DocumentCorrectionRequest(BaseModel):
    document_id: int
    new_category: str
    reason: Optional[str] = None


class ClassificationStatsResponse(BaseModel):
    total_documents: int
    categories_distribution: Dict[str, int]
    average_confidence: float
    low_confidence_count: int
    classifier_stats: Dict[str, Any]


# Endpoints
@router.post("/classify", response_model=ClassificationResponse)
async def classify_text(
    request: ClassificationRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Classifie un document à partir de son nom et contenu
    """
    try:
        classifier = get_document_classifier()
        result = classifier.classify_document(
            filename=request.filename,
            ocr_text=request.ocr_text,
            entities=request.entities
        )
        
        # Calculer tous les scores pour debug
        all_scores = {}
        for category in DocumentCategory:
            test_result = classifier.classify_document(
                filename=request.filename,
                ocr_text=request.ocr_text,
                entities=request.entities
            )
            # Note: pour une vraie implémentation, il faudrait modifier le classificateur
            # pour retourner tous les scores, pas juste le meilleur
        
        return ClassificationResponse(
            category=result.category,
            confidence=result.confidence,
            score=result.score,
            matched_rules=result.matched_rules,
            reasoning=result.reasoning,
            all_scores=all_scores
        )
        
    except Exception as e:
        logger.error(f"Erreur classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la classification: {str(e)}"
        )


@router.post("/correct/{document_id}")
async def correct_document_classification(
    document_id: int,
    request: DocumentCorrectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Corrige la classification d'un document
    """
    try:
        # Vérifier que le document existe et appartient à l'utilisateur
        result = await db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.user_id == current_user.id
            )
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document non trouvé"
            )
        
        # Vérifier que la nouvelle catégorie est valide
        valid_categories = [cat.value for cat in DocumentCategory]
        if request.new_category not in valid_categories:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Catégorie invalide. Catégories valides: {valid_categories}"
            )
        
        # Mettre à jour le document
        old_category = document.category
        await db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                category=request.new_category,
                custom_tags=[request.new_category] + (document.custom_tags or [])
            )
        )
        await db.commit()
        
        logger.info(f"📝 Correction classification: {document.filename}")
        logger.info(f"   📋 {old_category} → {request.new_category}")
        logger.info(f"   👤 Par: {current_user.email}")
        if request.reason:
            logger.info(f"   💬 Raison: {request.reason}")
        
        return {
            "success": True,
            "message": f"Classification corrigée: {old_category} → {request.new_category}",
            "document_id": document_id,
            "old_category": old_category,
            "new_category": request.new_category
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur correction classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la correction: {str(e)}"
        )


@router.get("/stats", response_model=ClassificationStatsResponse)
async def get_classification_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Récupère les statistiques de classification
    """
    try:
        # Compter les documents par catégorie
        result = await db.execute(
            select(Document).where(Document.user_id == current_user.id)
        )
        documents = result.scalars().all()
        
        if not documents:
            return ClassificationStatsResponse(
                total_documents=0,
                categories_distribution={},
                average_confidence=0.0,
                low_confidence_count=0,
                classifier_stats={}
            )
        
        # Distribution par catégorie
        categories_distribution = {}
        confidences = []
        low_confidence_count = 0
        
        for doc in documents:
            category = doc.category
            categories_distribution[category] = categories_distribution.get(category, 0) + 1
            
            if doc.confidence_score:
                confidences.append(doc.confidence_score)
                if doc.confidence_score < 0.7:
                    low_confidence_count += 1
        
        # Moyenne de confiance
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Stats du classificateur
        classifier = get_document_classifier()
        classifier_stats = classifier.get_classification_statistics()
        
        return ClassificationStatsResponse(
            total_documents=len(documents),
            categories_distribution=categories_distribution,
            average_confidence=average_confidence,
            low_confidence_count=low_confidence_count,
            classifier_stats=classifier_stats
        )
        
    except Exception as e:
        logger.error(f"Erreur stats classification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la récupération des stats: {str(e)}"
        )


@router.get("/categories")
async def get_available_categories():
    """
    Retourne la liste des catégories disponibles
    """
    return {
        "categories": [
            {
                "value": cat.value,
                "label": cat.value.replace("_", " ").title()
            }
            for cat in DocumentCategory
        ]
    }