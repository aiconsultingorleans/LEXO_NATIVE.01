"""
Routes API pour le système OCR et prétraitement d'images
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.responses import FileResponse
from typing import List, Optional, Dict, Any
import tempfile
import shutil
import os
from pathlib import Path
import logging
import json
from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import des modules internes
from core.database import get_db
from api.auth import get_current_user
from models.user import User
from models.document import Document, DocumentCategory
from ocr.image_preprocessor import ImagePreprocessor, preprocess_for_ocr
from ocr.tesseract_ocr import TesseractOCR, OCRResult
# Imports avancés commentés temporairement à cause de dépendances manquantes dans Docker
from ocr.trocr_ocr import TrOCREngine, TrOCRConfig
from ocr.hybrid_ocr import HybridOCREngine, HybridOCRConfig, OCRStrategy
from ocr.layoutlm_ocr import LayoutLMEngine, LayoutLMConfig
from ocr.table_detector import TableDetector, TableDetectorConfig, TableDetectionMethod
from ocr.entity_extractor import EntityExtractor, extract_document_metadata
from ocr.apple_silicon_optimizer import AppleSiliconOCROptimizer
from ocr.ocr_cache import OCRCacheManager

logger = logging.getLogger(__name__)

# Initialisation du router
router = APIRouter(prefix="/api/v1/ocr", tags=["OCR"])

# Initialisation des modules OCR (lazy loading)
_hybrid_ocr_engine = None
_trocr_engine = None
_layoutlm_engine = None
_table_detector = None
_entity_extractor = None
_apple_optimizer = None
_cache_manager = None

def get_hybrid_ocr_engine():
    global _hybrid_ocr_engine
    if _hybrid_ocr_engine is None:
        config = HybridOCRConfig(strategy=OCRStrategy.TROCR_FALLBACK)
        _hybrid_ocr_engine = HybridOCREngine(config)
    return _hybrid_ocr_engine

def get_cache_manager():
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = OCRCacheManager({'type': 'hybrid'})
    return _cache_manager

# Schémas Pydantic
class ImagePreprocessingRequest(BaseModel):
    """Requête de prétraitement d'image"""
    apply_rotation_correction: bool = Field(default=True, description="Corriger la rotation automatiquement")
    apply_denoising: bool = Field(default=True, description="Appliquer le débruitage")
    crop_borders: bool = Field(default=True, description="Supprimer les bordures automatiquement")
    optimize_contrast: bool = Field(default=True, description="Optimiser le contraste")
    split_pages: bool = Field(default=True, description="Découper les pages multiples")


class ImagePreprocessingResponse(BaseModel):
    """Réponse de prétraitement d'image"""
    success: bool
    message: str
    processed_files: List[str] = Field(default_factory=list)
    quality_scores: List[float] = Field(default_factory=list)
    processing_time: float
    original_size: Dict[str, int] = Field(default_factory=dict)
    processed_sizes: List[Dict[str, int]] = Field(default_factory=list)


class OCRProcessingRequest(BaseModel):
    """Requête de traitement OCR complet"""
    document_id: Optional[str] = None
    category: Optional[DocumentCategory] = None
    preprocess: bool = Field(default=True, description="Appliquer le prétraitement")
    extract_entities: bool = Field(default=True, description="Extraire les entités")
    generate_summary: bool = Field(default=False, description="Générer un résumé")


class ZoneExtractionRequest(BaseModel):
    """Requête d'extraction OCR par zones"""
    zones: List[List[int]] = Field(description="Liste des zones [x, y, width, height]")
    lang: Optional[str] = Field(default=None, description="Langue spécifique pour l'OCR")
    preprocess: bool = Field(default=True, description="Appliquer le prétraitement")


class OCRProcessingResponse(BaseModel):
    """Réponse de traitement OCR"""
    success: bool
    message: str
    document_id: str
    extracted_text: str
    confidence_score: float
    detected_entities: Dict[str, Any] = Field(default_factory=dict)
    suggested_category: Optional[DocumentCategory] = None
    processing_time: float


class AdvancedOCRRequest(BaseModel):
    """Requête OCR avancée avec choix du moteur"""
    engine: str = Field(default="hybrid", description="Moteur OCR (tesseract, trocr, hybrid)")
    strategy: Optional[str] = Field(default="trocr_fallback", description="Stratégie pour moteur hybride")
    preprocess: bool = Field(default=True, description="Appliquer le prétraitement")
    extract_entities: bool = Field(default=True, description="Extraire les entités")
    detect_tables: bool = Field(default=False, description="Détecter les tableaux")
    analyze_structure: bool = Field(default=False, description="Analyser la structure (LayoutLM)")
    use_cache: bool = Field(default=True, description="Utiliser le cache")


