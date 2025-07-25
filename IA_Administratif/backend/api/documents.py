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
import logging

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
    """Traite un document uploadé avec OCR, Mistral et classification automatique"""
    import logging
    import httpx
    import time
    from datetime import datetime
    import tempfile
    from pdf2image import convert_from_path
    
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 Début traitement document uploadé: {Path(file_path).name}")
    
    start_time = time.time()
    
    try:
        # 1. Analyse préliminaire avec Mistral MLX (basée sur le nom du fichier)
        filename = Path(file_path).name
        logger.info(f"🤖 Étape 1: Pré-analyse Mistral du fichier: {filename}")
        
        mistral_preanalysis = None
        mistral_category_suggestion = None
        
        try:
            # Analyse basée sur le nom de fichier et le type de document
            mistral_preanalysis = await _get_mistral_filename_analysis(filename)
            if mistral_preanalysis and mistral_preanalysis.get('success'):
                result_data = mistral_preanalysis.get('result', {})
                mistral_category_suggestion = result_data.get('document_type')
                logger.info(f"🎯 Pré-analyse Mistral: type={mistral_category_suggestion}")
        except Exception as e:
            logger.warning(f"Pré-analyse Mistral échouée: {e}")
        
        # 2. Préparation du fichier pour OCR
        processing_path = str(file_path)
        temp_image_path = None
        
        # Conversion PDF vers image si nécessaire
        if Path(file_path).suffix.lower() == '.pdf':
            try:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                    temp_image_path = temp_file.name
                
                images = convert_from_path(str(file_path), first_page=1, last_page=1)
                if images:
                    images[0].save(temp_image_path, 'PNG')
                    processing_path = temp_image_path
                    logger.info(f"📄 PDF converti en image: {temp_image_path}")
                else:
                    logger.error(f"Échec conversion PDF: {Path(file_path).name}")
                    return
                    
            except Exception as e:
                logger.error(f"Erreur conversion PDF {Path(file_path).name}: {e}")
                return
        
        # 3. Traitement OCR avec le moteur hybride
        from ocr.hybrid_ocr import HybridOCREngine, OCRStrategy
        from ocr.entity_extractor import EntityExtractor
        
        try:
            # OCR hybride (TrOCR + Tesseract fallback)
            ocr_engine = HybridOCREngine()
            ocr_result = ocr_engine.extract_text(
                processing_path,
                strategy=OCRStrategy.TROCR_FALLBACK
            )
            
            # Extraction d'entités
            entity_extractor = EntityExtractor()
            entities = []
            if hasattr(ocr_result, 'text') and ocr_result.text:
                try:
                    entity_result = entity_extractor.extract_entities(ocr_result.text)
                    entities = [
                        {
                            "type": entity.entity_type,
                            "value": entity.value,
                            "confidence": entity.confidence
                        }
                        for entity in entity_result.entities
                    ]
                except Exception as e:
                    logger.warning(f"Extraction d'entités échouée: {e}")
            
            logger.info(f"🔍 OCR terminé: {getattr(ocr_result, 'word_count', 0)} mots, confiance: {getattr(ocr_result, 'confidence', 0):.2f}")
            
        finally:
            # Nettoyer le fichier temporaire
            if temp_image_path and Path(temp_image_path).exists():
                Path(temp_image_path).unlink()
                logger.debug(f"Fichier temporaire supprimé: {temp_image_path}")
        
        # 4. Analyse avancée post-OCR avec Mistral MLX (service natif)
        ocr_text = getattr(ocr_result, 'text', str(ocr_result))
        mistral_analysis = None
        
        if ocr_text and len(ocr_text.strip()) > 50:
            try:
                mistral_analysis = await _get_mistral_analysis(ocr_text)
                if mistral_analysis and mistral_analysis.get('success'):
                    result_data = mistral_analysis.get('result', {})
                    # Fusionner avec la pré-analyse si elle existe
                    if not mistral_category_suggestion:
                        mistral_category_suggestion = result_data.get('document_type')
                    logger.info(f"🤖 Analyse Mistral post-OCR: type={mistral_category_suggestion}, confiance={result_data.get('confidence', 0)}")
            except Exception as e:
                logger.warning(f"Analyse Mistral post-OCR échouée: {e}")
        
        # 5. Classification hybride (règles + Mistral + pré-analyse)
        from services.document_classifier import get_document_classifier
        
        classifier = get_document_classifier()
        classification_result = classifier.classify_document(
            filename=Path(file_path).name,
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
        
        # 6. Génération de résumé Mistral
        summary = ""
        if mistral_analysis and mistral_analysis.get('success'):
            result_data = mistral_analysis.get('result', {})
            summary = result_data.get('summary', '').strip()
            
            if not summary or len(summary) < 10:
                try:
                    summary = await _generate_mistral_summary(ocr_text, final_category)
                except Exception as e:
                    logger.warning(f"Génération résumé Mistral échouée: {e}")
                    summary = f"Document de type {final_category} analysé. Contenu de {len(ocr_text.split())} mots traité automatiquement."
        else:
            try:
                summary = await _generate_mistral_summary(ocr_text, final_category)
            except Exception as e:
                logger.warning(f"Génération résumé Mistral échouée: {e}")
                summary = f"Document de type {final_category} analysé. Contenu de {len(ocr_text.split())} mots traité automatiquement."
        
        # 7. Mise à jour du document en base
        from core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Document).where(Document.id == document_id)
            )
            document = result.scalar_one_or_none()
            
            if document:
                # Mettre à jour le document existant
                document.category = final_category
                document.confidence_score = final_confidence
                document.ocr_text = ocr_text[:10000]  # Limiter la taille
                document.entities = entities
                document.custom_tags = [final_category]
                document.summary = summary
                document.processed_at = datetime.utcnow()
                
                await db.commit()
                
                process_time = time.time() - start_time
                
                logger.info(f"✅ Document mis à jour et traité: {Path(file_path).name}")
                logger.info(f"   📊 ID: {document.id} | Catégorie: {final_category}")
                logger.info(f"   🔍 Confiance: {document.confidence_score:.2f}")
                logger.info(f"   📝 Texte: {len(document.ocr_text)} chars")
                logger.info(f"   📄 Résumé: {len(summary)} chars")
                logger.info(f"   🏷️ Entités: {len(entities)} trouvées")
                logger.info(f"   ⏱️ Temps: {process_time:.2f}s")
                
                # 8. Déplacer le fichier vers le dossier de catégorie
                await _move_to_category_folder(Path(file_path), final_category)
                
            else:
                logger.error(f"Document {document_id} non trouvé en base")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors du traitement {Path(file_path).name}: {e}")
        import traceback
        traceback.print_exc()


