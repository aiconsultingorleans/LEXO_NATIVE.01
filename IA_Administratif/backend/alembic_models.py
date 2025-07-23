"""
Modèles SQLAlchemy pour Alembic
Ce fichier reproduit les modèles sans dépendance aux modules async
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum as SQLEnum, Float, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData

# Base pour Alembic
metadata = MetaData()
Base = declarative_base(metadata=metadata)


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class DocumentCategory(str, Enum):
    FACTURES = "factures"
    IMPOTS = "impots"
    RIB = "rib"
    PIECES_IDENTITE = "pieces_identite"
    CONTRATS = "contrats"
    COURRIERS = "courriers"
    RELEVES_BANCAIRES = "releves_bancaires"
    NON_CLASSES = "non_classes"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)


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
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)