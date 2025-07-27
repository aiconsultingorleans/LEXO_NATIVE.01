"""
Service de traitement en batch avec rollback
Orchestration du traitement de plusieurs documents
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from fastapi import UploadFile

from models.batch_operation import (
    BatchOperation, BatchDocument, BatchStatus, DocumentProcessingStatus
)
from models.document import Document
from models.user import User
from core.database import AsyncSessionLocal
from services.rollback_manager import RollbackManager
from services.ocr_watcher import OCRFileHandler
from api.documents import clean_filename

logger = logging.getLogger(__name__)


@dataclass
class BatchFile:
    """Représentation d'un fichier dans un batch"""
    file: UploadFile
    original_filename: str
    cleaned_filename: str
    size: int
    mime_type: str


@dataclass
class BatchConfig:
    """Configuration pour un traitement batch"""
    user_id: int
    pipeline_type: str = "mistral"  # mistral | donut
    auto_rollback_on_error: bool = True
    max_retries_per_file: int = 3
    pause_on_error: bool = False
    batch_name: Optional[str] = None
    concurrent_processing: bool = False  # Pour futur usage


@dataclass
class ProcessingResult:
    """Résultat du traitement d'un document"""
    success: bool
    document_id: Optional[int] = None
    category: Optional[str] = None
    confidence: Optional[float] = None
    processing_time: Optional[float] = None
    error_message: Optional[str] = None