class StructureAnalysisRequest(BaseModel):
    """Requête d'analyse de structure"""
    include_regions: bool = Field(default=True, description="Inclure les régions détectées")
    visualize: bool = Field(default=False, description="Générer une visualisation")


class TableDetectionRequest(BaseModel):
    """Requête de détection de tableaux"""
    method: str = Field(default="hybrid", description="Méthode de détection")
    min_table_area: Optional[int] = Field(default=1000, description="Aire minimale des tableaux")
    extract_content: bool = Field(default=True, description="Extraire le contenu des tableaux")


class EntityExtractionRequest(BaseModel):
    """Requête d'extraction d'entités"""
    entity_types: Optional[List[str]] = Field(default=None, description="Types d'entités à extraire")
    include_context: bool = Field(default=True, description="Inclure le contexte")
    normalize_values: bool = Field(default=True, description="Normaliser les valeurs")


class AdvancedOCRResponse(BaseModel):
    """Réponse OCR avancée"""
    success: bool
    message: str
    document_id: Optional[str] = None
    engine_used: str
    extracted_text: str
    confidence_score: float
    processing_time: float
    detected_entities: Dict[str, Any] = Field(default_factory=dict)
    detected_tables: List[Dict[str, Any]] = Field(default_factory=list)
    structure_regions: List[Dict[str, Any]] = Field(default_factory=list)
    cache_used: bool = False
    apple_silicon_optimized: bool = False


# Endpoints

