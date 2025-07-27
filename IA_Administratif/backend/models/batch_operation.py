"""
Modèles pour le traitement en batch avec rollback
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import List, Dict, Any, Optional

from core.database import Base


class BatchStatus(str, Enum):
    """Status des opérations batch"""
    PENDING = "pending"
    VALIDATING = "validating"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIAL_SUCCESS = "partial_success"


class DocumentProcessingStatus(str, Enum):
    """Status du traitement de document individuel"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    SKIPPED = "skipped"


class BatchOperation(Base):
    """
    Opération de traitement en batch
    Gère le traitement de plusieurs documents avec rollback
    """
    __tablename__ = "batch_operations"

    id = Column(Integer, primary_key=True, index=True)
    
    # Métadonnées batch
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    batch_name = Column(String, nullable=True)  # Nom optionnel donné par l'utilisateur
    status = Column(String, default=BatchStatus.PENDING, index=True)
    
    # Configuration
    total_files = Column(Integer, nullable=False, default=0)
    pipeline_type = Column(String, default="mistral", nullable=False)  # mistral | donut
    auto_rollback_on_error = Column(Boolean, default=True)
    
    # Progression
    files_processed = Column(Integer, default=0)
    files_succeeded = Column(Integer, default=0)
    files_failed = Column(Integer, default=0)
    current_file_index = Column(Integer, default=0)
    progress_percentage = Column(Float, default=0.0)
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    estimated_completion = Column(DateTime(timezone=True), nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    
    # Rollback
    can_rollback = Column(Boolean, default=True)
    rollback_snapshot_id = Column(String, nullable=True)  # ID du snapshot filesystem
    rollback_reason = Column(Text, nullable=True)
    
    # Résultats et logs
    error_message = Column(Text, nullable=True)
    processing_logs = Column(JSON, default=list)  # Logs détaillés du traitement
    summary_stats = Column(JSON, default=dict)  # Statistiques finales
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relations
    user = relationship("User", back_populates="batch_operations")
    batch_documents = relationship("BatchDocument", back_populates="batch_operation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BatchOperation(id={self.id}, status={self.status}, progress={self.progress_percentage:.1f}%)>"

    @property
    def is_active(self) -> bool:
        """Vérifie si l'opération est en cours"""
        return self.status in [BatchStatus.PENDING, BatchStatus.VALIDATING, BatchStatus.PROCESSING, BatchStatus.PAUSED]

    @property
    def is_completed(self) -> bool:
        """Vérifie si l'opération est terminée (succès ou échec)"""
        return self.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.ROLLED_BACK, BatchStatus.PARTIAL_SUCCESS]

    @property
    def success_rate(self) -> float:
        """Calcule le taux de succès"""
        if self.files_processed == 0:
            return 0.0
        return (self.files_succeeded / self.files_processed) * 100

    def update_progress(self):
        """Met à jour automatiquement le pourcentage de progression"""
        if self.total_files > 0:
            self.progress_percentage = (self.files_processed / self.total_files) * 100
        else:
            self.progress_percentage = 0.0

    def add_log(self, level: str, message: str, document_id: int = None):
        """Ajoute un log à l'opération"""
        if not self.processing_logs:
            self.processing_logs = []
        
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "document_id": document_id
        }
        
        self.processing_logs.append(log_entry)
        
        # Limiter à 1000 logs pour éviter la surcharge
        if len(self.processing_logs) > 1000:
            self.processing_logs = self.processing_logs[-1000:]


class BatchDocument(Base):
    """
    Document individuel dans une opération batch
    Tracking détaillé par document
    """
    __tablename__ = "batch_documents"

    id = Column(Integer, primary_key=True, index=True)
    
    # Relations
    batch_operation_id = Column(Integer, ForeignKey("batch_operations.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=True)  # Null si création échouée
    
    # Métadonnées fichier
    original_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    processing_order = Column(Integer, nullable=False)  # Ordre dans le batch
    
    # État traitement
    status = Column(String, default=DocumentProcessingStatus.PENDING, index=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Résultats
    confidence_score = Column(Float, nullable=True)
    category = Column(String, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Rollback
    original_file_path = Column(String, nullable=True)  # Chemin original avant traitement
    backup_file_path = Column(String, nullable=True)   # Chemin de sauvegarde pour rollback
    pre_processing_snapshot = Column(JSON, default=dict)  # État avant traitement
    
    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relations
    batch_operation = relationship("BatchOperation", back_populates="batch_documents")
    document = relationship("Document", backref="batch_document")

    def __repr__(self):
        return f"<BatchDocument(id={self.id}, filename={self.original_filename}, status={self.status})>"

    @property
    def can_retry(self) -> bool:
        """Vérifie si le document peut être retraité"""
        return self.status == DocumentProcessingStatus.FAILED and self.retry_count < self.max_retries

    @property
    def is_processed(self) -> bool:
        """Vérifie si le document a été traité (succès ou échec définitif)"""
        return self.status in [DocumentProcessingStatus.SUCCESS, DocumentProcessingStatus.FAILED, 
                             DocumentProcessingStatus.ROLLED_BACK, DocumentProcessingStatus.SKIPPED]

    def increment_retry(self):
        """Incrémente le compteur de retry"""
        self.retry_count += 1
        if self.retry_count >= self.max_retries:
            self.status = DocumentProcessingStatus.FAILED


class RollbackSnapshot(Base):
    """
    Snapshot pour rollback d'opérations batch
    Sauvegarde l'état du système avant modifications
    """
    __tablename__ = "rollback_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    
    # Identifiant unique du snapshot
    snapshot_id = Column(String, unique=True, nullable=False, index=True)
    
    # Métadonnées
    batch_operation_id = Column(Integer, ForeignKey("batch_operations.id"), nullable=False)
    snapshot_type = Column(String, nullable=False)  # filesystem | database | mixed
    
    # État sauvegardé
    filesystem_state = Column(JSON, default=dict)  # Structure des dossiers et fichiers
    database_state = Column(JSON, default=dict)    # État des tables affectées
    
    # Configuration rollback
    auto_cleanup = Column(Boolean, default=True)
    cleanup_after_days = Column(Integer, default=30)
    
    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    batch_operation = relationship("BatchOperation", backref="rollback_snapshot")

    def __repr__(self):
        return f"<RollbackSnapshot(id={self.snapshot_id}, type={self.snapshot_type})>"

    @property
    def is_expired(self) -> bool:
        """Vérifie si le snapshot a expiré"""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at