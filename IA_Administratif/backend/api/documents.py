"""
Endpoints de gestion des documents
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
from datetime import datetime
from pathlib import Path

from core.database import get_db
from models.user import User
from models.document import Document, DocumentCategory
from api.auth import get_current_user
from services.ocr_watcher import OCRFileHandler

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
    summary: str | None = None
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
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload d'un nouveau document avec traitement OCR automatique"""
    import os
    from datetime import datetime
    
    # Create upload directory dans le dossier surveillé
    upload_dir = "/app/ocr_data"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file directement dans le dossier surveillé
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(upload_dir, safe_filename)
    
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Create document entry temporaire (sera mis à jour par le traitement OCR)
    document = Document(
        filename=file.filename,
        original_filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        mime_type=file.content_type or "application/octet-stream",
        user_id=current_user.id,
        category="non_classe",  # Sera mis à jour par le traitement
        confidence_score=0.0,
        ocr_text="",
        entities=[],
        custom_tags=[],
        processed_at=None  # Indique qu'il n'est pas encore traité
    )
    
    db.add(document)
    await db.commit()
    await db.refresh(document)
    
    # Lancer le traitement OCR en arrière-plan
    background_tasks.add_task(
        process_uploaded_document,
        file_path,
        document.id,
        current_user.id
    )
    
    return document


async def process_uploaded_document(file_path: str, document_id: int, user_id: int):
    """Traite un document uploadé avec OCR et Mistral"""
    import logging
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 Début traitement document uploadé: {Path(file_path).name}")
    
    try:
        # Utiliser le handler OCR du watcher
        ocr_handler = OCRFileHandler()
        
        # Override temporaire pour utiliser l'utilisateur courant
        original_get_admin = ocr_handler._get_admin_user
        async def get_current_user_override():
            from core.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.id == user_id)
                )
                return result.scalar_one_or_none()
        
        ocr_handler._get_admin_user = get_current_user_override
        
        # Traiter le fichier
        await ocr_handler._process_file(Path(file_path))
        
        # Supprimer l'entrée temporaire car le watcher en crée une nouvelle
        from core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            temp_doc = result.scalar_one_or_none()
            if temp_doc and not temp_doc.processed_at:
                await db.delete(temp_doc)
                await db.commit()
        
        logger.info(f"✅ Traitement terminé: {Path(file_path).name}")
        
    except Exception as e:
        logger.error(f"❌ Erreur traitement upload {Path(file_path).name}: {e}")
        import traceback
        traceback.print_exc()


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