class BatchProcessor:
    """
    Processeur de traitement en batch avec support rollback
    
    Fonctionnalités :
    - Traitement séquentiel de fichiers multiples
    - Snapshots automatiques avant modifications
    - Rollback complet ou partiel en cas d'erreur
    - Pause/Reprise des opérations
    - Monitoring temps réel du progrès
    """

    def __init__(self):
        self.rollback_manager = RollbackManager()
        self.ocr_handler = OCRFileHandler()
        self.active_batches: Dict[int, asyncio.Task] = {}
        self.paused_batches: Dict[int, bool] = {}
        
        # Configuration
        self.max_concurrent_batches = 3
        self.ocr_base_path = Path("/Users/stephaneansel/Documents/LEXO_v1/OCR")
        
        logger.info("BatchProcessor initialisé")

    async def create_batch(self, files: List[UploadFile], config: BatchConfig) -> int:
        """
        Crée une nouvelle opération batch
        
        Args:
            files: Liste des fichiers à traiter
            config: Configuration du batch
            
        Returns:
            ID du batch créé
        """
        try:
            logger.info(f"🚀 Création batch - {len(files)} fichiers pour user {config.user_id}")
            
            # 1. Validation des fichiers
            batch_files = []
            total_size = 0
            
            for file in files:
                if not file.filename:
                    continue
                    
                # Validation du type de fichier
                file_extension = Path(file.filename).suffix.lower()
                if file_extension not in {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}:
                    raise ValueError(f"Format non supporté: {file_extension} ({file.filename})")
                
                # Préparation du fichier
                cleaned_filename = clean_filename(file.filename)
                file_size = 0  # FastAPI UploadFile n'expose pas la taille directement
                
                batch_files.append(BatchFile(
                    file=file,
                    original_filename=file.filename,
                    cleaned_filename=cleaned_filename,
                    size=file_size,
                    mime_type=self._get_mime_type(file_extension)
                ))
                
                total_size += file_size
            
            if not batch_files:
                raise ValueError("Aucun fichier valide dans le batch")
            
            # 2. Créer l'opération batch en base
            async with AsyncSessionLocal() as db:
                batch_op = BatchOperation(
                    user_id=config.user_id,
                    batch_name=config.batch_name or f"Batch {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    total_files=len(batch_files),
                    pipeline_type=config.pipeline_type,
                    auto_rollback_on_error=config.auto_rollback_on_error,
                    status=BatchStatus.PENDING
                )
                
                db.add(batch_op)
                await db.flush()  # Pour obtenir l'ID
                
                # 3. Créer les entrées pour chaque document
                for i, batch_file in enumerate(batch_files):
                    batch_doc = BatchDocument(
                        batch_operation_id=batch_op.id,
                        original_filename=batch_file.original_filename,
                        file_size=batch_file.size,
                        mime_type=batch_file.mime_type,
                        processing_order=i,
                        max_retries=config.max_retries_per_file
                    )
                    db.add(batch_doc)
                
                await db.commit()
                
                batch_op.add_log("INFO", f"Batch créé avec {len(batch_files)} fichiers")
                await db.commit()
                
                logger.success(f"✅ Batch {batch_op.id} créé avec {len(batch_files)} fichiers")
                return batch_op.id
                
        except Exception as e:
            logger.error(f"❌ Erreur création batch: {e}")
            raise

    async def start_batch_processing(self, batch_id: int, files: List[UploadFile]) -> bool:
        """
        Démarre le traitement d'un batch
        
        Args:
            batch_id: ID du batch à traiter
            files: Liste des fichiers (dans le même ordre que lors de la création)
            
        Returns:
            True si le démarrage a réussi
        """
        try:
            if batch_id in self.active_batches:
                logger.warning(f"Batch {batch_id} déjà en cours de traitement")
                return False
            
            if len(self.active_batches) >= self.max_concurrent_batches:
                logger.warning(f"Limite de batches concurrents atteinte ({self.max_concurrent_batches})")
                return False
            
            logger.info(f"🚀 Démarrage traitement batch {batch_id}")
            
            # Créer et démarrer la tâche de traitement
            task = asyncio.create_task(self._process_batch_async(batch_id, files))
            self.active_batches[batch_id] = task
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur démarrage batch {batch_id}: {e}")
            return False

    async def _process_batch_async(self, batch_id: int, files: List[UploadFile]):
        """Traitement asynchrone d'un batch complet"""
        try:
            async with AsyncSessionLocal() as db:
                # 1. Mettre à jour le statut
                await db.execute(
                    update(BatchOperation)
                    .where(BatchOperation.id == batch_id)
                    .values(
                        status=BatchStatus.VALIDATING,
                        started_at=datetime.utcnow()
                    )
                )
                await db.commit()
            
            # 2. Créer un snapshot avant le traitement
            logger.info(f"📸 Création snapshot pour batch {batch_id}")
            paths_to_monitor = [
                str(self.ocr_base_path),
                str(self.ocr_base_path / "factures"),
                str(self.ocr_base_path / "impots"),
                str(self.ocr_base_path / "rib"),
                str(self.ocr_base_path / "contrats"),
                str(self.ocr_base_path / "courriers"),
                str(self.ocr_base_path / "non_classes")
            ]
            
            snapshot_id = await self.rollback_manager.create_snapshot(batch_id, paths_to_monitor)
            
            # 3. Mettre à jour avec l'ID du snapshot
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(BatchOperation)
                    .where(BatchOperation.id == batch_id)
                    .values(
                        rollback_snapshot_id=snapshot_id,
                        status=BatchStatus.PROCESSING
                    )
                )
                await db.commit()
            
            # 4. Traiter les fichiers un par un
            success_count = 0
            failed_count = 0
            
            async for result in self._process_files_sequentially(batch_id, files):
                if result.success:
                    success_count += 1
                else:
                    failed_count += 1
                    
                    # Vérifier si on doit faire un rollback automatique
                    async with AsyncSessionLocal() as db:
                        batch_result = await db.execute(
                            select(BatchOperation).where(BatchOperation.id == batch_id)
                        )
                        batch_op = batch_result.scalar_one()
                        
                        if batch_op.auto_rollback_on_error:
                            logger.warning(f"🔄 Erreur détectée - Rollback automatique batch {batch_id}")
                            await self.rollback_batch(batch_id, "Erreur automatique détectée")
                            return
                
                # Vérifier si le batch a été mis en pause
                if batch_id in self.paused_batches and self.paused_batches[batch_id]:
                    logger.info(f"⏸️ Batch {batch_id} mis en pause")
                    async with AsyncSessionLocal() as db:
                        await db.execute(
                            update(BatchOperation)
                            .where(BatchOperation.id == batch_id)
                            .values(status=BatchStatus.PAUSED)
                        )
                        await db.commit()
                    return
            
            # 5. Finaliser le batch
            await self._finalize_batch(batch_id, success_count, failed_count)
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement batch {batch_id}: {e}")
            await self._handle_batch_error(batch_id, str(e))
        finally:
            # Nettoyer
            self.active_batches.pop(batch_id, None)
            self.paused_batches.pop(batch_id, None)

    async def _process_files_sequentially(self, batch_id: int, files: List[UploadFile]) -> AsyncGenerator[ProcessingResult, None]:
        """Traite les fichiers un par un en séquence"""
        try:
            async with AsyncSessionLocal() as db:
                # Récupérer les documents du batch
                result = await db.execute(
                    select(BatchDocument)
                    .where(BatchDocument.batch_operation_id == batch_id)
                    .order_by(BatchDocument.processing_order)
                )
                batch_documents = result.scalars().all()
            
            for i, (batch_doc, file) in enumerate(zip(batch_documents, files)):
                logger.info(f"📄 Traitement {i+1}/{len(files)}: {batch_doc.original_filename}")
                
                # Marquer comme en cours
                async with AsyncSessionLocal() as db:
                    batch_doc.status = DocumentProcessingStatus.PROCESSING
                    batch_doc.started_at = datetime.utcnow()
                    db.add(batch_doc)
                    await db.commit()
                
                start_time = time.time()
                result = await self._process_single_file(batch_doc, file)
                processing_time = time.time() - start_time
                
                # Mettre à jour le résultat
                async with AsyncSessionLocal() as db:
                    batch_doc.processing_time_seconds = processing_time
                    batch_doc.completed_at = datetime.utcnow()
                    
                    if result.success:
                        batch_doc.status = DocumentProcessingStatus.SUCCESS
                        batch_doc.document_id = result.document_id
                        batch_doc.category = result.category
                        batch_doc.confidence_score = result.confidence
                    else:
                        if batch_doc.can_retry:
                            batch_doc.increment_retry()
                            batch_doc.status = DocumentProcessingStatus.PROCESSING
                            # Réessayer
                            result = await self._process_single_file(batch_doc, file)
                            if result.success:
                                batch_doc.status = DocumentProcessingStatus.SUCCESS
                                batch_doc.document_id = result.document_id
                                batch_doc.category = result.category
                                batch_doc.confidence_score = result.confidence
                            else:
                                batch_doc.status = DocumentProcessingStatus.FAILED
                                batch_doc.error_message = result.error_message
                        else:
                            batch_doc.status = DocumentProcessingStatus.FAILED
                            batch_doc.error_message = result.error_message
                    
                    db.add(batch_doc)
                    
                    # Mettre à jour la progression du batch
                    await db.execute(
                        update(BatchOperation)
                        .where(BatchOperation.id == batch_id)
                        .values(
                            current_file_index=i + 1,
                            files_processed=i + 1,
                            files_succeeded=await self._count_successful_docs(batch_id),
                            files_failed=await self._count_failed_docs(batch_id)
                        )
                    )
                    
                    await db.commit()
                
                yield result
                
        except Exception as e:
            logger.error(f"Erreur traitement séquentiel: {e}")
            yield ProcessingResult(success=False, error_message=str(e))

    async def _process_single_file(self, batch_doc: BatchDocument, file: UploadFile) -> ProcessingResult:
        """Traite un fichier individuel"""
        try:
            # Sauvegarder le fichier temporairement
            temp_dir = Path("/tmp/lexo_batch_processing")
            temp_dir.mkdir(exist_ok=True)
            
            temp_file_path = temp_dir / clean_filename(batch_doc.original_filename)
            
            # Éviter les conflits de nom
            counter = 1
            original_path = temp_file_path
            while temp_file_path.exists():
                stem = original_path.stem
                suffix = original_path.suffix
                temp_file_path = temp_dir / f"{stem}_{counter}{suffix}"
                counter += 1
            
            content = await file.read()
            with open(temp_file_path, 'wb') as f:
                f.write(content)
            
            # Traiter avec le pipeline OCR existant
            # (Réutiliser la logique de OCRFileHandler)
            
            # Pour cette implémentation, on simule le traitement
            # Dans la vraie version, on appellerait l'API de traitement
            await asyncio.sleep(0.5)  # Simulation du traitement
            
            # Nettoyage
            if temp_file_path.exists():
                temp_file_path.unlink()
            
            return ProcessingResult(
                success=True,
                document_id=12345,  # ID simulé
                category="factures",
                confidence=0.85,
                processing_time=0.5
            )
            
        except Exception as e:
            logger.error(f"Erreur traitement fichier {batch_doc.original_filename}: {e}")
            return ProcessingResult(success=False, error_message=str(e))

    async def _count_successful_docs(self, batch_id: int) -> int:
        """Compte les documents traités avec succès"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(BatchDocument)
                .where(BatchDocument.batch_operation_id == batch_id)
                .where(BatchDocument.status == DocumentProcessingStatus.SUCCESS)
            )
            return len(result.scalars().all())

    async def _count_failed_docs(self, batch_id: int) -> int:
        """Compte les documents échoués"""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(BatchDocument)
                .where(BatchDocument.batch_operation_id == batch_id)
                .where(BatchDocument.status == DocumentProcessingStatus.FAILED)
            )
            return len(result.scalars().all())

    async def _finalize_batch(self, batch_id: int, success_count: int, failed_count: int):
        """Finalise un batch terminé"""
        try:
            async with AsyncSessionLocal() as db:
                # Déterminer le statut final
                if failed_count == 0:
                    final_status = BatchStatus.COMPLETED
                elif success_count == 0:
                    final_status = BatchStatus.FAILED
                else:
                    final_status = BatchStatus.PARTIAL_SUCCESS
                
                # Calculer les statistiques
                total_files = success_count + failed_count
                success_rate = (success_count / total_files) * 100 if total_files > 0 else 0
                
                # Mettre à jour le batch
                await db.execute(
                    update(BatchOperation)
                    .where(BatchOperation.id == batch_id)
                    .values(
                        status=final_status,
                        completed_at=datetime.utcnow(),
                        files_succeeded=success_count,
                        files_failed=failed_count,
                        summary_stats={
                            "success_rate": success_rate,
                            "total_processed": total_files,
                            "completion_time": datetime.utcnow().isoformat()
                        }
                    )
                )
                await db.commit()
                
                logger.success(f"✅ Batch {batch_id} terminé - {success_count}/{total_files} réussis")
                
        except Exception as e:
            logger.error(f"Erreur finalisation batch {batch_id}: {e}")

    async def _handle_batch_error(self, batch_id: int, error_message: str):
        """Gère les erreurs de batch"""
        try:
            async with AsyncSessionLocal() as db:
                await db.execute(
                    update(BatchOperation)
                    .where(BatchOperation.id == batch_id)
                    .values(
                        status=BatchStatus.FAILED,
                        error_message=error_message,
                        completed_at=datetime.utcnow()
                    )
                )
                await db.commit()
                
        except Exception as e:
            logger.error(f"Erreur gestion erreur batch {batch_id}: {e}")

    async def pause_batch(self, batch_id: int) -> bool:
        """Met en pause un batch en cours"""
        if batch_id not in self.active_batches:
            return False
        
        self.paused_batches[batch_id] = True
        logger.info(f"⏸️ Batch {batch_id} marqué pour pause")
        return True

    async def resume_batch(self, batch_id: int) -> bool:
        """Reprend un batch en pause"""
        if batch_id not in self.paused_batches:
            return False
        
        self.paused_batches[batch_id] = False
        
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(BatchOperation)
                .where(BatchOperation.id == batch_id)
                .values(status=BatchStatus.PROCESSING)
            )
            await db.commit()
        
        logger.info(f"▶️ Batch {batch_id} repris")
        return True

    async def rollback_batch(self, batch_id: int, reason: str = "User requested") -> bool:
        """Effectue le rollback d'un batch"""
        try:
            # Arrêter le traitement s'il est en cours
            if batch_id in self.active_batches:
                task = self.active_batches[batch_id]
                task.cancel()
                self.active_batches.pop(batch_id, None)
            
            # Effectuer le rollback
            success = await self.rollback_manager.rollback_batch(batch_id, reason)
            
            if success:
                logger.success(f"✅ Rollback batch {batch_id} réussi")
            else:
                logger.error(f"❌ Rollback batch {batch_id} échoué")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur rollback batch {batch_id}: {e}")
            return False

    async def get_batch_status(self, batch_id: int) -> Optional[Dict[str, Any]]:
        """Récupère le statut détaillé d'un batch"""
        try:
            async with AsyncSessionLocal() as db:
                # Récupérer le batch
                result = await db.execute(
                    select(BatchOperation).where(BatchOperation.id == batch_id)
                )
                batch_op = result.scalar_one_or_none()
                
                if not batch_op:
                    return None
                
                # Récupérer les documents
                docs_result = await db.execute(
                    select(BatchDocument)
                    .where(BatchDocument.batch_operation_id == batch_id)
                    .order_by(BatchDocument.processing_order)
                )
                documents = docs_result.scalars().all()
                
                # Calculer la progression
                batch_op.update_progress()
                
                return {
                    "id": batch_op.id,
                    "status": batch_op.status,
                    "progress_percentage": batch_op.progress_percentage,
                    "files_processed": batch_op.files_processed,
                    "files_succeeded": batch_op.files_succeeded,
                    "files_failed": batch_op.files_failed,
                    "total_files": batch_op.total_files,
                    "started_at": batch_op.started_at,
                    "estimated_completion": batch_op.estimated_completion,
                    "can_rollback": batch_op.can_rollback and batch_op.rollback_snapshot_id,
                    "documents": [
                        {
                            "filename": doc.original_filename,
                            "status": doc.status,
                            "processing_time": doc.processing_time_seconds,
                            "error_message": doc.error_message
                        }
                        for doc in documents
                    ],
                    "logs": batch_op.processing_logs[-10:] if batch_op.processing_logs else []
                }
                
        except Exception as e:
            logger.error(f"Erreur récupération statut batch {batch_id}: {e}")
            return None

    def _get_mime_type(self, extension: str) -> str:
        """Détermine le type MIME d'un fichier"""
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.bmp': 'image/bmp'
        }
        return mime_types.get(extension.lower(), 'application/octet-stream')