@router.post("/preprocess", response_model=ImagePreprocessingResponse)
async def preprocess_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Image à prétraiter"),
    request: ImagePreprocessingRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Prétraite une image pour améliorer la qualité OCR
    
    - **file**: Image à prétraiter (PNG, JPG, TIFF)
    - **request**: Options de prétraitement
    
    Retourne les images prétraitées avec métriques de qualité
    """
    start_time = datetime.now()
    
    try:
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        # Vérification du format
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp'}:
            raise HTTPException(
                status_code=400, 
                detail=f"Format non supporté: {file_extension}. Formats acceptés: PNG, JPG, TIFF, BMP"
            )
        
        # Sauvegarde temporaire du fichier
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_input_path = tmp_file.name
        
        try:
            # Initialisation du préprocesseur
            preprocessor = ImagePreprocessor()
            
            # Chargement et analyse de l'image originale
            original_image = preprocessor.load_image(temp_input_path)
            original_size = {
                "width": original_image.shape[1],
                "height": original_image.shape[0],
                "channels": original_image.shape[2] if len(original_image.shape) > 2 else 1
            }
            
            logger.info(f"Image chargée: {file.filename}, taille: {original_size}")
            
            # Configuration du prétraitement selon les options
            processed_image = original_image.copy()
            
            if request.apply_rotation_correction:
                processed_image = preprocessor.correct_rotation(processed_image)
                logger.debug("Correction de rotation appliquée")
            
            if request.apply_denoising:
                processed_image = preprocessor.denoise_image(processed_image)
                logger.debug("Débruitage appliqué")
            
            if request.crop_borders:
                processed_image = preprocessor.detect_and_crop_borders(processed_image)
                logger.debug("Bordures supprimées")
            
            if request.optimize_contrast:
                processed_image = preprocessor.optimize_contrast_brightness(processed_image)
                logger.debug("Contraste optimisé")
            
            # Découpage en pages si demandé
            if request.split_pages:
                pages = preprocessor.split_pages(processed_image)
                logger.info(f"Pages détectées: {len(pages)}")
            else:
                pages = [processed_image]
            
            # Création du dossier de sortie temporaire
            with tempfile.TemporaryDirectory() as temp_output_dir:
                processed_files = []
                quality_scores = []
                processed_sizes = []
                
                for i, page in enumerate(pages):
                    # Nom du fichier de sortie
                    if len(pages) > 1:
                        output_filename = f"{Path(file.filename).stem}_page{i+1}_processed{file_extension}"
                    else:
                        output_filename = f"{Path(file.filename).stem}_processed{file_extension}"
                    
                    output_path = Path(temp_output_dir) / output_filename
                    
                    # Sauvegarde de la page
                    import cv2
                    cv2.imwrite(str(output_path), page)
                    
                    # Calcul du score de qualité
                    quality_score = preprocessor.get_image_quality_score(page)
                    quality_scores.append(quality_score)
                    
                    # Taille de l'image traitée
                    processed_size = {
                        "width": page.shape[1],
                        "height": page.shape[0],
                        "channels": page.shape[2] if len(page.shape) > 2 else 1
                    }
                    processed_sizes.append(processed_size)
                    
                    processed_files.append(output_filename)
                    
                    logger.info(f"Page {i+1} traitée: {output_filename}, qualité: {quality_score:.3f}")
                
                # Calcul du temps de traitement
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # TODO: Ici on pourrait sauvegarder les fichiers dans un stockage permanent
                # et retourner des URLs ou des IDs pour les récupérer plus tard
                
                return ImagePreprocessingResponse(
                    success=True,
                    message=f"Prétraitement réussi: {len(pages)} page(s) traitée(s)",
                    processed_files=processed_files,
                    quality_scores=quality_scores,
                    processing_time=processing_time,
                    original_size=original_size,
                    processed_sizes=processed_sizes
                )
        
        finally:
            # Nettoyage du fichier temporaire
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
    
    except Exception as e:
        logger.error(f"Erreur lors du prétraitement de {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de prétraitement: {str(e)}")


@router.post("/process", response_model=OCRProcessingResponse)
async def process_document_ocr(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document à traiter"),
    request: OCRProcessingRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Traitement OCR complet d'un document
    
    - **file**: Document à analyser
    - **request**: Options de traitement OCR
    
    Effectue le prétraitement, l'OCR et l'extraction d'entités
    """
    start_time = datetime.now()
    
    try:
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        logger.info(f"Début traitement OCR pour: {file.filename} (utilisateur: {current_user.email})")
        
        # Sauvegarde temporaire du fichier
        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix.lower(), delete=False) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_input_path = tmp_file.name
        
        try:
            # Pipeline OCR complet
            ocr_result = None
            preprocessed_image = None
            
            # 1. Prétraitement si demandé
            if request.preprocess:
                logger.info("Application du prétraitement...")
                preprocessor = ImagePreprocessor()
                preprocessed_image = preprocessor.process_image(temp_input_path)
                
                # Sauvegarder l'image prétraitée temporairement
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as processed_tmp:
                    import cv2
                    cv2.imwrite(processed_tmp.name, preprocessed_image)
                    processed_path = processed_tmp.name
            else:
                processed_path = temp_input_path
            
            # 2. OCR avec Tesseract
            logger.info("Exécution OCR Tesseract...")
            tesseract_ocr = TesseractOCR()
            ocr_result = tesseract_ocr.extract_text(processed_path)
            
            # 3. Classification automatique basique
            suggested_category = DocumentCategory.NON_CLASSE
            
            # Heuristiques simples pour la classification
            text_lower = ocr_result.text.lower()
            if any(word in text_lower for word in ['facture', 'invoice', 'bill']):
                suggested_category = DocumentCategory.FACTURE
            elif any(word in text_lower for word in ['contrat', 'contract', 'accord']):
                suggested_category = DocumentCategory.CONTRAT
            elif any(word in text_lower for word in ['impôt', 'taxe', 'fiscal']):
                suggested_category = DocumentCategory.IMPOT
            elif any(word in text_lower for word in ['rib', 'iban', 'bank']):
                suggested_category = DocumentCategory.RIB
            
            logger.info(f"Classification suggérée: {suggested_category}")
            
            # 4. Analyse avancée avec Mistral MLX (si disponible)
            mistral_analysis = None
            mistral_category_suggestion = None
            summary = ""
            
            if ocr_result.text and len(ocr_result.text.strip()) > 50:
                try:
                    # Appel direct au service Mistral MLX natif
                    mistral_result = await _call_mistral_service_direct(ocr_result.text)
                    
                    if mistral_result.get('success'):
                        result_data = mistral_result.get('result', {})
                        mistral_category_suggestion = result_data.get('document_type')
                        summary = result_data.get('summary', '').strip()
                        
                        logger.info(f"🤖 Analyse Mistral: type={mistral_category_suggestion}, summary={len(summary)} chars")
                        
                        # Mapping des types Mistral vers nos catégories
                        mistral_to_our_categories = {
                            'facture': DocumentCategory.FACTURE,
                            'rib': DocumentCategory.RIB, 
                            'contrat': DocumentCategory.CONTRAT,
                            'attestation': DocumentCategory.ATTESTATION,
                            'courrier': DocumentCategory.COURRIER,
                            'rapport': DocumentCategory.NON_CLASSE,
                            'autre': DocumentCategory.NON_CLASSE
                        }
                        
                        mistral_mapped_category = mistral_to_our_categories.get(mistral_category_suggestion, DocumentCategory.NON_CLASSE)
                        
                        # Si Mistral est confiant, utiliser sa suggestion
                        mistral_confidence = result_data.get('confidence', 0)
                        if mistral_confidence > 0.7:
                            suggested_category = mistral_mapped_category
                            logger.info(f"🔄 Classification Mistral utilisée: {suggested_category} (confiance: {mistral_confidence:.2f})")
                        
                except Exception as e:
                    logger.warning(f"Analyse Mistral échouée: {e}")
            
            # 5. Classification hybride finale avec classification basée sur règles
            from services.document_classifier import get_document_classifier
            
            try:
                classifier = get_document_classifier()
                classification_result = classifier.classify_document(
                    filename=file.filename,
                    ocr_text=ocr_result.text,
                    entities=list(ocr_result.detected_entities.keys()) if ocr_result.detected_entities else []
                )
                
                final_category = classification_result.category
                final_confidence = classification_result.confidence
                
                # Combiner avec Mistral si disponible
                if mistral_category_suggestion:
                    # Booster la confiance si les deux méthodes s'accordent
                    if suggested_category == DocumentCategory(final_category):
                        final_confidence = min(0.98, final_confidence * 1.2)
                        logger.info(f"🎯 Accord classification: {final_category} (confiance boostée: {final_confidence:.2f})")
                
                suggested_category = DocumentCategory(final_category)
                
                logger.info(f"🏷️ Classification finale: {final_category} (confiance: {final_confidence:.2f})")
                logger.info(f"   📋 Raisonnement: {classification_result.reasoning}")
                
            except Exception as e:
                logger.warning(f"Classification par règles échouée: {e}")
                final_confidence = ocr_result.confidence
            
            # 6. Calcul de la taille du fichier
            file_size = os.path.getsize(temp_input_path)
            
            # 7. Sauvegarde en base avec toutes les informations
            document = Document(
                filename=file.filename,
                original_filename=file.filename,
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                user_id=current_user.id,
                category=request.category or suggested_category.value,
                ocr_text=ocr_result.text,
                confidence_score=final_confidence,
                entities=list(ocr_result.detected_entities.keys()) if ocr_result.detected_entities else [],
                custom_tags=[suggested_category.value],
                summary=summary if summary else f"Document {suggested_category.value} analysé automatiquement.",
                processed_at=datetime.utcnow()
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Temps de traitement total
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"OCR terminé: {ocr_result.word_count} mots, "
                       f"confiance: {ocr_result.confidence:.3f}, "
                       f"temps: {processing_time:.2f}s")
            
            return OCRProcessingResponse(
                success=True,
                message=f"OCR + IA réussi: {ocr_result.word_count} mots extraits, classification {suggested_category.value}",
                document_id=str(document.id),
                extracted_text=ocr_result.text,
                confidence_score=final_confidence,
                detected_entities=ocr_result.detected_entities,
                suggested_category=suggested_category,
                processing_time=processing_time
            )
            
        finally:
            # Nettoyage des fichiers temporaires
            for path in [temp_input_path, processed_path if 'processed_path' in locals() and processed_path != temp_input_path else None]:
                if path and os.path.exists(path):
                    os.unlink(path)
    
    except Exception as e:
        logger.error(f"Erreur lors du traitement OCR de {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de traitement OCR: {str(e)}")


