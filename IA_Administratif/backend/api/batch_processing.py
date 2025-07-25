"""
API pour le traitement par lot des fichiers OCR
Permet de traiter les fichiers existants non analysés
"""

import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.database import get_db
from core.auth import get_current_user
from models.user import User
from models.document import Document
from services.ocr_watcher import OCRFileHandler

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/api/v1/batch/scan-folder")
async def scan_ocr_folder(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Scanne le dossier OCR pour identifier les fichiers non traités"""
    
    ocr_folder = Path("/app/ocr_data")
    if not ocr_folder.exists():
        raise HTTPException(status_code=404, detail="Dossier OCR introuvable")
    
    # Extensions supportées
    supported_extensions = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
    
    # Fichiers dans le dossier OCR (racine seulement)
    all_files = []
    for file_path in ocr_folder.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
            all_files.append({
                "name": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime
            })
    
    # Fichiers déjà en base
    result = await db.execute(select(Document))
    processed_files = {doc.filename for doc in result.scalars()}
    
    # Fichiers non traités
    unprocessed_files = [
        file_info for file_info in all_files 
        if file_info["name"] not in processed_files
    ]
    
    return {
        "total_files": len(all_files),
        "processed_files": len(processed_files),
        "unprocessed_files": len(unprocessed_files),
        "files": unprocessed_files
    }


@router.post("/api/v1/batch/process-unprocessed")
async def process_unprocessed_files(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lance le traitement en arrière-plan des fichiers non traités"""
    
    # Identifier les fichiers non traités
    scan_result = await scan_ocr_folder(current_user, db)
    unprocessed_files = scan_result["files"]
    
    if not unprocessed_files:
        return {
            "success": True,
            "message": "Aucun fichier à traiter",
            "count": 0
        }
    
    # Lancer le traitement en arrière-plan
    background_tasks.add_task(
        process_files_batch, 
        [f["path"] for f in unprocessed_files],
        current_user.id
    )
    
    return {
        "success": True,
        "message": f"Traitement de {len(unprocessed_files)} fichiers lancé en arrière-plan",
        "count": len(unprocessed_files),
        "files": [f["name"] for f in unprocessed_files]
    }


@router.post("/api/v1/batch/process-file")
async def process_single_file(
    file_path: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Traite un fichier spécifique"""
    
    file_path_obj = Path(file_path)
    if not file_path_obj.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    
    # Lancer le traitement en arrière-plan
    background_tasks.add_task(
        process_files_batch, 
        [str(file_path_obj)],
        current_user.id
    )
    
    return {
        "success": True,
        "message": f"Traitement de {file_path_obj.name} lancé",
        "file": file_path_obj.name
    }


async def process_files_batch(file_paths: List[str], user_id: int):
    """Traite une liste de fichiers en arrière-plan"""
    
    logger.info(f"🚀 Début traitement batch: {len(file_paths)} fichiers")
    
    # Créer un handler OCR temporaire
    ocr_handler = OCRFileHandler()
    
    # Forcer l'utilisateur admin pour le batch
    ocr_handler._admin_user_id = user_id
    
    for file_path in file_paths:
        try:
            file_path_obj = Path(file_path)
            logger.info(f"📄 Traitement batch: {file_path_obj.name}")
            
            # Utiliser la même logique que le watcher
            await ocr_handler._process_file(file_path_obj)
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement batch {file_path}: {e}")
            continue
    
    logger.info(f"✅ Traitement batch terminé: {len(file_paths)} fichiers")


@router.get("/api/v1/batch/status")
async def get_batch_status():
    """Retourne le statut des traitements en cours"""
    
    # Pour l'instant, simple retour statique
    # Pourrait être étendu avec un système de suivi des tâches
    return {
        "active_tasks": 0,
        "last_batch_run": None,
        "total_processed_today": 0
    }


# Modification du handler OCR pour supporter le batch
class BatchOCRHandler(OCRFileHandler):
    """Handler OCR spécialisé pour le traitement par lot"""
    
    def __init__(self, user_id: int):
        super().__init__()
        self._admin_user_id = user_id
    
    async def _get_admin_user(self):
        """Override pour utiliser l'utilisateur fourni"""
        from core.database import AsyncSessionLocal
        from models.user import User
        from sqlalchemy import select
        
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.id == self._admin_user_id)
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erreur récupération utilisateur batch: {e}")
            return None