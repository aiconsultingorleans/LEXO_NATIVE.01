"""
Modèle document
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from core.database import Base


class DocumentCategory(str, Enum):
    FACTURES = "factures"
    IMPOTS = "impots"
    RIB = "rib"
    CONTRATS = "contrats"
    COURRIERS = "courriers"
    NON_CLASSES = "non_classes"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    category = Column(String, index=True, server_default='non_classes')
    confidence_score = Column(Float, default=0.0)
    
    # Données extraites
    ocr_text = Column(Text, nullable=True)
    entities = Column(JSON, default=list)
    amount = Column(Float, nullable=True)
    document_date = Column(DateTime(timezone=True), nullable=True)
    custom_tags = Column(JSON, default=list)
    embeddings_id = Column(String, nullable=True)
    
    # Métadonnées
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relations
    user = relationship("User", backref="documents")

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', category='{self.category}')>"