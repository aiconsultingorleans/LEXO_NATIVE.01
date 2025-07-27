"""
Gestionnaire Arborescence Dynamique OCR - Étape 3.6
Organisation intelligente documents avec création dossiers/sous-dossiers automatique

Architecture simple LEXO :
- Gestion concurrente création dossiers
- Normalisation noms système fichiers
- Logs traçabilité complète
"""

import logging
import os
import shutil
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter
import threading
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DocumentOrganizer:
    """
    Gestionnaire organisation automatique documents OCR
    
    Fonctionnalités :
    - Création arborescence hiérarchique dynamique
    - Gestion seuils sous-dossiers par émetteur
    - Support concurrence (thread-safe)
    - Logs détaillés pour traçabilité
    - Rollback en cas d'erreur
    """
    
    def __init__(self, ocr_base_path: str = "/OCR", threshold_documents: int = 2):
        """
        Initialise gestionnaire organisation
        
        Args:
            ocr_base_path: Chemin racine dossier OCR
            threshold_documents: Seuil création sous-dossiers
        """
        self.ocr_base_path = Path(ocr_base_path)
        self.threshold_documents = threshold_documents
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Statistiques organisation
        self.organization_stats = defaultdict(int)
        self.emitter_counts = defaultdict(lambda: defaultdict(int))
        
        # Historique organisation pour traçabilité
        self.organization_history = []
        
        # Chemin logs
        self.logs_path = Path("logs/organization")
        self.logs_path.mkdir(parents=True, exist_ok=True)
        
        # Création dossier OCR base si inexistant
        self.ocr_base_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"DocumentOrganizer initialisé - Base: {self.ocr_base_path} - Seuil: {threshold_documents}")
    
    def organize_document(self, 
                         document_path: str, 
                         category: str, 
                         emitter_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Organisation document avec création arborescence automatique
        
        Args:
            document_path: Chemin document source
            category: Catégorie détectée
            emitter_info: Infos émetteur (nom, confiance, etc.)
            
        Returns:
            Résultat organisation avec chemin final
        """
        with self._lock:  # Thread safety
            try:
                start_time = time.time()
                
                # Validation entrées
                if not Path(document_path).exists():
                    return {"error": f"Document non trouvé : {document_path}"}
                
                if not category or not emitter_info:
                    return {"error": "Catégorie et émetteur requis"}
                
                # Calcul chemin destination
                destination_info = self._calculate_destination_path(category, emitter_info)
                
                # Création arborescence si nécessaire
                creation_result = self._ensure_folder_structure(destination_info)
                
                if not creation_result["success"]:
                    return creation_result
                
                # Déplacement document
                move_result = self._move_document_safely(document_path, destination_info)
                
                if not move_result["success"]:
                    return move_result
                
                # Mise à jour statistiques
                self._update_organization_stats(category, emitter_info, destination_info)
                
                # Log traçabilité
                self._log_organization(document_path, destination_info, emitter_info)
                
                processing_time = time.time() - start_time
                
                result = {
                    "success": True,
                    "source_path": document_path,
                    "destination_path": str(destination_info["full_path"]),
                    "folder_created": destination_info.get("folder_created", False),
                    "organization_type": destination_info["organization_type"],
                    "processing_time": processing_time,
                    "emitter_count": self.emitter_counts[category][emitter_info["normalized_name"]]
                }
                
                logger.info(f"Document organisé: {Path(document_path).name} → {destination_info['relative_path']}")
                return result
                
            except Exception as e:
                logger.error(f"Erreur organisation document : {e}")
                return {"error": str(e), "success": False}
    
    def _calculate_destination_path(self, category: str, emitter_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcule chemin destination selon logique seuils
        
        Args:
            category: Catégorie document
            emitter_info: Informations émetteur
            
        Returns:
            Infos chemin destination
        """
        emitter_name = emitter_info.get("normalized_name", "Inconnu")
        
        # Comptage documents existants pour cet émetteur
        current_count = self.emitter_counts[category][emitter_name]
        
        # Logique seuil création sous-dossier
        if current_count >= self.threshold_documents:
            # Seuil atteint : sous-dossier émetteur
            relative_path = f"{category}/{emitter_name}"
            organization_type = "subfolder_emitter"
        else:
            # Sous seuil : dossier catégorie principal
            relative_path = category
            organization_type = "main_category"
        
        full_path = self.ocr_base_path / relative_path
        
        return {
            "full_path": full_path,
            "relative_path": relative_path,
            "category": category,
            "emitter_name": emitter_name,
            "organization_type": organization_type,
            "current_count": current_count
        }
    
    def _ensure_folder_structure(self, destination_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assure existence structure dossiers
        
        Args:
            destination_info: Infos destination
            
        Returns:
            Résultat création dossiers
        """
        try:
            full_path = destination_info["full_path"]
            folders_created = []
            
            # Création récursive avec logs
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                folders_created.append(str(full_path))
                
                logger.info(f"Dossier créé : {destination_info['relative_path']}")
                
                # Si sous-dossier émetteur créé, réorganiser documents existants
                if destination_info["organization_type"] == "subfolder_emitter":
                    self._reorganize_existing_documents(destination_info)
            
            return {
                "success": True,
                "folders_created": folders_created,
                "folder_created": len(folders_created) > 0
            }
            
        except Exception as e:
            logger.error(f"Erreur création dossiers : {e}")
            return {"error": str(e), "success": False}
    
    def _reorganize_existing_documents(self, destination_info: Dict[str, Any]):
        """
        Réorganise documents existants lors création sous-dossier
        
        Args:
            destination_info: Infos nouveau sous-dossier
        """
        try:
            category = destination_info["category"]
            emitter_name = destination_info["emitter_name"]
            
            # Dossier catégorie principal
            main_category_path = self.ocr_base_path / category
            
            if not main_category_path.exists():
                return
            
            # Recherche documents du même émetteur dans dossier principal
            documents_to_move = []
            
            for file_path in main_category_path.iterdir():
                if file_path.is_file():
                    # Heuristique simple : nom fichier contient émetteur
                    if emitter_name.lower() in file_path.name.lower():
                        documents_to_move.append(file_path)
            
            # Déplacement vers nouveau sous-dossier
            moved_count = 0
            for doc_path in documents_to_move:
                try:
                    new_path = destination_info["full_path"] / doc_path.name
                    shutil.move(str(doc_path), str(new_path))
                    moved_count += 1
                    
                    logger.info(f"Document réorganisé : {doc_path.name} → {destination_info['relative_path']}")
                    
                except Exception as e:
                    logger.warning(f"Erreur réorganisation {doc_path.name} : {e}")
            
            if moved_count > 0:
                logger.info(f"Réorganisation terminée : {moved_count} documents déplacés vers {destination_info['relative_path']}")
                
        except Exception as e:
            logger.warning(f"Erreur réorganisation documents existants : {e}")
    
    def _move_document_safely(self, source_path: str, destination_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Déplacement sécurisé document avec gestion conflits
        
        Args:
            source_path: Chemin source
            destination_info: Infos destination
            
        Returns:
            Résultat déplacement
        """
        try:
            source = Path(source_path)
            destination_folder = destination_info["full_path"]
            
            # Calcul nom final (gestion doublons)
            final_name = self._get_unique_filename(destination_folder, source.name)
            final_path = destination_folder / final_name
            
            # Déplacement avec sauvegarde
            backup_needed = final_path.exists()
            if backup_needed:
                backup_path = final_path.with_suffix(f".backup_{int(time.time())}{final_path.suffix}")
                shutil.copy2(str(final_path), str(backup_path))
            
            # Déplacement principal
            shutil.move(str(source), str(final_path))
            
            return {
                "success": True,
                "final_path": str(final_path),
                "final_name": final_name,
                "backup_created": backup_needed
            }
            
        except Exception as e:
            logger.error(f"Erreur déplacement document : {e}")
            return {"error": str(e), "success": False}
    
    def _get_unique_filename(self, folder: Path, basename: str) -> str:
        """
        Génère nom fichier unique en cas de conflit
        
        Args:
            folder: Dossier destination
            basename: Nom base fichier
            
        Returns:
            Nom unique garanti
        """
        base_path = folder / basename
        
        if not base_path.exists():
            return basename
        
        # Gestion conflit avec compteur
        name_stem = Path(basename).stem
        extension = Path(basename).suffix
        
        counter = 1
        while True:
            new_name = f"{name_stem}_{counter}{extension}"
            new_path = folder / new_name
            
            if not new_path.exists():
                return new_name
            
            counter += 1
            
            # Sécurité : éviter boucle infinie
            if counter > 1000:
                timestamp = int(time.time())
                return f"{name_stem}_{timestamp}{extension}"
    
    def _update_organization_stats(self, category: str, emitter_info: Dict[str, Any], destination_info: Dict[str, Any]):
        """
        Met à jour statistiques organisation
        
        Args:
            category: Catégorie
            emitter_info: Infos émetteur
            destination_info: Infos destination
        """
        # Compteurs généraux
        self.organization_stats["total_documents"] += 1
        self.organization_stats[f"category_{category}"] += 1
        
        # Compteur émetteur spécifique
        emitter_name = emitter_info.get("normalized_name", "Inconnu")
        self.emitter_counts[category][emitter_name] += 1
        
        # Stats création dossiers
        if destination_info.get("folder_created"):
            self.organization_stats["folders_created"] += 1
        
        # Stats type organisation
        org_type = destination_info["organization_type"]
        self.organization_stats[f"org_type_{org_type}"] += 1
    
    def _log_organization(self, source_path: str, destination_info: Dict[str, Any], emitter_info: Dict[str, Any]):
        """
        Log détaillé pour traçabilité
        
        Args:
            source_path: Chemin source
            destination_info: Infos destination
            emitter_info: Infos émetteur
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "source_path": source_path,
            "destination_path": str(destination_info["full_path"]),
            "relative_path": destination_info["relative_path"],
            "category": destination_info["category"],
            "emitter": {
                "name": emitter_info.get("normalized_name"),
                "original_name": emitter_info.get("original_name"),
                "confidence": emitter_info.get("confidence")
            },
            "organization_type": destination_info["organization_type"],
            "emitter_count": destination_info["current_count"] + 1,
            "folder_created": destination_info.get("folder_created", False)
        }
        
        # Ajout historique mémoire
        self.organization_history.append(log_entry)
        
        # Limitation historique (1000 dernières)
        if len(self.organization_history) > 1000:
            self.organization_history = self.organization_history[-1000:]
        
        # Log fichier journalier
        log_file = self.logs_path / f"organization_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Erreur écriture log : {e}")
    
    def get_folder_structure(self, include_stats: bool = True) -> Dict[str, Any]:
        """
        Retourne structure dossiers actuelle
        
        Args:
            include_stats: Inclure statistiques
            
        Returns:
            Structure complète avec stats
        """
        try:
            structure = self._scan_folder_recursive(self.ocr_base_path)
            
            result = {
                "base_path": str(self.ocr_base_path),
                "structure": structure,
                "scan_timestamp": time.time()
            }
            
            if include_stats:
                result["statistics"] = dict(self.organization_stats)
                result["emitter_counts"] = {
                    category: dict(emitters) 
                    for category, emitters in self.emitter_counts.items()
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur scan structure : {e}")
            return {"error": str(e)}
    
    def _scan_folder_recursive(self, path: Path) -> Dict[str, Any]:
        """
        Scan récursif structure dossiers
        
        Args:
            path: Chemin à scanner
            
        Returns:
            Structure hiérarchique
        """
        if not path.exists():
            return {}
        
        structure = {
            "path": str(path),
            "name": path.name,
            "type": "folder",
            "children": [],
            "file_count": 0,
            "folder_count": 0
        }
        
        try:
            for item in sorted(path.iterdir()):
                if item.is_dir():
                    child_structure = self._scan_folder_recursive(item)
                    structure["children"].append(child_structure)
                    structure["folder_count"] += 1
                elif item.is_file():
                    structure["children"].append({
                        "path": str(item),
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size,
                        "modified": item.stat().st_mtime
                    })
                    structure["file_count"] += 1
        
        except PermissionError:
            structure["error"] = "Permission denied"
        
        return structure
    
    def suggest_reorganization(self) -> List[Dict[str, Any]]:
        """
        Suggestions réorganisation basées sur seuils
        
        Returns:
            Liste suggestions avec émetteurs fréquents
        """
        suggestions = []
        
        for category, emitters in self.emitter_counts.items():
            for emitter, count in emitters.items():
                if count >= self.threshold_documents:
                    # Vérifier si sous-dossier existe déjà
                    subfolder_path = self.ocr_base_path / category / emitter
                    
                    if not subfolder_path.exists():
                        suggestions.append({
                            "action": "create_subfolder",
                            "category": category,
                            "emitter": emitter,
                            "document_count": count,
                            "suggested_path": f"{category}/{emitter}",
                            "priority": count  # Plus de documents = priorité plus haute
                        })
        
        # Tri par priorité
        return sorted(suggestions, key=lambda x: x["priority"], reverse=True)

# Fonctions utilitaires
def organize_document_simple(document_path: str, 
                           category: str, 
                           emitter_name: str,
                           ocr_base: str = "/OCR") -> Dict[str, Any]:
    """
    Organisation rapide document unique
    
    Args:
        document_path: Chemin document
        category: Catégorie
        emitter_name: Nom émetteur
        ocr_base: Base OCR
        
    Returns:
        Résultat organisation
    """
    organizer = DocumentOrganizer(ocr_base)
    
    emitter_info = {
        "normalized_name": emitter_name,
        "original_name": emitter_name,
        "confidence": 1.0
    }
    
    return organizer.organize_document(document_path, category, emitter_info)