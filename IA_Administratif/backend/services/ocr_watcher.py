"""
Service de surveillance automatique du dossier OCR
Surveille ~/Documents/LEXO_v1/OCR et déclenche automatiquement le traitement OCR
"""

import asyncio
import logging
import time
import os
from pathlib import Path
from typing import Dict, Set, Optional
from datetime import datetime
import threading
import tempfile

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from pdf2image import convert_from_path
from PIL import Image

from core.database import AsyncSessionLocal
from models.document import Document
from models.user import User
from ocr.hybrid_ocr import HybridOCREngine, OCRStrategy
from ocr.entity_extractor import EntityExtractor 
from services.document_classifier import get_document_classifier
from sqlalchemy import select

logger = logging.getLogger(__name__)


class OCRFileHandler(FileSystemEventHandler):
    """Gestionnaire d'événements pour les fichiers OCR"""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}
    PROCESSING_DELAY = 2.0  # Attendre 2s pour éviter les fichiers en cours d'écriture
    
    def __init__(self):
        super().__init__()
        self.ocr_engine = HybridOCREngine()
        self.entity_extractor = EntityExtractor()
        self.processing_files: Set[str] = set()
        self.file_timestamps: Dict[str, float] = {}
        
    def on_created(self, event):
        """Déclenché quand un nouveau fichier est créé"""
        if not event.is_directory:
            self._schedule_processing(event.src_path)
    
    def on_modified(self, event):
        """Déclenché quand un fichier est modifié"""
        if not event.is_directory:
            self._schedule_processing(event.src_path)
    
    def _schedule_processing(self, file_path: str):
        """Planifie le traitement d'un fichier avec délai"""
        file_path = Path(file_path).resolve()
        
        # Vérifier l'extension
        if file_path.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            logger.debug(f"Extension non supportée ignorée: {file_path}")
            return
            
        # Éviter les doublons
        if str(file_path) in self.processing_files:
            logger.debug(f"Fichier déjà en cours de traitement: {file_path.name}")
            return
            
        # Mettre à jour le timestamp
        self.file_timestamps[str(file_path)] = time.time()
        
        logger.info(f"📄 Nouveau fichier détecté: {file_path.name}")
        
        # Programmer le traitement avec délai
        threading.Timer(
            self.PROCESSING_DELAY, 
            self._process_file_async, 
            args=[file_path]
        ).start()
    
    def _process_file_async(self, file_path: Path):
        """Lance le traitement asynchrone d'un fichier"""
        # Vérifier si le fichier a été modifié récemment
        current_time = time.time()
        file_key = str(file_path)
        
        if file_key in self.file_timestamps:
            if current_time - self.file_timestamps[file_key] < self.PROCESSING_DELAY - 0.1:
                # Fichier modifié récemment, reprogrammer
                threading.Timer(
                    self.PROCESSING_DELAY, 
                    self._process_file_async, 
                    args=[file_path]
                ).start()
                return
        
        # Démarrer une nouvelle boucle d'événements pour l'async
        asyncio.run(self._process_file(file_path))
    
    async def _process_file(self, file_path: Path):
        """Traite un fichier avec OCR et sauvegarde en base"""
        file_key = str(file_path)
        
        try:
            # Marquer comme en cours de traitement
            self.processing_files.add(file_key)
            
            # Vérifier que le fichier existe encore
            if not file_path.exists():
                logger.warning(f"Fichier supprimé avant traitement: {file_path.name}")
                return
                
            # Obtenir les informations du fichier
            file_size = file_path.stat().st_size
            mime_type = self._get_mime_type(file_path)
            
            logger.info(f"🔍 Traitement OCR: {file_path.name} ({file_size:,} bytes)")
            start_time = time.time()
            
            # Conversion PDF vers image si nécessaire
            processing_path = str(file_path)
            temp_image_path = None
            
            if file_path.suffix.lower() == '.pdf':
                try:
                    # Convertir la première page du PDF en image
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                        temp_image_path = temp_file.name
                    
                    images = convert_from_path(str(file_path), first_page=1, last_page=1)
                    if images:
                        images[0].save(temp_image_path, 'PNG')
                        processing_path = temp_image_path
                        logger.info(f"📄 PDF converti en image: {temp_image_path}")
                    else:
                        logger.error(f"Échec conversion PDF: {file_path.name}")
                        return
                        
                except Exception as e:
                    logger.error(f"Erreur conversion PDF {file_path.name}: {e}")
                    return
            
            try:
                # Traitement OCR (méthode synchrone)
                ocr_result = self.ocr_engine.extract_text(
                    processing_path,
                    strategy=OCRStrategy.TROCR_FALLBACK
                )
            finally:
                # Nettoyer le fichier temporaire
                if temp_image_path and Path(temp_image_path).exists():
                    Path(temp_image_path).unlink()
                    logger.debug(f"Fichier temporaire supprimé: {temp_image_path}")
            
            # Extraction d'entités
            entities = []
            if hasattr(ocr_result, 'text') and ocr_result.text:
                try:
                    entities = await self.entity_extractor.extract_entities(ocr_result.text)
                except Exception as e:
                    logger.warning(f"Extraction d'entités échouée: {e}")
            
            # ÉTAPE 1: Analyse Mistral pour enrichir la classification
            ocr_text = getattr(ocr_result, 'text', str(ocr_result))
            mistral_analysis = None
            mistral_category_suggestion = None
            
            if ocr_text and len(ocr_text.strip()) > 50:
                try:
                    mistral_analysis = await self._get_mistral_analysis(ocr_text)
                    if mistral_analysis and mistral_analysis.get('success'):
                        result_data = mistral_analysis.get('result', {})
                        mistral_category_suggestion = result_data.get('document_type')
                        logger.info(f"🤖 Analyse Mistral: type={mistral_category_suggestion}, confiance={result_data.get('confidence', 0)}")
                except Exception as e:
                    logger.warning(f"Analyse Mistral échouée: {e}")
            
            # ÉTAPE 2: Classification hybride (règles + Mistral)
            classifier = get_document_classifier()
            classification_result = classifier.classify_document(
                filename=file_path.name,
                ocr_text=ocr_text,
                entities=entities
            )
            
            # Affiner la classification avec l'analyse Mistral
            final_category = classification_result.category
            final_confidence = classification_result.confidence
            
            if mistral_category_suggestion and mistral_analysis:
                mistral_confidence = mistral_analysis.get('result', {}).get('confidence', 0)
                # Mapping des types Mistral vers nos catégories
                mistral_to_our_categories = {
                    'facture': 'factures',
                    'rib': 'rib', 
                    'contrat': 'contrats',
                    'attestation': 'attestations',
                    'courrier': 'courriers',
                    'rapport': 'non_classes',
                    'autre': 'non_classes'
                }
                
                mistral_mapped_category = mistral_to_our_categories.get(mistral_category_suggestion, 'non_classes')
                
                # Si Mistral est très confiant et différent, privilégier Mistral
                if mistral_confidence > 0.8 and mistral_mapped_category != final_category:
                    logger.info(f"🔄 Classification ajustée: {final_category} → {mistral_mapped_category} (Mistral confiance: {mistral_confidence:.2f})")
                    final_category = mistral_mapped_category
                    final_confidence = min(0.95, (final_confidence + mistral_confidence) / 2)
                # Si même catégorie, booster la confiance
                elif mistral_mapped_category == final_category:
                    final_confidence = min(0.98, final_confidence * 1.2)
            
            # Log du raisonnement de classification
            logger.info(f"🏷️ Classification finale: {final_category} (confiance: {final_confidence:.2f})")
            logger.info(f"   📋 Raisonnement: {classification_result.reasoning}")
            if classification_result.matched_rules:
                logger.info(f"   🎯 Règles: {', '.join(classification_result.matched_rules[:3])}")
            
            # ÉTAPE 3: Génération de résumé Mistral optimisé
            summary = ""
            if mistral_analysis and mistral_analysis.get('success'):
                result_data = mistral_analysis.get('result', {})
                summary = result_data.get('summary', '').strip()
                
                if not summary or len(summary) < 10:
                    # Réessayer avec l'endpoint de résumé direct
                    try:
                        summary = await self._generate_mistral_summary(ocr_text, final_category)
                    except Exception as e:
                        logger.warning(f"Génération résumé Mistral échouée: {e}")
                        summary = f"Document de type {final_category} analysé. Contenu de {len(ocr_text.split())} mots traité automatiquement."
            else:
                # Fallback si pas d'analyse Mistral
                try:
                    summary = await self._generate_mistral_summary(ocr_text, final_category)
                except Exception as e:
                    logger.warning(f"Génération résumé Mistral échouée: {e}")
                    summary = f"Document de type {final_category} analysé. Contenu de {len(ocr_text.split())} mots traité automatiquement."
            
            # Récupérer l'utilisateur admin par défaut
            admin_user = await self._get_admin_user()
            if not admin_user:
                logger.error("Utilisateur admin non trouvé")
                return
            
            # Créer le document en base
            async with AsyncSessionLocal() as db:
                document = Document(
                    user_id=admin_user.id,
                    filename=file_path.name,
                    original_filename=file_path.name,
                    file_path=str(file_path),
                    file_size=file_size,
                    mime_type=mime_type,
                    category=final_category,
                    confidence_score=final_confidence,
                    ocr_text=getattr(ocr_result, 'text', str(ocr_result))[:10000],  # Limiter la taille
                    entities=entities,
                    custom_tags=[final_category],
                    summary=summary,
                    processed_at=datetime.utcnow()
                )
                
                db.add(document)
                await db.commit()
                
                process_time = time.time() - start_time
                
                logger.info(f"✅ Document traité et sauvé: {file_path.name}")
                logger.info(f"   📊 ID: {document.id} | Catégorie: {final_category}")
                logger.info(f"   🔍 Confiance: {document.confidence_score:.2f}")
                logger.info(f"   📝 Texte: {len(document.ocr_text)} chars")
                logger.info(f"   📄 Résumé: {len(summary)} chars")
                logger.info(f"   🏷️ Entités: {len(entities)} trouvées")
                logger.info(f"   ⏱️ Temps: {process_time:.2f}s")
                
                # Optionnel: déplacer le fichier vers un sous-dossier
                await self._move_to_category_folder(file_path, final_category)
                
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement {file_path.name}: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            # Nettoyer
            self.processing_files.discard(file_key)
            self.file_timestamps.pop(file_key, None)
    
    async def _get_admin_user(self) -> Optional[User]:
        """Récupère l'utilisateur admin par défaut"""
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(
                    select(User).where(User.email == 'admin@lexo.fr')
                )
                return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Erreur récupération admin: {e}")
            return None
    
    def _get_mime_type(self, file_path: Path) -> str:
        """Détermine le type MIME du fichier"""
        ext = file_path.suffix.lower()
        mime_types = {
            '.pdf': 'application/pdf',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.tiff': 'image/tiff',
            '.bmp': 'image/bmp'
        }
        return mime_types.get(ext, 'application/octet-stream')
    
    
    async def _move_to_category_folder(self, file_path: Path, category: str):
        """Déplace le fichier vers le dossier de catégorie approprié"""
        try:
            # Créer le dossier de catégorie s'il n'existe pas
            category_folder = file_path.parent / category
            category_folder.mkdir(exist_ok=True)
            
            # Destination
            destination = category_folder / file_path.name
            
            # Éviter les conflits de noms
            counter = 1
            original_destination = destination
            while destination.exists():
                stem = original_destination.stem
                suffix = original_destination.suffix
                destination = category_folder / f"{stem}_{counter}{suffix}"
                counter += 1
            
            # Déplacer le fichier
            file_path.rename(destination)
            logger.info(f"📁 Fichier déplacé vers: {category}/{destination.name}")
            
        except Exception as e:
            logger.warning(f"Échec du déplacement vers {category}: {e}")
    
    async def _get_mistral_analysis(self, text: str) -> dict:
        """Obtient l'analyse complète du document depuis Mistral"""
        try:
            import httpx
            
            # Limiter le texte pour éviter les prompts trop longs
            text_excerpt = text[:2000] if len(text) > 2000 else text
            
            # Appel à l'API Mistral locale (service document_analyzer)
            # Architecture native macOS
            mistral_host = "localhost"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"http://{mistral_host}:8004/analyze",
                    json={
                        "text": text_excerpt,
                        "analysis_types": ["classification", "summarization", "key_extraction"]
                    }
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Erreur API Mistral: {response.status_code}")
                    return {"success": False, "error": f"HTTP {response.status_code}"}
                    
        except Exception as e:
            logger.warning(f"Erreur connexion Mistral: {e}")
            return {"success": False, "error": str(e)}

    async def _generate_mistral_summary(self, text: str, category: str) -> str:
        """Génère un résumé du document avec Mistral"""
        try:
            import httpx
            
            # Préparer le prompt selon la catégorie
            category_prompts = {
                'factures': "Résume cette facture en mentionnant : le fournisseur, le montant total, la date, et les services/produits principaux.",
                'attestations': "Résume cette attestation en mentionnant : l'organisme émetteur, la personne concernée, la validité et l'objet de l'attestation.",
                'rib': "Résume ce RIB en mentionnant : la banque, le titulaire du compte, et les informations bancaires essentielles.",
                'impots': "Résume ce document fiscal en mentionnant : le type de document, l'année concernée, les montants principaux.",
                'courriers': "Résume ce courrier en mentionnant : l'expéditeur, le destinataire, le sujet principal et les actions requises.",
                'non_classes': "Fais un résumé concis de ce document en mentionnant les informations les plus importantes."
            }
            
            prompt = category_prompts.get(category, category_prompts['non_classes'])
            
            # Limiter le texte pour éviter les prompts trop longs
            text_excerpt = text[:2000] if len(text) > 2000 else text
            
            # Appel à l'API Mistral locale (service document_analyzer)
            # Architecture native macOS
            mistral_host = "localhost"
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Essayer d'abord l'endpoint /analyze
                response = await client.post(
                    f"http://{mistral_host}:8004/analyze",
                    json={
                        "text": text_excerpt,
                        "type": category,
                        "operation": "summarization"
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        # Chercher le résumé dans différents champs
                        summary = (result.get('result', {}).get('summary') or 
                                 result.get('analysis') or 
                                 result.get('summary', '')).strip()
                        
                        if summary and len(summary) > 10:
                            # Nettoyer et valider le résumé
                            summary = summary.replace('\n', ' ').strip()
                            if len(summary) > 500:
                                summary = summary[:497] + "..."
                            return summary
                
                # Fallback: créer un résumé simple basé sur le contenu
                logger.info(f"Mistral unavailable, generating basic summary for {category}")
                
                # Résumé basique selon la catégorie
                if category == 'factures' and 'eur' in text_excerpt.lower():
                    import re
                    amounts = re.findall(r'(\d+[,.]?\d*)\s*(?:eur|€)', text_excerpt.lower())
                    if amounts:
                        return f"Facture d'un montant de {amounts[0]} EUR détectée dans le document."
                elif category == 'attestations':
                    return f"Attestation officielle - Document certifiant des informations administratives."
                elif category == 'rib':
                    return f"Relevé d'identité bancaire contenant les coordonnées du compte."
                    
                return f"Document de type {category} analysé - {len(text_excerpt)} caractères de contenu."
                
        except Exception as e:
            logger.warning(f"Erreur génération résumé Mistral: {e}")
            # Fallback basique
            word_count = len(text.split())
            return f"Document {category} de {word_count} mots analysé automatiquement."


class OCRWatcherService:
    """Service principal de surveillance OCR"""
    
    def __init__(self, watch_path: str = "/Users/stephaneansel/Documents/LEXO_v1/OCR/En attente"):
        self.watch_path = Path(watch_path)
        self.observer = None
        self.event_handler = OCRFileHandler()
        
    def start(self):
        """Démarrer la surveillance"""
        if not self.watch_path.exists():
            logger.warning(f"Dossier de surveillance introuvable: {self.watch_path}")
            # Créer le dossier s'il n'existe pas
            self.watch_path.mkdir(parents=True, exist_ok=True)
            
        logger.info(f"🔍 Démarrage surveillance OCR: {self.watch_path}")
        
        self.observer = Observer()
        self.observer.schedule(
            self.event_handler, 
            str(self.watch_path), 
            recursive=False  # Surveiller seulement le dossier racine
        )
        self.observer.start()
        
        logger.info("✅ Service de surveillance OCR démarré")
        
    def stop(self):
        """Arrêter la surveillance"""
        if self.observer:
            logger.info("🛑 Arrêt du service de surveillance OCR...")
            self.observer.stop()
            self.observer.join()
            logger.info("✅ Service de surveillance OCR arrêté")
    
    def is_alive(self) -> bool:
        """Vérifier si le service est actif"""
        return self.observer and self.observer.is_alive()


# Instance globale du service
_watcher_service: Optional[OCRWatcherService] = None


def start_ocr_watcher(watch_path: str = "/Users/stephaneansel/Documents/LEXO_v1/OCR/En attente") -> OCRWatcherService:
    """Démarre le service de surveillance OCR"""
    global _watcher_service
    
    if _watcher_service and _watcher_service.is_alive():
        logger.info("Service de surveillance OCR déjà actif")
        return _watcher_service
    
    _watcher_service = OCRWatcherService(watch_path)
    _watcher_service.start()
    return _watcher_service


def stop_ocr_watcher():
    """Arrête le service de surveillance OCR"""
    global _watcher_service
    
    if _watcher_service:
        _watcher_service.stop()
        _watcher_service = None


def get_watcher_status() -> dict:
    """Retourne le statut du watcher"""
    global _watcher_service
    
    if _watcher_service and _watcher_service.is_alive():
        return {
            "status": "active",
            "watch_path": str(_watcher_service.watch_path),
            "processing_files": len(_watcher_service.event_handler.processing_files)
        }
    else:
        return {"status": "inactive"}