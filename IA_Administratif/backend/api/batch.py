"""
API endpoints pour le traitement en batch avec rollback
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from core.database import get_db
from models.user import User
from models.batch_operation import BatchOperation, BatchDocument, BatchStatus
from api.auth import get_current_user
from services.batch_processor import BatchProcessor, BatchConfig
from services.rollback_manager import RollbackManager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Instance globale du processeur batch
batch_processor = BatchProcessor()
rollback_manager = RollbackManager()


# === Modèles Pydantic ===

class BatchCreateRequest(BaseModel):
    """Requête de création de batch"""
    batch_name: Optional[str] = None
    pipeline_type: str = Field(default="mistral", pattern="^(mistral|donut)$")
    auto_rollback_on_error: bool = True
    max_retries_per_file: int = Field(default=3, ge=0, le=10)
    pause_on_error: bool = False


class BatchCreateResponse(BaseModel):
    """Réponse de création de batch"""
    batch_id: int
    message: str
    total_files: int
    estimated_duration_minutes: Optional[float] = None


class BatchStatusResponse(BaseModel):
    """Réponse de statut de batch"""
    id: int
    status: str
    progress_percentage: float
    files_processed: int
    files_succeeded: int
    files_failed: int
    total_files: int
    started_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    can_rollback: bool
    success_rate: Optional[float] = None
    processing_time_seconds: Optional[float] = None


class DocumentStatus(BaseModel):
    """Statut d'un document dans le batch"""
    filename: str
    status: str
    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    category: Optional[str] = None
    confidence: Optional[float] = None


class BatchDetailResponse(BaseModel):
    """Réponse détaillée d'un batch"""
    id: int
    batch_name: str
    status: str
    progress_percentage: float
    files_processed: int
    files_succeeded: int
    files_failed: int
    total_files: int
    pipeline_type: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    can_rollback: bool
    documents: List[DocumentStatus]
    recent_logs: List[Dict[str, Any]]


class BatchListResponse(BaseModel):
    """Liste des batches"""
    batches: List[BatchStatusResponse]
    total_count: int
    active_count: int


class RollbackRequest(BaseModel):
    """Requête de rollback"""
    reason: str = "User requested rollback"


class RollbackResponse(BaseModel):
    """Réponse de rollback"""
    success: bool
    message: str
    rollback_id: Optional[str] = None


# === Endpoints ===

