"""
Endpoints de gestion des documents
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
from datetime import datetime

from core.database import get_db
from models.user import User
from models.document import Document, DocumentCategory
from api.auth import get_current_user

router = APIRouter()


# Schemas
class DocumentResponse(BaseModel):
    id: int
    filename: str
    category: str
    confidence_score: float
    ocr_text: str | None
    entities: List[str] = []
    amount: float | None
    document_date: datetime | None
    custom_tags: List[str] = []
    created_at: datetime
    processed_at: datetime | None

    class Config:
        from_attributes = True


class DocumentsListResponse(BaseModel):
    documents: List[DocumentResponse]
    total: int
    page: int
    limit: int


# Endpoints
@router.get("/", response_model=DocumentsListResponse)
async def get_documents(
    page: int = 1,
    limit: int = 20,
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Récupère la liste des documents de l'utilisateur"""
    query = select(Document).where(Document.user_id == current_user.id)
    
    if category:
        query = query.where(Document.category == category)
    
    # Count total
    count_result = await db.execute(query)
    total = len(count_result.scalars().all())
    
    # Paginated results
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit).order_by(Document.created_at.desc())
    
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return DocumentsListResponse(
        documents=documents,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Récupère un document spécifique"""
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
            detail="Document not found"
        )
    
    return document


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload d'un nouveau document"""
    # TODO: Implémenter la logique d'upload et de traitement OCR
    # Pour l'instant, on crée juste l'entrée en base
    
    document = Document(
        filename=file.filename,
        original_filename=file.filename,
        file_path=f"/tmp/{file.filename}",  # Temporaire
        file_size=0,  # À calculer
        mime_type=file.content_type or "application/octet-stream",
        user_id=current_user.id
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    return document


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Supprime un document"""
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
            detail="Document not found"
        )
    
    await db.delete(document)
    await db.commit()
    
    return {"message": "Document deleted successfully"}