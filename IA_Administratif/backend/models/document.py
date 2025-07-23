"""
Modèle document
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Float, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from core.database import Base


class DocumentCategory(str, Enum):
    FACTURES = "factures"
    IMPOTS = "impots"
    RIB = "rib"
    PIECES_IDENTITE = "pieces_identite"
    CONTRATS = "contrats"
    COURRIERS = "courriers"
    RELEVES_BANCAIRES = "releves_bancaires"
    NON_CLASSES = "non_classes"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    
    # Classification
    category = Column(String, default=DocumentCategory.NON_CLASSES)
    confidence_score = Column(Float, default=0.0)
    
    # OCR Results
    ocr_text = Column(Text, nullable=True)
    entities = Column(JSON, default=list)  # List of extracted entities
    amount = Column(Float, nullable=True)  # Montant extrait
    document_date = Column(DateTime(timezone=True), nullable=True)  # Date du document
    
    # Metadata
    custom_tags = Column(JSON, default=list)
    embeddings_id = Column(String, nullable=True)  # ID dans ChromaDB
    
    # Relations
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", backref="documents")
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', category='{self.category}')>"