async def _get_mistral_analysis(text: str) -> dict:
    """Obtient l'analyse complète du document depuis Mistral MLX natif avec cache"""
    from utils.mistral_cache import cached_mistral_analysis
    
    async def _do_mistral_request(text_excerpt: str, analysis_types: list) -> dict:
        """Fonction interne pour faire l'appel Mistral"""
        try:
            import httpx
            import os
            
            # Appel à l'API Mistral locale (service document_analyzer)
            mistral_host = "host.docker.internal" if "DOCKER" in os.environ or "/app" in os.getcwd() else "localhost"
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"http://{mistral_host}:8004/analyze",
                    json={
                        "text": text_excerpt,
                        "analysis_types": analysis_types
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
    
    # Limiter le texte pour éviter les prompts trop longs
    text_excerpt = text[:2000] if len(text) > 2000 else text
    analysis_types = ["classification", "summarization", "key_extraction"]
    
    # Utiliser le cache intelligent
    return await cached_mistral_analysis(
        text_excerpt, 
        analysis_types, 
        lambda t, at: _do_mistral_request(t, at)
    )


async def _generate_mistral_summary(text: str, category: str) -> str:
    """Génère un résumé du document avec Mistral MLX"""
    try:
        import httpx
        import os
        
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
        mistral_host = "host.docker.internal" if "DOCKER" in os.environ or "/app" in os.getcwd() else "localhost"
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"http://{mistral_host}:8004/analyze",
                json={
                    "text": text_excerpt,
                    "analysis_types": ["summarization"]
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    summary = result.get('result', {}).get('summary', '').strip()
                    if summary and len(summary) > 10:
                        return summary[:500]  # Limiter la taille
            
            # Fallback si Mistral n'est pas disponible
            logger.info(f"Mistral indisponible, génération résumé basique pour {category}")
            return f"Document de type {category} analysé - {len(text.split())} mots de contenu."
            
    except Exception as e:
        logger.warning(f"Erreur génération résumé Mistral: {e}")
        return f"Document {category} de {len(text.split())} mots analysé automatiquement."


async def _move_to_category_folder(file_path: Path, category: str):
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


async def _get_mistral_filename_analysis(filename: str) -> dict:
    """Analyse préliminaire du document basée sur le nom de fichier"""
    try:
        import httpx
        import os
        
        # Préparer un prompt spécialisé pour l'analyse du nom de fichier
        prompt = f"""Analyse ce nom de fichier et détermine le type de document probable : "{filename}"
        
Types possibles : factures, rib, contrats, attestations, courriers, rapports, cartes_transport, documents_personnels, non_classes

Réponds en JSON avec :
- document_type: le type le plus probable
- confidence: score de confiance (0-1)
- reasoning: courte explication"""
        
        mistral_host = "host.docker.internal" if "DOCKER" in os.environ or "/app" in os.getcwd() else "localhost"
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://{mistral_host}:8004/analyze",
                json={
                    "text": prompt,
                    "analysis_types": ["classification"]
                }
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Erreur API Mistral filename: {response.status_code}")
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
    except Exception as e:
        logger.warning(f"Erreur pré-analyse Mistral filename: {e}")
        return {"success": False, "error": str(e)}


@router.post("/upload-and-process", response_model=DocumentResponse)
async def upload_and_process_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload et traitement complet d'un document (pipeline unifié)
    - Upload du fichier
    - OCR extraction de texte
    - Analyse Mistral MLX pour classification et résumé
    - Sauvegarde avec toutes les métadonnées
    """
    import os
    import time
    import tempfile
    from datetime import datetime
    from pathlib import Path
    from pdf2image import convert_from_path
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Pipeline unifié démarré pour: {file.filename}")
    
    start_time = time.time()
    
    try:
        # 1. Validation du fichier
        if not file.filename:
            raise HTTPException(status_code=400, detail="Nom de fichier manquant")
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp'}:
            raise HTTPException(
                status_code=400, 
                detail=f"Format non supporté: {file_extension}"
            )
        
        # 2. Sauvegarde temporaire du fichier
        with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            temp_file_path = tmp_file.name
        
        try:
            # 3. Préparation pour OCR (conversion PDF → Image si nécessaire)
            processing_path = temp_file_path
            temp_image_path = None
            
            if file_extension == '.pdf':
                try:
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_img:
                        temp_image_path = temp_img.name
                    
                    images = convert_from_path(temp_file_path, first_page=1, last_page=1)
                    if images:
                        images[0].save(temp_image_path, 'PNG')
                        processing_path = temp_image_path
                        logger.info(f"📄 PDF converti en image")
                    else:
                        raise HTTPException(status_code=500, detail="Échec conversion PDF")
                        
                except Exception as e:
                    logger.error(f"Erreur conversion PDF: {e}")
                    raise HTTPException(status_code=500, detail=f"Erreur conversion PDF: {str(e)}")
            
            # 4. OCR avec Tesseract (fallback fiable)
            logger.info("🔍 Démarrage OCR Tesseract...")
            from ocr.tesseract_ocr import TesseractOCR
            from ocr.entity_extractor import EntityExtractor
            
            ocr_engine = TesseractOCR()
            ocr_result = ocr_engine.extract_text(processing_path)
            
            ocr_text = getattr(ocr_result, 'text', str(ocr_result))
            ocr_confidence = getattr(ocr_result, 'confidence', 0.0)
            word_count = getattr(ocr_result, 'word_count', len(ocr_text.split()))
            
            logger.info(f"✅ OCR terminé: {word_count} mots, confiance: {ocr_confidence:.2f}")
            
            # 5. Extraction d'entités
            entity_extractor = EntityExtractor()
            entities_data = []
            
            if ocr_text:
                try:
                    entity_result = entity_extractor.extract_entities(ocr_text)
                    entities_data = [
                        f"{entity.entity_type}:{entity.value}" 
                        for entity in entity_result.entities[:10]  # Limiter à 10
                    ]
                    logger.info(f"🏷️ Entités extraites: {len(entities_data)}")
                except Exception as e:
                    logger.warning(f"Extraction entités échouée: {e}")
            
            # 6. Analyse Mistral MLX pour classification et résumé
            mistral_analysis = None
            mistral_category = None
            summary = ""
            
            if ocr_text and len(ocr_text.strip()) > 50:
                try:
                    mistral_analysis = await _call_mistral_analysis(ocr_text)
                    if mistral_analysis.get('success'):
                        result_data = mistral_analysis.get('result', {})
                        mistral_category = result_data.get('document_type')
                        summary = result_data.get('summary', '').strip()
                        
                        logger.info(f"🤖 Mistral: type={mistral_category}, résumé={len(summary)} chars")
                    else:
                        logger.warning(f"Mistral échec: {mistral_analysis.get('error', 'Erreur inconnue')}")
                        
                except Exception as e:
                    logger.warning(f"Analyse Mistral échouée: {e}")
            
            # 7. Classification hybride (règles + Mistral)
            from services.document_classifier import get_document_classifier
            
            classifier = get_document_classifier()
            classification_result = classifier.classify_document(
                filename=file.filename,
                ocr_text=ocr_text,
                entities=entities_data
            )
            
            final_category = classification_result.category
            final_confidence = classification_result.confidence
            
            # Améliorer avec Mistral si disponible
            if mistral_category and mistral_analysis:
                mistral_confidence = mistral_analysis.get('result', {}).get('confidence', 0)
                mistral_to_our_categories = {
                    'facture': 'factures',
                    'rib': 'rib', 
                    'contrat': 'contrats',
                    'attestation': 'attestations',
                    'courrier': 'courriers',
                    'rapport': 'non_classes',
                    'autre': 'non_classes'
                }
                
                mistral_mapped = mistral_to_our_categories.get(mistral_category, 'non_classes')
                
                if mistral_confidence > 0.8 and mistral_mapped != final_category:
                    logger.info(f"🔄 Classification Mistral prioritaire: {mistral_mapped}")
                    final_category = mistral_mapped
                    final_confidence = min(0.95, (final_confidence + mistral_confidence) / 2)
                elif mistral_mapped == final_category:
                    final_confidence = min(0.98, final_confidence * 1.2)
            
            # 8. Génération de résumé si manquant
            if not summary:
                summary = f"Document de type {final_category} analysé automatiquement. Contenu: {word_count} mots extraits avec {final_confidence:.1%} de confiance."
            
            # 9. Sauvegarde en base de données
            document = Document(
                filename=file.filename,
                original_filename=file.filename,
                file_path=temp_file_path,  # Stocké temporairement 
                file_size=len(content),
                mime_type=file.content_type or "application/octet-stream",
                user_id=current_user.id,
                category=final_category,
                confidence_score=final_confidence,
                ocr_text=ocr_text[:10000],  # Limiter la taille
                entities=entities_data,
                custom_tags=[final_category],
                summary=summary[:500],  # Limiter la taille
                processed_at=datetime.utcnow()
            )
            
            db.add(document)
            await db.commit()
            await db.refresh(document)
            
            # 10. Métriques finales
            total_time = time.time() - start_time
            
            logger.info(f"✅ Pipeline unifié terminé avec succès:")
            logger.info(f"   📊 Document ID: {document.id}")
            logger.info(f"   🏷️ Catégorie: {final_category} (confiance: {final_confidence:.2f})")
            logger.info(f"   📝 Texte: {len(ocr_text)} chars, {word_count} mots")
            logger.info(f"   📄 Résumé: {len(summary)} chars")
            logger.info(f"   🔍 Entités: {len(entities_data)}")
            logger.info(f"   ⏱️ Temps total: {total_time:.2f}s")
            
            return document
            
        finally:
            # Nettoyage des fichiers temporaires
            for path in [temp_file_path, temp_image_path]:
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                    except Exception as e:
                        logger.warning(f"Échec suppression fichier temporaire {path}: {e}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur pipeline unifié {file.filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Erreur traitement: {str(e)}")


async def _call_mistral_analysis(text: str) -> dict:
    """Appel au service Mistral MLX natif avec gestion d'erreur robuste"""
    logger = logging.getLogger(__name__)
    try:
        import httpx
        import os
        
        # Configuration service MLX
        mistral_host = "host.docker.internal" if "DOCKER" in os.environ or "/app" in os.getcwd() else "localhost"
        
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