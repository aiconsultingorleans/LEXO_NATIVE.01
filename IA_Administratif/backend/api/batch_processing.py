"""
API pour le traitement par lot des fichiers OCR
Permet de traiter les fichiers existants non analysés avec suivi en temps réel
"""

import asyncio
import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
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

# Stockage en mémoire pour le suivi des progressions (en production, utiliser Redis)
batch_progress_store: Dict[int, Dict] = {}


@router.get("/api/v1/batch/scan-folder")
async def scan_ocr_folder(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Scanne le dossier OCR pour identifier les fichiers non traités"""
    
    ocr_folder = Path("/Users/stephaneansel/Documents/LEXO_v1/OCR/En attente")
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
    """Lance le traitement en arrière-plan des fichiers non traités avec suivi"""
    
    # Identifier les fichiers non traités
    scan_result = await scan_ocr_folder(current_user, db)
    unprocessed_files = scan_result["files"]
    
    if not unprocessed_files:
        return {
            "success": True,
            "message": "Aucun fichier à traiter",
            "count": 0
        }
    
    # Initialiser le suivi de progression
    batch_id = current_user.id  # Utiliser l'ID utilisateur comme batch ID
    batch_progress_store[batch_id] = {
        "status": "starting",
        "current": 0,
        "total": len(unprocessed_files),
        "start_time": time.time(),
        "current_file": None,
        "files_processed": [],
        "completion_time": None,
        "estimated_remaining": len(unprocessed_files) * 8  # 8s par fichier en moyenne
    }
    
    # Lancer le traitement en arrière-plan
    background_tasks.add_task(
        process_files_batch, 
        [f["path"] for f in unprocessed_files],
        current_user.id,
        batch_id
    )
    
    return {
        "success": True,
        "message": f"Traitement de {len(unprocessed_files)} fichiers lancé en arrière-plan",
        "count": len(unprocessed_files),
        "files": [f["name"] for f in unprocessed_files],
        "batch_id": batch_id
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


async def process_files_batch(file_paths: List[str], user_id: int, batch_id: int):
    """Traite une liste de fichiers en arrière-plan avec suivi de progression"""
    
    logger.info(f"🚀 Début traitement batch: {len(file_paths)} fichiers")
    
    # Créer un handler OCR temporaire
    ocr_handler = OCRFileHandler()
    
    # Forcer l'utilisateur admin pour le batch
    ocr_handler._admin_user_id = user_id
    
    batch_start_time = time.time()
    
    for i, file_path in enumerate(file_paths):
        try:
            file_path_obj = Path(file_path)
            filename = file_path_obj.name
            
            logger.info(f"📄 Traitement batch ({i+1}/{len(file_paths)}): {filename}")
            
            # Mettre à jour la progression
            if batch_id in batch_progress_store:
                current_time = time.time()
                elapsed_time = current_time - batch_start_time
                
                # Estimation temps restant basée sur performance actuelle
                if i > 0:
                    avg_time_per_file = elapsed_time / i
                    remaining_files = len(file_paths) - i
                    estimated_remaining = avg_time_per_file * remaining_files
                else:
                    estimated_remaining = (len(file_paths) - i) * 8  # 8s par défaut
                
                batch_progress_store[batch_id].update({
                    "status": "processing",
                    "current": i,
                    "current_file": filename,
                    "elapsed_time": elapsed_time,
                    "estimated_remaining": estimated_remaining
                })
            
            # Traitement du fichier
            file_start_time = time.time()
            await ocr_handler._process_file(file_path_obj)
            file_end_time = time.time()
            
            # Enregistrer le fichier traité
            if batch_id in batch_progress_store:
                batch_progress_store[batch_id]["files_processed"].append({
                    "filename": filename,
                    "processing_time": file_end_time - file_start_time,
                    "completed_at": file_end_time
                })
                
                # Mise à jour finale pour ce fichier
                batch_progress_store[batch_id]["current"] = i + 1
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement batch {file_path}: {e}")
            
            # Enregistrer l'erreur dans la progression
            if batch_id in batch_progress_store:
                batch_progress_store[batch_id]["files_processed"].append({
                    "filename": file_path_obj.name,
                    "error": str(e),
                    "completed_at": time.time()
                })
                batch_progress_store[batch_id]["current"] = i + 1
            continue
    
    # Finaliser la progression
    batch_end_time = time.time()
    total_time = batch_end_time - batch_start_time
    
    if batch_id in batch_progress_store:
        batch_progress_store[batch_id].update({
            "status": "completed",
            "current": len(file_paths),
            "current_file": None,
            "completion_time": total_time,
            "estimated_remaining": 0
        })
    
    logger.info(f"✅ Traitement batch terminé: {len(file_paths)} fichiers en {total_time:.1f}s")


@router.get("/api/v1/batch/progress/{batch_id}")
async def get_batch_progress(
    batch_id: int,
    current_user: User = Depends(get_current_user)
):
    """Retourne la progression d'un traitement batch"""
    
    # Vérifier que l'utilisateur demande sa propre progression
    if batch_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé à cette progression")
    
    if batch_id not in batch_progress_store:
        raise HTTPException(status_code=404, detail="Progression introuvable")
    
    progress_data = batch_progress_store[batch_id].copy()
    
    # Calculer des métriques additionnelles
    if progress_data["status"] in ["processing", "completed"]:
        current_time = time.time()
        elapsed_time = current_time - progress_data["start_time"]
        progress_data["elapsed_time"] = elapsed_time
        
        # Calculer le pourcentage
        if progress_data["total"] > 0:
            progress_data["percentage"] = (progress_data["current"] / progress_data["total"]) * 100
        else:
            progress_data["percentage"] = 0
    
    return progress_data


@router.get("/api/v1/batch/status")
async def get_batch_status():
    """Retourne le statut général des traitements en cours"""
    
    active_batches = [
        {
            "batch_id": batch_id,
            "status": data["status"],
            "current": data["current"],
            "total": data["total"],
            "start_time": data["start_time"]
        }
        for batch_id, data in batch_progress_store.items()
        if data["status"] in ["starting", "processing"]
    ]
    
    return {
        "active_tasks": len(active_batches),
        "active_batches": active_batches,
        "total_batches_in_memory": len(batch_progress_store)
    }


@router.delete("/api/v1/batch/progress/{batch_id}")
async def clear_batch_progress(
    batch_id: int,
    current_user: User = Depends(get_current_user)
):
    """Supprime les données de progression d'un batch terminé"""
    
    # Vérifier que l'utilisateur peut supprimer sa propre progression
    if batch_id != current_user.id:
        raise HTTPException(status_code=403, detail="Accès non autorisé")
    
    if batch_id in batch_progress_store:
        del batch_progress_store[batch_id]
        return {"success": True, "message": "Progression supprimée"}
    
    raise HTTPException(status_code=404, detail="Progression introuvable")


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