@router.post("/extract-zones")
async def extract_text_from_zones(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Image à analyser par zones"),
    request: ZoneExtractionRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extrait le texte de zones spécifiques de l'image
    
    - **file**: Image à analyser
    - **zones**: Liste des zones [x, y, width, height]
    - **lang**: Langue pour l'OCR (auto-détection si non spécifiée)
    - **preprocess**: Appliquer le prétraitement
    
    Retourne le texte extrait pour chaque zone avec positions
    """
    start_time = datetime.now()
    
    try:
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        # Validation des zones
        if not request.zones:
            raise HTTPException(status_code=400, detail="Aucune zone spécifiée")
        
        for i, zone in enumerate(request.zones):
            if len(zone) != 4:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Zone {i+1} invalide: doit contenir [x, y, width, height]"
                )
            if any(coord < 0 for coord in zone):
                raise HTTPException(
                    status_code=400,
                    detail=f"Zone {i+1} invalide: coordonnées négatives"
                )
        
        logger.info(f"Extraction par zones pour: {file.filename} ({len(request.zones)} zones)")
        
        # Sauvegarde temporaire
        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix.lower(), delete=False) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_input_path = tmp_file.name
        
        try:
            # Prétraitement si demandé
            if request.preprocess:
                preprocessor = ImagePreprocessor()
                preprocessed_image = preprocessor.process_image(temp_input_path)
                
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as processed_tmp:
                    import cv2
                    cv2.imwrite(processed_tmp.name, preprocessed_image)
                    processed_path = processed_tmp.name
            else:
                processed_path = temp_input_path
            
            # Conversion des zones en tuples
            zones_tuples = [tuple(zone) for zone in request.zones]
            
            # Extraction OCR par zones
            tesseract_ocr = TesseractOCR()
            zone_results = tesseract_ocr.extract_text_from_zones(
                processed_path, 
                zones_tuples, 
                lang=request.lang
            )
            
            # Temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Formatage de la réponse
            zone_responses = []
            total_words = 0
            
            for i, result in enumerate(zone_results):
                zone_response = {
                    "zone_id": i + 1,
                    "zone_coords": request.zones[i],
                    "extracted_text": result.text,
                    "confidence": result.confidence,
                    "word_count": result.word_count,
                    "line_count": result.line_count,
                    "detected_entities": result.detected_entities,
                    "quality_metrics": result.quality_metrics
                }
                zone_responses.append(zone_response)
                total_words += result.word_count
            
            logger.info(f"Extraction zones terminée: {total_words} mots total, "
                       f"temps: {processing_time:.2f}s")
            
            return {
                "success": True,
                "message": f"Extraction réussie sur {len(request.zones)} zones",
                "total_zones": len(request.zones),
                "total_words": total_words,
                "processing_time": processing_time,
                "zones": zone_responses
            }
            
        finally:
            # Nettoyage
            for path in [temp_input_path, processed_path if 'processed_path' in locals() and processed_path != temp_input_path else None]:
                if path and os.path.exists(path):
                    os.unlink(path)
    
    except Exception as e:
        logger.error(f"Erreur extraction zones {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction: {str(e)}")


@router.get("/quality-check/{file_id}")
async def check_image_quality(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Vérifie la qualité d'une image pour OCR
    
    - **file_id**: ID du fichier à analyser
    
    Retourne un score de qualité et des recommandations
    """
    try:
        # TODO: Récupérer le fichier par son ID
        # document = db.query(Document).filter(Document.id == file_id).first()
        
        # Simulation pour l'instant
        quality_metrics = {
            "overall_score": 0.85,
            "sharpness": 0.90,
            "contrast": 0.80,
            "resolution": 0.85,
            "noise_level": 0.15,
            "recommendations": [
                "Qualité acceptable pour OCR",
                "Légère amélioration du contraste recommandée"
            ]
        }
        
        return {
            "success": True,
            "file_id": file_id,
            "quality_metrics": quality_metrics
        }
    
    except Exception as e:
        logger.error(f"Erreur lors de l'analyse qualité: {str(e)}")
        raise HTTPException(status_code=500, details=f"Erreur d'analyse: {str(e)}")


@router.post("/advanced", response_model=AdvancedOCRResponse)
async def advanced_ocr_processing(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Document à analyser"),
    request: AdvancedOCRRequest = Depends(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Traitement OCR avancé avec choix du moteur et fonctionnalités étendues
    
    - **file**: Document à analyser
    - **request**: Configuration avancée
    
    Utilise les derniers modèles (TrOCR, LayoutLM) avec cache intelligent
    """
    start_time = datetime.now()
    
    try:
        # Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        logger.info(f"OCR avancé démarré: {file.filename} (moteur: {request.engine})")
        
        # Sauvegarde temporaire
        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix.lower(), delete=False) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_input_path = tmp_file.name
        
        try:
            # Initialisation des composants
            cache_manager = get_cache_manager() if request.use_cache else None
            detected_tables = []
            structure_regions = []
            apple_silicon_optimized = False
            
            # Vérifier le cache si activé
            cache_used = False
            if cache_manager:
                cached_result = cache_manager.get_cached_result(
                    temp_input_path, 
                    request.engine, 
                    request.dict()
                )
                if cached_result:
                    cache_used = True
                    logger.info("Résultat trouvé dans le cache")
                    
                    return AdvancedOCRResponse(
                        success=True,
                        message="Résultat OCR récupéré du cache",
                        engine_used=request.engine,
                        extracted_text=cached_result.text,
                        confidence_score=cached_result.confidence,
                        processing_time=0.1,  # Temps de cache quasi-instantané
                        detected_entities=cached_result.detected_entities,
                        cache_used=True
                    )
            
            # Optimisation Apple Silicon
            apple_optimizer = AppleSiliconOCROptimizer()
            if apple_optimizer.chip_info["is_apple_silicon"]:
                apple_silicon_optimized = True
                logger.info("Optimisations Apple Silicon activées")
            
            # Sélection et exécution du moteur OCR
            ocr_result = None
            engine_used = request.engine
            
            if request.engine == "hybrid":
                # Moteur hybride
                hybrid_engine = get_hybrid_ocr_engine()
                
                # Mapper la stratégie
                strategy_map = {
                    "trocr_only": OCRStrategy.TROCR_ONLY,
                    "tesseract_only": OCRStrategy.TESSERACT_ONLY,
                    "trocr_fallback": OCRStrategy.TROCR_FALLBACK,
                    "best_confidence": OCRStrategy.BEST_CONFIDENCE,
                    "ensemble": OCRStrategy.ENSEMBLE
                }
                strategy = strategy_map.get(request.strategy, OCRStrategy.TROCR_FALLBACK)
                
                ocr_result = hybrid_engine.extract_text(temp_input_path, strategy=strategy)
                engine_used = f"hybrid_{request.strategy}"
                
            elif request.engine == "trocr":
                # TrOCR uniquement
                trocr_config = TrOCRConfig()
                trocr_engine = TrOCREngine(trocr_config)
                ocr_result = trocr_engine.extract_text(temp_input_path, preprocess=request.preprocess)
                
            elif request.engine == "tesseract":
                # Tesseract uniquement
                tesseract_engine = TesseractOCR()
                ocr_result = tesseract_engine.extract_text(temp_input_path, preprocess=request.preprocess)
                
            else:
                raise HTTPException(status_code=400, detail=f"Moteur OCR non supporté: {request.engine}")
            
            if not ocr_result:
                raise HTTPException(status_code=500, detail="Échec de l'extraction OCR")
            
            # Détection de tableaux si demandée
            if request.detect_tables:
                try:
                    table_config = TableDetectorConfig(detection_method=TableDetectionMethod.HYBRID)
                    table_detector = TableDetector(table_config)
                    tables = table_detector.detect_tables(temp_input_path, preprocess=request.preprocess)
                    
                    for table in tables:
                        detected_tables.append(table_detector.extract_table_as_dict(table))
                    
                    logger.info(f"Tableaux détectés: {len(detected_tables)}")
                    
                except Exception as e:
                    logger.error(f"Erreur détection tableaux: {e}")
            
            # Analyse de structure si demandée
            if request.analyze_structure:
                try:
                    layoutlm_config = LayoutLMConfig()
                    layoutlm_engine = LayoutLMEngine(layoutlm_config)
                    _, regions = layoutlm_engine.extract_structured_text(temp_input_path, preprocess=request.preprocess)
                    
                    for region in regions:
                        structure_regions.append({
                            "type": region.region_type.value,
                            "text": region.text,
                            "bbox": region.bbox,
                            "confidence": region.confidence
                        })
                    
                    logger.info(f"Régions structurées: {len(structure_regions)}")
                    
                except Exception as e:
                    logger.error(f"Erreur analyse structure: {e}")
            
            # Extraction d'entités avancée si demandée
            if request.extract_entities:
                try:
                    entity_extractor = EntityExtractor()
                    entity_result = entity_extractor.extract_entities(ocr_result.text)
                    
                    # Enrichir les entités détectées
                    enriched_entities = entity_extractor.get_structured_summary(entity_result)
                    ocr_result.detected_entities.update(enriched_entities['entities_by_type'])
                    
                except Exception as e:
                    logger.error(f"Erreur extraction entités: {e}")
            
            # Sauvegarde en base de données
            file_size = os.path.getsize(temp_input_path)
            document = Document(
                filename=file.filename,
                original_filename=file.filename,
                file_size=file_size,
                mime_type=file.content_type or "application/octet-stream",
                user_id=current_user.id,
                category=DocumentCategory.NON_CLASSE,  # Classification automatique plus tard
                ocr_text=ocr_result.text,
                confidence_score=ocr_result.confidence
            )
            
            db.add(document)
            db.commit()
            db.refresh(document)
            
            # Mise en cache du résultat
            if cache_manager:
                cache_manager.cache_result(
                    temp_input_path,
                    engine_used,
                    ocr_result,
                    request.dict()
                )
            
            # Temps de traitement total
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"OCR avancé terminé: {ocr_result.word_count} mots, "
                       f"confiance: {ocr_result.confidence:.3f}, "
                       f"temps: {processing_time:.2f}s")
            
            return AdvancedOCRResponse(
                success=True,
                message=f"OCR avancé réussi: {ocr_result.word_count} mots extraits",
                document_id=str(document.id),
                engine_used=engine_used,
                extracted_text=ocr_result.text,
                confidence_score=ocr_result.confidence,
                processing_time=processing_time,
                detected_entities=ocr_result.detected_entities,
                detected_tables=detected_tables,
                structure_regions=structure_regions,
                cache_used=cache_used,
                apple_silicon_optimized=apple_silicon_optimized
            )
            
        finally:
            # Nettoyage
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
    
    except Exception as e:
        logger.error(f"Erreur OCR avancé {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur OCR avancé: {str(e)}")


@router.post("/analyze-structure")
async def analyze_document_structure(
    file: UploadFile = File(..., description="Document à analyser"),
    request: StructureAnalysisRequest = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Analyse la structure d'un document avec LayoutLMv3
    
    - **file**: Document à analyser
    - **request**: Options d'analyse
    
    Retourne les régions détectées et leur classification
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix.lower(), delete=False) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_input_path = tmp_file.name
        
        try:
            layoutlm_config = LayoutLMConfig()
            layoutlm_engine = LayoutLMEngine(layoutlm_config)
            
            ocr_result, regions = layoutlm_engine.extract_structured_text(temp_input_path)
            
            response_data = {
                "success": True,
                "message": f"Structure analysée: {len(regions)} régions détectées",
                "extracted_text": ocr_result.text,
                "confidence": ocr_result.confidence,
                "processing_time": ocr_result.processing_time
            }
            
            if request.include_regions:
                response_data["regions"] = [
                    {
                        "type": region.region_type.value,
                        "text": region.text,
                        "bbox": region.bbox,
                        "confidence": region.confidence,
                        "tokens": region.tokens if hasattr(region, 'tokens') else []
                    }
                    for region in regions
                ]
            
            return response_data
            
        finally:
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
    
    except Exception as e:
        logger.error(f"Erreur analyse structure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {str(e)}")


@router.post("/detect-tables")
async def detect_document_tables(
    file: UploadFile = File(..., description="Document à analyser"),
    request: TableDetectionRequest = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Détecte et extrait les tableaux d'un document
    
    - **file**: Document à analyser
    - **request**: Configuration de la détection
    
    Retourne les tableaux détectés avec leur contenu
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix.lower(), delete=False) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_input_path = tmp_file.name
        
        try:
            # Configuration du détecteur
            method_map = {
                "hough_lines": TableDetectionMethod.HOUGH_LINES,
                "contours": TableDetectionMethod.CONTOURS,
                "morphology": TableDetectionMethod.MORPHOLOGY,
                "hybrid": TableDetectionMethod.HYBRID
            }
            
            detection_method = method_map.get(request.method, TableDetectionMethod.HYBRID)
            
            table_config = TableDetectorConfig(
                detection_method=detection_method,
                min_table_area=request.min_table_area or 1000
            )
            
            table_detector = TableDetector(table_config)
            tables = table_detector.detect_tables(temp_input_path)
            
            response_tables = []
            for table in tables:
                table_data = table_detector.extract_table_as_dict(table)
                if request.extract_content:
                    response_tables.append(table_data)
                else:
                    # Retourner seulement les métadonnées
                    response_tables.append({
                        "bbox": table_data["bbox"],
                        "dimensions": table_data["dimensions"],
                        "confidence": table_data["confidence"],
                        "extraction_method": table_data["extraction_method"]
                    })
            
            return {
                "success": True,
                "message": f"Détection terminée: {len(response_tables)} tableaux trouvés",
                "tables": response_tables,
                "detection_method": request.method
            }
            
        finally:
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
    
    except Exception as e:
        logger.error(f"Erreur détection tableaux: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur de détection: {str(e)}")


@router.post("/extract-entities")
async def extract_document_entities(
    file: UploadFile = File(..., description="Document à analyser"),
    request: EntityExtractionRequest = Depends(),
    current_user: User = Depends(get_current_user)
):
    """
    Extrait les entités spécifiques d'un document
    
    - **file**: Document à analyser
    - **request**: Configuration de l'extraction
    
    Retourne les entités détectées avec normalisation
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        with tempfile.NamedTemporaryFile(suffix=Path(file.filename).suffix.lower(), delete=False) as tmp_file:
            shutil.copyfileobj(file.file, tmp_file)
            temp_input_path = tmp_file.name
        
        try:
            # OCR basique pour obtenir le texte
            tesseract_engine = TesseractOCR()
            ocr_result = tesseract_engine.extract_text(temp_input_path)
            
            # Extraction d'entités
            entity_extractor = EntityExtractor()
            entity_result = entity_extractor.extract_entities(
                ocr_result.text, 
                entity_types=request.entity_types
            )
            
            # Métadonnées du document
            document_metadata = extract_document_metadata(ocr_result.text)
            
            response_data = {
                "success": True,
                "message": f"Extraction terminée: {len(entity_result.entities)} entités trouvées",
                "extracted_text": ocr_result.text if request.include_context else None,
                "processing_time": entity_result.processing_time,
                "entity_counts": entity_result.entity_counts,
                "entities": []
            }
            
            # Formatter les entités
            for entity in entity_result.entities:
                entity_data = {
                    "type": entity.entity_type,
                    "value": entity.value,
                    "confidence": entity.confidence,
                    "position": {
                        "start": entity.start_position,
                        "end": entity.end_position
                    }
                }
                
                if request.normalize_values and entity.normalized_value:
                    entity_data["normalized_value"] = str(entity.normalized_value)
                
                if request.include_context and entity.context:
                    entity_data["context"] = entity.context
                
                response_data["entities"].append(entity_data)
            
            # Ajouter les métadonnées du document
            response_data["document_metadata"] = document_metadata
            
            return response_data
            
        finally:
            if os.path.exists(temp_input_path):
                os.unlink(temp_input_path)
    
    except Exception as e:
        logger.error(f"Erreur extraction entités: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur d'extraction: {str(e)}")


@router.get("/cache/stats")
async def get_cache_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    Retourne les statistiques du cache OCR
    """
    try:
        cache_manager = get_cache_manager()
        stats = cache_manager.get_cache_stats()
        
        return {
            "success": True,
            "cache_stats": stats
        }
    
    except Exception as e:
        logger.error(f"Erreur stats cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.delete("/cache")
async def clear_ocr_cache(
    current_user: User = Depends(get_current_user)
):
    """
    Vide le cache OCR
    """
    try:
        cache_manager = get_cache_manager()
        cache_manager.clear_all_cache()
        
        return {
            "success": True,
            "message": "Cache OCR vidé avec succès"
        }
    
    except Exception as e:
        logger.error(f"Erreur vidage cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur: {str(e)}")


@router.get("/supported-formats")
async def get_supported_formats():
    """
    Retourne la liste des formats d'image supportés
    """
    return {
        "success": True,
        "supported_formats": [
            {
                "extension": ".jpg",
                "mime_types": ["image/jpeg"],
                "description": "JPEG image"
            },
            {
                "extension": ".jpeg", 
                "mime_types": ["image/jpeg"],
                "description": "JPEG image"
            },
            {
                "extension": ".png",
                "mime_types": ["image/png"],
                "description": "PNG image"
            },
            {
                "extension": ".tiff",
                "mime_types": ["image/tiff"],
                "description": "TIFF image"
            },
            {
                "extension": ".tif",
                "mime_types": ["image/tiff"],
                "description": "TIFF image"
            },
            {
                "extension": ".bmp",
                "mime_types": ["image/bmp"],
                "description": "Bitmap image"
            }
        ],
        "max_file_size": "50MB",
        "recommendations": [
            "Utilisez des images haute résolution (minimum 300 DPI)",
            "Évitez les images floues ou pixelisées",
            "Le format PNG est recommandé pour les documents scannés",
            "TIFF est idéal pour les documents de qualité archivage"
        ]
    }


async def _call_mistral_service_direct(text: str) -> dict:
    """Appel direct au service Mistral MLX natif avec gestion d'erreur robuste"""
    try:
        import httpx
        import os
        
        # Configuration service MLX
        mistral_host = "localhost"  # Architecture native macOS
        
        # Limiter le texte pour éviter les timeouts
        text_excerpt = text[:2000] if len(text) > 2000 else text
        
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


@router.get("/preprocessing-options")
async def get_preprocessing_options():
    """
    Retourne les options disponibles pour le prétraitement
    """
    return {
        "success": True,
        "options": {
            "rotation_correction": {
                "description": "Détecte et corrige automatiquement la rotation du document",
                "recommended": True,
                "processing_time": "medium"
            },
            "denoising": {
                "description": "Supprime le bruit de l'image pour améliorer la lisibilité",
                "recommended": True,
                "processing_time": "medium"
            },
            "border_cropping": {
                "description": "Détecte et supprime les bordures inutiles",
                "recommended": True,
                "processing_time": "fast"
            },
            "contrast_optimization": {
                "description": "Optimise le contraste et la luminosité pour l'OCR",
                "recommended": True,
                "processing_time": "fast"
            },
            "page_splitting": {
                "description": "Découpe automatiquement les pages multiples (livre ouvert, etc.)",
                "recommended": False,
                "processing_time": "fast"
            }
        }
    }