@router.post("/batch/create", response_model=BatchCreateResponse)
async def create_batch(
    files: List[UploadFile] = File(...),
    request: BatchCreateRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Crée un nouveau batch de traitement de documents
    
    - **files**: Liste des fichiers à traiter (max 50 fichiers)
    - **batch_name**: Nom optionnel du batch  
    - **pipeline_type**: Type de pipeline (mistral ou donut)
    - **auto_rollback_on_error**: Rollback automatique en cas d'erreur
    """
    try:
        logger.info(f"📄 Création batch - {len(files)} fichiers pour user {current_user.id}")
        
        # Validation
        if len(files) == 0:
            raise HTTPException(
                status_code=400,
                detail="Aucun fichier fourni"
            )
        
        if len(files) > 50:
            raise HTTPException(
                status_code=400,
                detail="Limite de 50 fichiers par batch dépassée"
            )
        
        # Validation des types de fichiers
        supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
        for file in files:
            if not file.filename:
                raise HTTPException(
                    status_code=400,
                    detail="Nom de fichier manquant"
                )
            
            extension = file.filename.lower().split('.')[-1]
            if f'.{extension}' not in supported_extensions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Format non supporté: {extension}"
                )
        
        # Configuration du batch
        config = BatchConfig(
            user_id=current_user.id,
            pipeline_type=request.pipeline_type,
            auto_rollback_on_error=request.auto_rollback_on_error,
            max_retries_per_file=request.max_retries_per_file,
            pause_on_error=request.pause_on_error,
            batch_name=request.batch_name
        )
        
        # Créer le batch
        batch_id = await batch_processor.create_batch(files, config)
        
        # Estimation de durée (2 secondes par fichier en moyenne)
        estimated_duration = len(files) * 2.0 / 60  # en minutes
        
        return BatchCreateResponse(
            batch_id=batch_id,
            message=f"Batch créé avec succès avec {len(files)} fichiers",
            total_files=len(files),
            estimated_duration_minutes=estimated_duration
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur création batch: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors de la création du batch: {str(e)}"
        )


@router.post("/batch/{batch_id}/start")
async def start_batch_processing(
    batch_id: int,
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Démarre le traitement d'un batch créé
    
    - **batch_id**: ID du batch à traiter
    - **files**: Liste des fichiers (même ordre que lors de la création)
    """
    try:
        # Vérifier que le batch appartient à l'utilisateur
        result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.id == batch_id)
            .where(BatchOperation.user_id == current_user.id)
        )
        batch_op = result.scalar_one_or_none()
        
        if not batch_op:
            raise HTTPException(
                status_code=404,
                detail="Batch non trouvé"
            )
        
        if batch_op.status != BatchStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Batch dans un état non valide: {batch_op.status}"
            )
        
        # Démarrer le traitement en arrière-plan
        success = await batch_processor.start_batch_processing(batch_id, files)
        
        if not success:
            raise HTTPException(
                status_code=503,
                detail="Impossible de démarrer le traitement (limite atteinte ou batch déjà actif)"
            )
        
        logger.info(f"🚀 Batch {batch_id} démarré pour user {current_user.id}")
        
        return {
            "message": f"Traitement du batch {batch_id} démarré",
            "batch_id": batch_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur démarrage batch {batch_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du démarrage: {str(e)}"
        )


@router.get("/batch/{batch_id}/status", response_model=BatchDetailResponse)
async def get_batch_status(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère le statut détaillé d'un batch
    
    - **batch_id**: ID du batch
    """
    try:
        # Vérifier que le batch appartient à l'utilisateur
        result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.id == batch_id)
            .where(BatchOperation.user_id == current_user.id)
        )
        batch_op = result.scalar_one_or_none()
        
        if not batch_op:
            raise HTTPException(
                status_code=404,
                detail="Batch non trouvé"
            )
        
        # Récupérer le statut détaillé
        status_data = await batch_processor.get_batch_status(batch_id)
        
        if not status_data:
            raise HTTPException(
                status_code=500,
                detail="Erreur lors de la récupération du statut"
            )
        
        # Convertir en réponse
        documents = [
            DocumentStatus(
                filename=doc["filename"],
                status=doc["status"],
                processing_time=doc["processing_time"],
                error_message=doc["error_message"]
            )
            for doc in status_data["documents"]
        ]
        
        return BatchDetailResponse(
            id=batch_op.id,
            batch_name=batch_op.batch_name,
            status=status_data["status"],
            progress_percentage=status_data["progress_percentage"],
            files_processed=status_data["files_processed"],
            files_succeeded=status_data["files_succeeded"],
            files_failed=status_data["files_failed"],
            total_files=status_data["total_files"],
            pipeline_type=batch_op.pipeline_type,
            started_at=status_data["started_at"],
            completed_at=batch_op.completed_at,
            can_rollback=status_data["can_rollback"],
            documents=documents,
            recent_logs=status_data["logs"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur récupération statut batch {batch_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors de la récupération du statut: {str(e)}"
        )


@router.post("/batch/{batch_id}/pause")
async def pause_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Met en pause un batch en cours de traitement
    
    - **batch_id**: ID du batch à mettre en pause
    """
    try:
        # Vérifier que le batch appartient à l'utilisateur
        result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.id == batch_id)
            .where(BatchOperation.user_id == current_user.id)
        )
        batch_op = result.scalar_one_or_none()
        
        if not batch_op:
            raise HTTPException(
                status_code=404,
                detail="Batch non trouvé"
            )
        
        success = await batch_processor.pause_batch(batch_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Impossible de mettre en pause ce batch"
            )
        
        return {
            "message": f"Batch {batch_id} mis en pause",
            "batch_id": batch_id,
            "status": "paused"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur pause batch {batch_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors de la pause: {str(e)}"
        )


@router.post("/batch/{batch_id}/resume")
async def resume_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Reprend un batch en pause
    
    - **batch_id**: ID du batch à reprendre
    """
    try:
        # Vérifier que le batch appartient à l'utilisateur
        result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.id == batch_id)
            .where(BatchOperation.user_id == current_user.id)
        )
        batch_op = result.scalar_one_or_none()
        
        if not batch_op:
            raise HTTPException(
                status_code=404,
                detail="Batch non trouvé"
            )
        
        success = await batch_processor.resume_batch(batch_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Impossible de reprendre ce batch"
            )
        
        return {
            "message": f"Batch {batch_id} repris",
            "batch_id": batch_id,
            "status": "processing"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur reprise batch {batch_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors de la reprise: {str(e)}"
        )


@router.post("/batch/{batch_id}/rollback", response_model=RollbackResponse)
async def rollback_batch(
    batch_id: int,
    request: RollbackRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Effectue le rollback complet d'un batch
    
    - **batch_id**: ID du batch à annuler
    - **reason**: Raison du rollback
    """
    try:
        # Vérifier que le batch appartient à l'utilisateur
        result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.id == batch_id)
            .where(BatchOperation.user_id == current_user.id)
        )
        batch_op = result.scalar_one_or_none()
        
        if not batch_op:
            raise HTTPException(
                status_code=404,
                detail="Batch non trouvé"
            )
        
        if not batch_op.can_rollback:
            raise HTTPException(
                status_code=400,
                detail="Ce batch ne peut pas être annulé (rollback déjà effectué ou snapshot expiré)"
            )
        
        # Effectuer le rollback
        success = await batch_processor.rollback_batch(batch_id, request.reason)
        
        if success:
            return RollbackResponse(
                success=True,
                message=f"Rollback du batch {batch_id} effectué avec succès",
                rollback_id=batch_op.rollback_snapshot_id
            )
        else:
            return RollbackResponse(
                success=False,
                message=f"Échec du rollback du batch {batch_id}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur rollback batch {batch_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du rollback: {str(e)}"
        )


