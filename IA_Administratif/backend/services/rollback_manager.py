"""
Service de gestion des rollbacks pour opérations batch
Gère les snapshots et la restauration d'état
"""

import os
import shutil
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from models.batch_operation import RollbackSnapshot, BatchOperation, BatchDocument
from core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


@dataclass
class FileSnapshot:
    """Snapshot d'un fichier individuel"""
    original_path: str
    backup_path: str
    file_hash: str
    size: int
    modified_time: float
    exists: bool


@dataclass
class DirectorySnapshot:
    """Snapshot d'un répertoire"""
    path: str
    files: List[FileSnapshot]
    subdirectories: List[str]
    permissions: str
    created: bool  # True si le dossier a été créé pendant l'opération


class RollbackManager:
    """
    Gestionnaire de rollback pour opérations batch
    
    Fonctionnalités :
    - Création de snapshots avant modifications
    - Sauvegarde incrémentale des changements
    - Restauration complète ou partielle
    - Nettoyage automatique des anciens snapshots
    """

    def __init__(self, backup_base_dir: str = "/tmp/lexo_backups"):
        self.backup_base_dir = Path(backup_base_dir)
        self.backup_base_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuration
        self.max_backup_age_days = 30
        self.max_backup_size_gb = 5.0
        
        logger.info(f"RollbackManager initialisé - Backups: {self.backup_base_dir}")

    async def create_snapshot(self, batch_id: int, paths_to_monitor: List[str]) -> str:
        """
        Crée un snapshot avant le début d'une opération batch
        
        Args:
            batch_id: ID de l'opération batch
            paths_to_monitor: Liste des chemins à surveiller
            
        Returns:
            ID unique du snapshot créé
        """
        snapshot_id = f"batch_{batch_id}_{uuid.uuid4().hex[:8]}"
        snapshot_dir = self.backup_base_dir / snapshot_id
        snapshot_dir.mkdir(exist_ok=True)
        
        try:
            logger.info(f"🔄 Création snapshot {snapshot_id} pour batch {batch_id}")
            
            # 1. Snapshot du système de fichiers
            filesystem_state = {}
            for path_str in paths_to_monitor:
                path = Path(path_str)
                if path.exists():
                    if path.is_file():
                        filesystem_state[path_str] = await self._snapshot_file(path, snapshot_dir)
                    elif path.is_dir():
                        filesystem_state[path_str] = await self._snapshot_directory(path, snapshot_dir)
                else:
                    # Marquer comme non-existant pour pouvoir le supprimer au rollback
                    filesystem_state[path_str] = {"exists": False, "type": "unknown"}
            
            # 2. Snapshot de l'état base de données
            database_state = await self._snapshot_database_state(batch_id)
            
            # 3. Sauvegarde du snapshot en base
            async with AsyncSessionLocal() as db:
                snapshot = RollbackSnapshot(
                    snapshot_id=snapshot_id,
                    batch_operation_id=batch_id,
                    snapshot_type="mixed",
                    filesystem_state=filesystem_state,
                    database_state=database_state,
                    expires_at=datetime.utcnow() + timedelta(days=self.max_backup_age_days)
                )
                
                db.add(snapshot)
                await db.commit()
            
            logger.success(f"✅ Snapshot {snapshot_id} créé avec succès")
            return snapshot_id
            
        except Exception as e:
            logger.error(f"❌ Erreur création snapshot {snapshot_id}: {e}")
            # Nettoyage en cas d'erreur
            if snapshot_dir.exists():
                shutil.rmtree(snapshot_dir, ignore_errors=True)
            raise

    async def _snapshot_file(self, file_path: Path, backup_dir: Path) -> Dict[str, Any]:
        """Crée un snapshot d'un fichier individuel"""
        try:
            # Calculer le hash du fichier
            file_hash = await self._calculate_file_hash(file_path)
            
            # Créer une sauvegarde physique
            backup_path = backup_dir / f"file_{file_hash[:8]}_{file_path.name}"
            shutil.copy2(file_path, backup_path)
            
            return {
                "type": "file",
                "exists": True,
                "original_path": str(file_path),
                "backup_path": str(backup_path),
                "hash": file_hash,
                "size": file_path.stat().st_size,
                "modified_time": file_path.stat().st_mtime,
                "permissions": oct(file_path.stat().st_mode)
            }
            
        except Exception as e:
            logger.warning(f"Erreur snapshot fichier {file_path}: {e}")
            return {"type": "file", "exists": True, "error": str(e)}

    async def _snapshot_directory(self, dir_path: Path, backup_dir: Path) -> Dict[str, Any]:
        """Crée un snapshot d'un répertoire"""
        try:
            files_snapshots = []
            subdirectories = []
            
            # Parcourir le contenu du répertoire
            for item in dir_path.iterdir():
                if item.is_file():
                    file_snapshot = await self._snapshot_file(item, backup_dir)
                    files_snapshots.append(file_snapshot)
                elif item.is_dir():
                    subdirectories.append(str(item))
                    # Récursion pour sous-dossiers (limitée à 3 niveaux)
                    if len(str(item).split(os.sep)) - len(str(dir_path).split(os.sep)) <= 3:
                        sub_snapshot = await self._snapshot_directory(item, backup_dir)
                        files_snapshots.extend(sub_snapshot.get("files", []))
            
            return {
                "type": "directory", 
                "exists": True,
                "original_path": str(dir_path),
                "files": files_snapshots,
                "subdirectories": subdirectories,
                "permissions": oct(dir_path.stat().st_mode),
                "created_during_batch": False  # Sera mis à jour pendant le traitement
            }
            
        except Exception as e:
            logger.warning(f"Erreur snapshot répertoire {dir_path}: {e}")
            return {"type": "directory", "exists": True, "error": str(e)}

    async def _snapshot_database_state(self, batch_id: int) -> Dict[str, Any]:
        """Crée un snapshot de l'état base de données avant le batch"""
        try:
            async with AsyncSessionLocal() as db:
                # Compter les documents par catégorie avant le batch
                # (pour pouvoir calculer les documents ajoutés)
                
                # Note: Dans une vraie implémentation, on pourrait sauvegarder
                # des IDs spécifiques ou faire un snapshot complet des tables affectées
                
                return {
                    "batch_id": batch_id,
                    "timestamp": datetime.utcnow().isoformat(),
                    "document_counts_before": {},  # À implémenter selon les besoins
                    "snapshot_method": "lightweight"  # ou "full" pour snapshot complet
                }
                
        except Exception as e:
            logger.warning(f"Erreur snapshot base de données: {e}")
            return {"error": str(e)}

    async def rollback_batch(self, batch_id: int, reason: str = "User requested") -> bool:
        """
        Effectue le rollback complet d'une opération batch
        
        Args:
            batch_id: ID de l'opération à annuler
            reason: Raison du rollback
            
        Returns:
            True si le rollback a réussi, False sinon
        """
        try:
            logger.info(f"🔄 Début rollback batch {batch_id} - Raison: {reason}")
            
            # 1. Récupérer le snapshot
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(RollbackSnapshot)
                    .where(RollbackSnapshot.batch_operation_id == batch_id)
                )
                snapshot = result.scalar_one_or_none()
                
                if not snapshot:
                    logger.error(f"Aucun snapshot trouvé pour batch {batch_id}")
                    return False
                
                # 2. Rollback du système de fichiers
                filesystem_success = await self._rollback_filesystem(snapshot.filesystem_state)
                
                # 3. Rollback de la base de données
                database_success = await self._rollback_database(snapshot.database_state, batch_id)
                
                # 4. Mettre à jour le statut du batch
                batch_result = await db.execute(
                    select(BatchOperation).where(BatchOperation.id == batch_id)
                )
                batch_op = batch_result.scalar_one_or_none()
                
                if batch_op:
                    batch_op.status = "rolled_back"
                    batch_op.rollback_reason = reason
                    batch_op.completed_at = datetime.utcnow()
                    batch_op.can_rollback = False
                    batch_op.add_log("INFO", f"Rollback effectué: {reason}")
                    
                    await db.commit()
                
                success = filesystem_success and database_success
                
                if success:
                    logger.success(f"✅ Rollback batch {batch_id} réussi")
                else:
                    logger.error(f"❌ Rollback batch {batch_id} partiellement échoué")
                
                return success
                
        except Exception as e:
            logger.error(f"❌ Erreur rollback batch {batch_id}: {e}")
            return False

    async def _rollback_filesystem(self, filesystem_state: Dict[str, Any]) -> bool:
        """Restaure l'état du système de fichiers"""
        try:
            for path_str, state in filesystem_state.items():
                path = Path(path_str)
                
                if state.get("error"):
                    continue  # Ignorer les éléments qui avaient des erreurs
                
                if not state.get("exists", False):
                    # Le fichier/dossier n'existait pas, le supprimer s'il existe maintenant
                    if path.exists():
                        if path.is_file():
                            path.unlink()
                            logger.debug(f"Supprimé fichier créé: {path}")
                        elif path.is_dir():
                            shutil.rmtree(path)
                            logger.debug(f"Supprimé dossier créé: {path}")
                else:
                    # Restaurer depuis la sauvegarde
                    if state["type"] == "file" and "backup_path" in state:
                        backup_path = Path(state["backup_path"])
                        if backup_path.exists():
                            # S'assurer que le dossier parent existe
                            path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(backup_path, path)
                            logger.debug(f"Restauré fichier: {path}")
                    elif state["type"] == "directory":
                        # Restaurer les fichiers du répertoire
                        for file_info in state.get("files", []):
                            if "backup_path" in file_info:
                                file_path = Path(file_info["original_path"])
                                backup_path = Path(file_info["backup_path"])
                                if backup_path.exists():
                                    file_path.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy2(backup_path, file_path)
                                    logger.debug(f"Restauré fichier: {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur rollback filesystem: {e}")
            return False

    async def _rollback_database(self, database_state: Dict[str, Any], batch_id: int) -> bool:
        """Restaure l'état de la base de données"""
        try:
            async with AsyncSessionLocal() as db:
                # Supprimer tous les documents créés pendant ce batch
                result = await db.execute(
                    select(BatchDocument).where(BatchDocument.batch_operation_id == batch_id)
                )
                batch_documents = result.scalars().all()
                
                for batch_doc in batch_documents:
                    if batch_doc.document_id:
                        # Supprimer le document principal
                        await db.execute(
                            delete(Document).where(Document.id == batch_doc.document_id)
                        )
                        logger.debug(f"Supprimé document {batch_doc.document_id}")
                
                await db.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erreur rollback database: {e}")
            return False

    async def cleanup_old_snapshots(self):
        """Nettoie les anciens snapshots expirés"""
        try:
            async with AsyncSessionLocal() as db:
                # Trouver les snapshots expirés
                expired_snapshots = await db.execute(
                    select(RollbackSnapshot)
                    .where(RollbackSnapshot.expires_at < datetime.utcnow())
                    .where(RollbackSnapshot.auto_cleanup == True)
                )
                
                for snapshot in expired_snapshots.scalars():
                    # Supprimer les fichiers de backup
                    snapshot_dir = self.backup_base_dir / snapshot.snapshot_id
                    if snapshot_dir.exists():
                        shutil.rmtree(snapshot_dir, ignore_errors=True)
                    
                    # Supprimer l'enregistrement
                    await db.delete(snapshot)
                    logger.debug(f"Nettoyé snapshot expiré: {snapshot.snapshot_id}")
                
                await db.commit()
                
        except Exception as e:
            logger.warning(f"Erreur nettoyage snapshots: {e}")

    async def _calculate_file_hash(self, file_path: Path) -> str:
        """Calcule le hash SHA-256 d'un fichier"""
        hash_sha256 = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except Exception:
            return "hash_error"

    async def get_snapshot_info(self, batch_id: int) -> Optional[Dict[str, Any]]:
        """Récupère les informations d'un snapshot"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(RollbackSnapshot)
                    .where(RollbackSnapshot.batch_operation_id == batch_id)
                )
                snapshot = result.scalar_one_or_none()
                
                if not snapshot:
                    return None
                
                snapshot_dir = self.backup_base_dir / snapshot.snapshot_id
                backup_size = 0
                if snapshot_dir.exists():
                    backup_size = sum(f.stat().st_size for f in snapshot_dir.rglob('*') if f.is_file())
                
                return {
                    "snapshot_id": snapshot.snapshot_id,
                    "created_at": snapshot.created_at,
                    "expires_at": snapshot.expires_at,
                    "backup_size_mb": backup_size / (1024 * 1024),
                    "can_rollback": not snapshot.is_expired,
                    "filesystem_paths": list(snapshot.filesystem_state.keys()),
                }
                
        except Exception as e:
            logger.error(f"Erreur récupération info snapshot: {e}")
            return None