@router.get("/batch/list", response_model=BatchListResponse)
async def list_user_batches(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
    offset: int = 0
):
    """
    Liste les batches de l'utilisateur
    
    - **limit**: Nombre maximum de résultats (max 100)
    - **offset**: Décalage pour pagination
    """
    try:
        if limit > 100:
            limit = 100
        
        # Récupérer les batches de l'utilisateur
        result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.user_id == current_user.id)
            .order_by(BatchOperation.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        batches = result.scalars().all()
        
        # Compter le total
        count_result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.user_id == current_user.id)
        )
        total_count = len(count_result.scalars().all())
        
        # Compter les actifs
        active_result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.user_id == current_user.id)
            .where(BatchOperation.status.in_([
                BatchStatus.PENDING, BatchStatus.VALIDATING, 
                BatchStatus.PROCESSING, BatchStatus.PAUSED
            ]))
        )
        active_count = len(active_result.scalars().all())
        
        # Convertir en réponse
        batch_list = []
        for batch in batches:
            batch.update_progress()
            
            batch_list.append(BatchStatusResponse(
                id=batch.id,
                status=batch.status,
                progress_percentage=batch.progress_percentage,
                files_processed=batch.files_processed,
                files_succeeded=batch.files_succeeded,
                files_failed=batch.files_failed,
                total_files=batch.total_files,
                started_at=batch.started_at,
                estimated_completion=batch.estimated_completion,
                can_rollback=batch.can_rollback and bool(batch.rollback_snapshot_id),
                success_rate=batch.success_rate,
                processing_time_seconds=batch.processing_time_seconds
            ))
        
        return BatchListResponse(
            batches=batch_list,
            total_count=total_count,
            active_count=active_count
        )
        
    except Exception as e:
        logger.error(f"❌ Erreur liste batches: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors de la récupération des batches: {str(e)}"
        )


@router.get("/batch/{batch_id}/snapshot")
async def get_batch_snapshot_info(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère les informations du snapshot de rollback d'un batch
    
    - **batch_id**: ID du batch
    """
    try:
        # Vérifier que le batch appartient à l'utilisateur
        result = await db.execute(
            select(BatchOperation)
            .where(BatchOperation.id == batch_id)
            .where(BatchOperation.user_id == current_user.id)
        )
        batch_op = result.scalar_one_or_none()
        
        if not batch_op:
            raise HTTPException(
                status_code=404,
                detail="Batch non trouvé"
            )
        
        # Récupérer les informations du snapshot
        snapshot_info = await rollback_manager.get_snapshot_info(batch_id)
        
        if not snapshot_info:
            raise HTTPException(
                status_code=404,
                detail="Aucun snapshot trouvé pour ce batch"
            )
        
        return snapshot_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur info snapshot batch {batch_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors de la récupération du snapshot: {str(e)}"
        )


@router.post("/batch/cleanup-snapshots")
async def cleanup_expired_snapshots(
    current_user: User = Depends(get_current_user)
):
    """
    Nettoie les snapshots expirés (admin uniquement)
    """
    try:
        # Note: Dans une vraie implémentation, on vérifierait les permissions admin
        await rollback_manager.cleanup_old_snapshots()
        
        return {
            "message": "Nettoyage des snapshots expirés effectué",
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage snapshots: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne lors du nettoyage: {str(e)}"
        )