#!/usr/bin/env python3
"""
Service DONUT + CamemBERT - Pipeline alternatif documentaire
Étape 2 Infrastructure - Version de base pour tests

Architecture: Port 8005 (parallèle Mistral MLX port 8004)
Approche: 100% non-destructive, coexistence avec pipeline existant
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
import re

def clean_filename(filename: str) -> str:
    """
    Nettoie un nom de fichier pour le système de fichiers macOS
    - Remplace les espaces par des underscores
    - Supprime/remplace les caractères spéciaux problématiques
    - Conserve l'extension originale
    """
    if not filename:
        return "document_unknown"
    
    # Séparer nom et extension
    if '.' in filename:
        name_part, extension = filename.rsplit('.', 1)
        extension = f".{extension}"
    else:
        name_part = filename
        extension = ""
    
    # Nettoyer le nom
    clean_name = name_part.replace(" ", "_")
    clean_name = re.sub(r'[<>:"/\\|?*]', '_', clean_name)
    clean_name = re.sub(r'[^\w\-_.]', '_', clean_name)
    clean_name = re.sub(r'_+', '_', clean_name).strip('_')
    
    if not clean_name:
        clean_name = "document"
    
    return f"{clean_name}{extension}"

# Imports ML/AI (avec gestion gracieuse des erreurs)
try:
    import torch
    from transformers import AutoTokenizer, AutoModel, DonutProcessor, VisionEncoderDecoderModel
    from PIL import Image
    import numpy as np
    ML_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️  Dépendances ML non disponibles: {e}")
    ML_AVAILABLE = False

# Configuration
SERVICE_PORT = 8005
SERVICE_HOST = "0.0.0.0"
MODELS_DIR = Path(__file__).parent / "models" / "donut"

# Modèles configurés (basé sur validation Étape 1)
MODELS_CONFIG = {
    "donut": {
        "path": MODELS_DIR / "donut-base-finetuned-cord-v2",
        "loaded": False,
        "model": None,
        "processor": None
    },
    "camembert": {
        "path": MODELS_DIR / "camembert-base", 
        "loaded": False,
        "tokenizer": None,
        "model": None
    },
    "camembert_ner": {
        "path": MODELS_DIR / "camembert-ner",
        "loaded": False,
        "tokenizer": None,
        "model": None
    }
}

# État du service
SERVICE_STATE = {
    "started_at": None,
    "models_loaded": False,
    "ready": False,
    "device": "cpu",
    "apple_mps": False
}

# Modèles Pydantic
class HealthResponse(BaseModel):
    """Réponse health check"""
    status: str = Field(..., description="État du service")
    service: str = Field(default="donut-camembert-analyzer", description="Nom du service")
    port: int = Field(default=SERVICE_PORT, description="Port du service")
    models_status: Dict[str, bool] = Field(..., description="État des modèles")
    device: str = Field(..., description="Device utilisé (cpu/mps)")
    ready: bool = Field(..., description="Service prêt pour analyse")
    uptime_seconds: Optional[float] = Field(None, description="Durée de fonctionnement")

class ModelsStatusResponse(BaseModel):
    """État des modèles"""
    models: Dict[str, Dict[str, Union[str, bool]]] = Field(..., description="État détaillé des modèles")
    total_loaded: int = Field(..., description="Nombre de modèles chargés")
    total_models: int = Field(..., description="Nombre total de modèles")
    ready: bool = Field(..., description="Tous modèles prêts")

class DocumentAnalysisRequest(BaseModel):
    """Requête d'analyse document (pour Étape 3)"""
    text: Optional[str] = Field(None, description="Texte extrait (si disponible)")
    image_path: Optional[str] = Field(None, description="Chemin vers image")
    classification_only: bool = Field(False, description="Classification seule (sans OCR)")

class DocumentAnalysisResponse(BaseModel):
    """Réponse analyse document (pour Étape 3)"""
    success: bool = Field(..., description="Succès de l'analyse")
    extracted_text: Optional[str] = Field(None, description="Texte extrait par DONUT")
    classification: Optional[str] = Field(None, description="Catégorie détectée")
    confidence: Optional[float] = Field(None, description="Score de confiance")
    emitter: Optional[str] = Field(None, description="Émetteur détecté")
    processing_time_ms: Optional[float] = Field(None, description="Temps de traitement")
    error: Optional[str] = Field(None, description="Erreur éventuelle")

# Application FastAPI
app = FastAPI(
    title="DONUT CamemBERT Analyzer",
    description="Service alternatif d'analyse documentaire basé sur DONUT + CamemBERT",
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS pour intégration frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def detect_device() -> str:
    """Détecte le meilleur device disponible"""
    if not ML_AVAILABLE:
        return "cpu"
    
    if torch.backends.mps.is_available():
        SERVICE_STATE["apple_mps"] = True
        logger.info("🍎 Apple MPS détecté et disponible")
        return "mps"
    elif torch.cuda.is_available():
        logger.info("🚀 CUDA détecté et disponible")
        return "cuda"
    else:
        logger.info("💻 Utilisation CPU")
        return "cpu"

def load_models() -> bool:
    """Charge les modèles en mémoire (hot loading)"""
    if not ML_AVAILABLE:
        logger.error("❌ Impossible de charger les modèles - dépendances ML manquantes")
        return False
    
    try:
        logger.info("🔄 Chargement des modèles DONUT + CamemBERT...")
        device = SERVICE_STATE["device"]
        
        # 1. DONUT
        if MODELS_CONFIG["donut"]["path"].exists():
            logger.info("📥 Chargement DONUT...")
            processor = DonutProcessor.from_pretrained(str(MODELS_CONFIG["donut"]["path"]))
            model = VisionEncoderDecoderModel.from_pretrained(str(MODELS_CONFIG["donut"]["path"]))
            
            if device != "cpu":
                model = model.to(device)
            
            MODELS_CONFIG["donut"]["processor"] = processor
            MODELS_CONFIG["donut"]["model"] = model
            MODELS_CONFIG["donut"]["loaded"] = True
            logger.success("✅ DONUT chargé avec succès")
        
        # 2. CamemBERT Base
        if MODELS_CONFIG["camembert"]["path"].exists():
            logger.info("📥 Chargement CamemBERT...")
            tokenizer = AutoTokenizer.from_pretrained(str(MODELS_CONFIG["camembert"]["path"]))
            model = AutoModel.from_pretrained(str(MODELS_CONFIG["camembert"]["path"]))
            
            if device != "cpu":
                model = model.to(device)
            
            MODELS_CONFIG["camembert"]["tokenizer"] = tokenizer
            MODELS_CONFIG["camembert"]["model"] = model
            MODELS_CONFIG["camembert"]["loaded"] = True
            logger.success("✅ CamemBERT chargé avec succès")
        
        # 3. CamemBERT NER
        if MODELS_CONFIG["camembert_ner"]["path"].exists():
            logger.info("📥 Chargement CamemBERT NER...")
            tokenizer = AutoTokenizer.from_pretrained(str(MODELS_CONFIG["camembert_ner"]["path"]))
            model = AutoModel.from_pretrained(str(MODELS_CONFIG["camembert_ner"]["path"]))
            
            if device != "cpu":
                model = model.to(device)
            
            MODELS_CONFIG["camembert_ner"]["tokenizer"] = tokenizer
            MODELS_CONFIG["camembert_ner"]["model"] = model
            MODELS_CONFIG["camembert_ner"]["loaded"] = True
            logger.success("✅ CamemBERT NER chargé avec succès")
        
        # Vérification état final
        loaded_count = sum(1 for config in MODELS_CONFIG.values() if config["loaded"])
        total_count = len(MODELS_CONFIG)
        
        SERVICE_STATE["models_loaded"] = (loaded_count > 0)
        SERVICE_STATE["ready"] = (loaded_count == total_count)
        
        logger.success(f"🎉 Modèles chargés: {loaded_count}/{total_count}")
        return SERVICE_STATE["models_loaded"]
        
    except Exception as e:
        logger.error(f"❌ Erreur chargement modèles: {e}")
        return False

@app.on_event("startup")
async def startup_event():
    """Initialisation du service"""
    logger.info("🍩 DONUT CamemBERT Analyzer - Démarrage Étape 2")
    logger.info(f"📍 Port: {SERVICE_PORT}")
    logger.info(f"📁 Modèles: {MODELS_DIR}")
    
    SERVICE_STATE["started_at"] = datetime.now()
    SERVICE_STATE["device"] = detect_device()
    
    # Chargement des modèles en arrière-plan
    if MODELS_DIR.exists():
        success = load_models()
        if success:
            logger.success("🚀 Service DONUT prêt!")
        else:
            logger.warning("⚠️  Service démarré avec modèles partiels")
    else:
        logger.warning(f"⚠️  Dossier modèles non trouvé: {MODELS_DIR}")

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check du service"""
    uptime = None
    if SERVICE_STATE["started_at"]:
        uptime = (datetime.now() - SERVICE_STATE["started_at"]).total_seconds()
    
    models_status = {
        model_name: config["loaded"] 
        for model_name, config in MODELS_CONFIG.items()
    }
    
    return HealthResponse(
        status="healthy" if SERVICE_STATE["ready"] else "partial",
        models_status=models_status,
        device=SERVICE_STATE["device"],
        ready=SERVICE_STATE["ready"],
        uptime_seconds=uptime
    )

@app.get("/models/status", response_model=ModelsStatusResponse)
async def models_status():
    """État détaillé des modèles"""
    models_info = {}
    loaded_count = 0
    
    for model_name, config in MODELS_CONFIG.items():
        models_info[model_name] = {
            "loaded": config["loaded"],
            "path": str(config["path"]),
            "exists": config["path"].exists()
        }
        if config["loaded"]:
            loaded_count += 1
    
    return ModelsStatusResponse(
        models=models_info,
        total_loaded=loaded_count,
        total_models=len(MODELS_CONFIG),
        ready=(loaded_count == len(MODELS_CONFIG))
    )

@app.post("/models/reload")
async def reload_models():
    """Rechargement à chaud des modèles"""
    logger.info("🔄 Rechargement des modèles demandé...")
    
    # Reset état modèles
    for config in MODELS_CONFIG.values():
        config["loaded"] = False
        config["model"] = None
        config["processor"] = None
        config["tokenizer"] = None
    
    success = load_models()
    
    if success:
        return {"status": "success", "message": "Modèles rechargés avec succès"}
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du rechargement des modèles"
        )

@app.post("/analyze", response_model=DocumentAnalysisResponse)
async def analyze_document(request: DocumentAnalysisRequest):
    """Analyse document basique (sans organisation)"""
    logger.info("📄 Analyse document basique sans organisation")
    
    return DocumentAnalysisResponse(
        success=False,
        error="Utilisez /analyze/complete pour l'analyse avec organisation automatique"
    )

@app.post("/analyze/complete")
async def analyze_document_complete(file: UploadFile = File(...)):
    """
    Analyse complète document avec organisation automatique hiérarchique
    
    Pipeline complet :
    1. Extraction texte DONUT (OCR-free)
    2. Classification dynamique CamemBERT
    3. Extraction émetteurs NER français
    4. Organisation automatique avec création sous-dossiers
    """
    import tempfile
    import time
    from datetime import datetime
    
    start_time = time.time()
    logger.info(f"🚀 Analyse complète démarrée pour : {file.filename}")
    
    try:
        # Import dynamique des modules d'organisation
        from utils.donut_processor import DonutDocumentProcessor
        from utils.dynamic_classifier import DynamicDocumentClassifier  
        from utils.entity_extractor import FrenchEntityExtractor
        from utils.document_organizer import DocumentOrganizer
        
        # Vérification que les modèles sont chargés
        if not SERVICE_STATE["models_loaded"]:
            logger.warning("🔄 Modèles non chargés, tentative de chargement...")
            if not load_models():
                raise HTTPException(
                    status_code=503,
                    detail="Modèles DONUT non disponibles - Utilisez le pipeline Mistral"
                )
        
        # 1. Sauvegarde avec nom original nettoyé
        cleaned_filename = clean_filename(file.filename)
        temp_dir = Path(tempfile.gettempdir())
        temp_file_path = temp_dir / cleaned_filename
        
        # Éviter les conflits de nom dans le dossier temporaire
        counter = 1
        original_path = temp_file_path
        while temp_file_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            temp_file_path = temp_dir / f"{stem}_{counter}{suffix}"
            counter += 1
        
        content = await file.read()
        with open(temp_file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"📁 Fichier sauvegardé avec nom original : {temp_file_path}")
        
        # 2. Extraction texte avec DONUT
        logger.info("🔍 Étape 1/4 : Extraction texte DONUT...")
        donut_processor = DonutDocumentProcessor(models_path="models/donut")
        if not donut_processor.load_models():
            raise HTTPException(status_code=500, detail="Erreur chargement modèles DONUT")
        
        # Extraction texte selon le type de fichier
        if temp_file_path.lower().endswith('.pdf'):
            from utils.donut_processor import extract_text_with_donut
            extraction_result = extract_text_with_donut(temp_file_path, "models/donut")
        else:
            extraction_result = donut_processor.extract_text_from_image(temp_file_path)
        if not extraction_result.get("success"):
            raise HTTPException(status_code=500, detail=f"Erreur extraction DONUT: {extraction_result.get('error')}")
        
        extracted_text = extraction_result.get("extracted_text", "")
        logger.success(f"✅ Texte extrait : {len(extracted_text)} caractères")
        
        # 3. Classification dynamique avec CamemBERT
        logger.info("🏷️ Étape 2/4 : Classification dynamique...")
        classifier = DynamicDocumentClassifier(models_path="models/donut")
        if not classifier.load_models():
            raise HTTPException(status_code=500, detail="Erreur chargement modèles CamemBERT")
        
        classification_result = classifier.classify_document(extracted_text, file.filename)
        if not classification_result.get("success"):
            raise HTTPException(status_code=500, detail=f"Erreur classification: {classification_result.get('error')}")
        
        category = classification_result.get("category", "non_classes")
        confidence = classification_result.get("confidence", 0.0)
        logger.success(f"✅ Catégorie : {category} (confiance: {confidence:.2f})")
        
        # 4. Extraction émetteurs avec NER français
        logger.info("🏢 Étape 3/4 : Extraction émetteurs...")
        entity_extractor = FrenchEntityExtractor(models_path="models/donut")
        if not entity_extractor.load_models():
            raise HTTPException(status_code=500, detail="Erreur chargement modèles NER")
        
        entities_result = entity_extractor.extract_emitters(extracted_text, category)
        if not entities_result.get("success"):
            logger.warning(f"⚠️ Erreur extraction émetteurs: {entities_result.get('error')}")
            # Continuer avec émetteur par défaut
            primary_emitter = {"normalized_name": "Inconnu", "original_name": "Inconnu", "confidence": 0.0}
        else:
            primary_emitter = entities_result.get("primary_emitter", {"normalized_name": "Inconnu", "original_name": "Inconnu", "confidence": 0.0})
        
        logger.success(f"✅ Émetteur principal : {primary_emitter['normalized_name']} (confiance: {primary_emitter.get('confidence', 0):.2f})")
        
        # 5. Organisation automatique avec création dossiers
        logger.info("📁 Étape 4/4 : Organisation automatique...")
        organizer = DocumentOrganizer(ocr_base_path="/Users/stephaneansel/Documents/LEXO_v1/OCR", threshold_documents=2)
        
        # Copie du fichier temporaire vers sa destination finale organisée
        organization_result = organizer.organize_document(
            document_path=temp_file_path,
            category=category,
            emitter_info=primary_emitter
        )
        
        if not organization_result.get("success"):
            raise HTTPException(status_code=500, detail=f"Erreur organisation: {organization_result.get('error')}")
        
        final_path = organization_result.get("destination_path")
        folder_created = organization_result.get("folder_created", False)
        organization_type = organization_result.get("organization_type", "main_category")
        emitter_count = organization_result.get("emitter_count", 1)
        
        logger.success(f"✅ Document organisé : {final_path}")
        if folder_created:
            logger.success(f"🆕 Nouveau sous-dossier créé pour {primary_emitter['normalized_name']}")
        
        # Nettoyage fichier temporaire
        try:
            if temp_file_path.exists():
                temp_file_path.unlink()
                logger.debug(f"🗑️ Fichier temporaire supprimé : {temp_file_path}")
        except Exception as e:
            logger.warning(f"⚠️ Échec suppression fichier temporaire : {e}")
        
        # 6. Résultat final
        processing_time = (time.time() - start_time) * 1000  # en ms
        
        result = {
            "success": True,
            "filename": file.filename,
            "category": category,
            "confidence_score": confidence,
            "emitter": {
                "name": primary_emitter["normalized_name"],
                "original_name": primary_emitter.get("original_name"),
                "confidence": primary_emitter.get("confidence", 0.0)
            },
            "organization": {
                "final_path": final_path,
                "organization_type": organization_type,
                "folder_created": folder_created,
                "emitter_count": emitter_count
            },
            "extracted_text_preview": extracted_text[:200] + "..." if len(extracted_text) > 200 else extracted_text,
            "processing_time_ms": processing_time,
            "pipeline": "donut-complete",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.success(f"🎉 Analyse complète terminée en {processing_time:.0f}ms")
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erreur analyse complète : {e}")
        # Nettoyage en cas d'erreur
        try:
            if 'temp_file_path' in locals() and temp_file_path.exists():
                temp_file_path.unlink()
                logger.debug(f"🗑️ Fichier temporaire supprimé (erreur) : {temp_file_path}")
        except Exception as cleanup_e:
            logger.warning(f"⚠️ Échec nettoyage après erreur : {cleanup_e}")
        except:
            pass
        
        raise HTTPException(
            status_code=500,
            detail=f"Erreur interne analyse complète: {str(e)}"
        )

@app.post("/organization/reorganize")
async def reorganize_existing_documents():
    """
    Réorganisation rétroactive des documents existants
    
    Applique le système de sous-dossiers automatiques aux documents déjà présents
    dans l'arborescence OCR pour créer les dossiers manquants (EDF, Sollea, etc.)
    """
    try:
        from utils.document_organizer import DocumentOrganizer
        from utils.entity_extractor import FrenchEntityExtractor
        from pathlib import Path
        import os
        
        logger.info("🔄 Démarrage réorganisation rétroactive...")
        
        # Initialisation des modules
        organizer = DocumentOrganizer(ocr_base_path="/Users/stephaneansel/Documents/LEXO_v1/OCR", threshold_documents=2)
        entity_extractor = FrenchEntityExtractor(models_path="models/donut")
        
        # Chargement modèles NER si nécessaire  
        if not entity_extractor.load_models():
            logger.warning("⚠️ Modèles NER non disponibles - Utilisation patterns de base")
        
        reorganization_stats = {
            "processed_documents": 0,
            "folders_created": 0,
            "documents_moved": 0,
            "errors": [],
            "emitter_matches": {},
            "cache_hits": 0,
            "ocr_extractions": 0
        }
        
        # Cache simple pour éviter re-traitement des mêmes documents
        analysis_cache = {}
        
        base_path = Path("/Users/stephaneansel/Documents/LEXO_v1/OCR")
        
        # Parcours des catégories principales
        for category_folder in base_path.iterdir():
            if not category_folder.is_dir() or category_folder.name.startswith('.'):
                continue
                
            category_name = category_folder.name
            logger.info(f"📁 Traitement catégorie : {category_name}")
            
            # Analyse des documents dans cette catégorie
            emitter_counts = {}
            documents_by_emitter = {}
            
            for document_path in category_folder.iterdir():
                if not document_path.is_file():
                    continue
                
                try:
                    reorganization_stats["processed_documents"] += 1
                    logger.info(f"  📄 Analyse: {document_path.name}")
                    
                    detected_emitter = "Inconnu"
                    
                    # NOUVELLE APPROCHE: Utiliser les données du cache d'entités existant
                    cache_emitter = _get_emitter_from_entity_cache(document_path.name)
                    
                    if cache_emitter:
                        detected_emitter = cache_emitter
                        reorganization_stats["cache_hits"] += 1
                        logger.success(f"    💾 Émetteur du cache: {detected_emitter}")
                    else:
                        # Fallback: patterns nom de fichier
                        filename_lower = document_path.name.lower()
                        
                        emitter_patterns = {
                            "EDF": ["edf", "electricite_france", "edf_", "facture_edf"],
                            "Sollea": ["sollea"],
                            "Orange": ["orange"],
                            "SFR": ["sfr"],
                            "Bouygues": ["bouygues"],
                            "Free": ["free"],
                            "CPAM": ["cpam", "assurance_maladie"],
                            "CAF": ["caf", "allocations_familiales"],
                            "Credit_Agricole": ["credit_agricole", "ca_", "ca.", "ca_paris"],
                            "BNP": ["bnp", "bnp_paribas"],
                            "Societe_Generale": ["societe_generale", "sg_"]
                        }
                        
                        for emitter, patterns in emitter_patterns.items():
                            if any(pattern in filename_lower for pattern in patterns):
                                detected_emitter = emitter
                                logger.info(f"    📂 Émetteur par nom fichier: {detected_emitter}")
                                break
                    
                    # Comptage par émetteur
                    if detected_emitter != "Inconnu":
                        emitter_counts[detected_emitter] = emitter_counts.get(detected_emitter, 0) + 1
                        if detected_emitter not in documents_by_emitter:
                            documents_by_emitter[detected_emitter] = []
                        documents_by_emitter[detected_emitter].append(document_path)
                    
                    logger.debug(f"  📄 {document_path.name} → {detected_emitter}")
                    
                except Exception as e:
                    reorganization_stats["errors"].append(f"Erreur traitement {document_path.name}: {e}")
                    logger.warning(f"⚠️ Erreur traitement {document_path.name}: {e}")
            
            # Création des sous-dossiers nécessaires
            for emitter, count in emitter_counts.items():
                if count >= organizer.threshold_documents and emitter != "Inconnu":
                    subfolder_path = category_folder / emitter
                    
                    if not subfolder_path.exists():
                        try:
                            subfolder_path.mkdir(exist_ok=True)
                            reorganization_stats["folders_created"] += 1
                            logger.success(f"✅ Sous-dossier créé : {category_name}/{emitter}")
                            
                            # Déplacement des documents vers le sous-dossier
                            for doc_path in documents_by_emitter[emitter]:
                                new_path = subfolder_path / doc_path.name
                                if not new_path.exists():
                                    doc_path.rename(new_path)
                                    reorganization_stats["documents_moved"] += 1
                                    logger.info(f"  📄 Déplacé : {doc_path.name} → {category_name}/{emitter}/")
                                    
                        except Exception as e:
                            error_msg = f"Erreur création/déplacement {category_name}/{emitter}: {e}"
                            reorganization_stats["errors"].append(error_msg)
                            logger.error(f"❌ {error_msg}")
                    
                    reorganization_stats["emitter_matches"][f"{category_name}/{emitter}"] = count
        
        # Mise à jour des statistiques de l'organizer
        for category_emitter, count in reorganization_stats["emitter_matches"].items():
            category, emitter = category_emitter.split("/", 1)
            organizer.emitter_counts[category][emitter] = count
        
        result = {
            "success": True,
            "reorganization_stats": reorganization_stats,
            "message": f"Réorganisation terminée : {reorganization_stats['folders_created']} dossiers créés, {reorganization_stats['documents_moved']} documents déplacés",
            "timestamp": datetime.now().isoformat()
        }
        
        logger.success(f"🎉 Réorganisation terminée : {reorganization_stats['folders_created']} dossiers créés")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur réorganisation rétroactive : {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur réorganisation: {str(e)}"
        )

@app.post("/test/single-document")
async def test_single_document_analysis(file_path: str):
    """
    Test analyse d'un seul document pour debugging
    """
    try:
        from utils.donut_processor import extract_text_with_donut
        from utils.entity_extractor import FrenchEntityExtractor
        from pathlib import Path
        
        document_path = Path(file_path)
        if not document_path.exists():
            raise HTTPException(status_code=404, detail=f"Fichier non trouvé: {file_path}")
        
        logger.info(f"🧪 Test analyse: {document_path.name}")
        
        # 1. Extraction DONUT
        logger.info("🔍 Extraction DONUT...")
        extraction_result = extract_text_with_donut(str(document_path), "models/donut")
        
        if not extraction_result.get("success"):
            return {"error": f"Erreur DONUT: {extraction_result.get('error')}", "success": False}
        
        extracted_text = extraction_result.get("extracted_text", "")
        logger.success(f"✅ Texte extrait: {len(extracted_text)} caractères")
        
        # 2. Extraction émetteur
        logger.info("🏢 Extraction émetteur...")
        entity_extractor = FrenchEntityExtractor(models_path="models/donut")
        if not entity_extractor.load_models():
            return {"error": "Modèles NER non disponibles", "success": False}
        
        entities_result = entity_extractor.extract_emitters(extracted_text, "factures")
        
        result = {
            "success": True,
            "file_path": str(document_path),
            "extracted_text_preview": extracted_text[:500] + "..." if len(extracted_text) > 500 else extracted_text,
            "text_length": len(extracted_text),
            "extraction_time": extraction_result.get("processing_time", 0),
            "entities_result": entities_result,
            "primary_emitter": entities_result.get("primary_emitter") if entities_result.get("success") else None
        }
        
        logger.success(f"🎉 Test terminé pour {document_path.name}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Erreur test: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def _get_emitter_from_entity_cache(filename: str) -> Optional[str]:
        """
        Recherche l'émetteur dans le cache d'entités existant
        
        Args:
            filename: Nom du fichier à rechercher
            
        Returns:
            Nom de l'émetteur normalisé ou None
        """
        import json
        from pathlib import Path
        
        entity_cache_dir = Path("/Users/stephaneansel/Documents/LEXO_v1/IA_Administratif/backend/data/entity_cache")
        
        if not entity_cache_dir.exists():
            return None
        
        # Recherche directe par nom de fichier dans les caches
        filename_base = filename.replace('.pdf', '').replace('.png', '').replace('.jpg', '').replace('.jpeg', '')
        
        for cache_file in entity_cache_dir.glob("*.json"):
            try:
                # Le nom du cache contient le nom original du fichier
                cache_filename = cache_file.name
                
                # Correspondance directe ou partielle
                if filename in cache_filename or filename_base in cache_filename:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    
                    # Extraction émetteur depuis les entreprises détectées
                    entreprises = cache_data.get("entreprises", [])
                    if entreprises:
                        # Prendre la première entreprise avec confiance > 0.6
                        for entreprise in entreprises:
                            if entreprise.get("confidence", 0) > 0.6:
                                emitter_name = entreprise.get("value", "").lower()
                                
                                # Normalisation des noms
                                emitter_mapping = {
                                    "edf": "EDF",
                                    "electricite de france": "EDF", 
                                    "sollea": "Sollea",
                                    "orange": "Orange",
                                    "sfr": "SFR",
                                    "bouygues": "Bouygues",
                                    "free": "Free",
                                    "caisse primaire": "CPAM",
                                    "cpam": "CPAM",
                                    "caf": "CAF",
                                    "credit agricole": "Credit_Agricole",
                                    "bnp": "BNP",
                                    "bnp paribas": "BNP",
                                    "societe generale": "Societe_Generale"
                                }
                                
                                for pattern, normalized in emitter_mapping.items():
                                    if pattern in emitter_name:
                                        logger.debug(f"      🎯 Émetteur trouvé dans cache: {normalized} (confiance: {entreprise.get('confidence'):.2f})")
                                        return normalized
                        
                        # Si pas de correspondance directe, prendre le premier
                        if entreprises:
                            first_emitter = entreprises[0].get("value", "").title()
                            logger.debug(f"      🔍 Émetteur générique du cache: {first_emitter}")
                            return first_emitter
                            
            except Exception as e:
                logger.debug(f"      ⚠️ Erreur lecture cache {cache_file.name}: {e}")
                continue
        
        return None

@app.get("/organization/structure")
async def get_organization_structure():
    """
    Obtenir l'arborescence intelligente DONUT
    
    Retourne la structure hiérarchique des dossiers organisés automatiquement
    par le pipeline DONUT avec classification dynamique.
    """
    try:
        # Import dynamique pour éviter les erreurs au démarrage
        from utils.document_organizer import DocumentOrganizer
        
        # Créer instance organizer avec chemin OCR correct
        organizer = DocumentOrganizer(ocr_base_path="/Users/stephaneansel/Documents/LEXO_v1/OCR")
        
        # Obtenir structure actuelle
        structure_data = organizer.get_folder_structure(include_stats=True)
        
        if "error" in structure_data:
            raise HTTPException(
                status_code=500,
                detail=f"Erreur scan structure: {structure_data['error']}"
            )
        
        # Formater pour compatibilité frontend
        formatted_structure = {
            "tree": _convert_to_frontend_format(structure_data["structure"]),
            "metadata": {
                "totalFolders": _count_folders(structure_data["structure"]),
                "totalDocuments": _count_documents(structure_data["structure"]),
                "autoCreatedFolders": _count_auto_folders(structure_data["structure"]),
                "categories": list(structure_data.get("emitter_counts", {}).keys()),
                "emitters": _extract_emitters(structure_data.get("emitter_counts", {})),
                "lastUpdate": datetime.now().isoformat()
            },
            "stats": {
                "pipeline": "donut",
                "organizationLevel": _calculate_organization_level(structure_data),
                "efficiency": _calculate_efficiency(structure_data)
            }
        }
        
        return formatted_structure
        
    except Exception as e:
        logger.error(f"Erreur récupération structure DONUT: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur organisation DONUT: {str(e)}"
        )

def _convert_to_frontend_format(structure: Dict[str, Any]) -> Dict[str, Any]:
    """Convertit la structure organizer vers format frontend"""
    if not structure:
        return {
            "name": "OCR",
            "path": "/OCR", 
            "type": "folder",
            "children": []
        }
    
    return {
        "name": structure.get("name", "OCR"),
        "path": structure.get("path", "/OCR"),
        "type": structure.get("type", "folder"),
        "documentCount": structure.get("file_count", 0),
        "isAutoCreated": structure.get("auto_created", False),
        "children": [
            _convert_to_frontend_format(child) 
            for child in structure.get("children", [])
        ] if structure.get("children") else []
    }

def _count_folders(structure: Dict[str, Any]) -> int:
    """Compte le nombre total de dossiers"""
    if not structure or structure.get("type") != "folder":
        return 0
    
    count = 1  # Ce dossier
    for child in structure.get("children", []):
        if child.get("type") == "folder":
            count += _count_folders(child)
    
    return count

def _count_documents(structure: Dict[str, Any]) -> int:
    """Compte le nombre total de documents"""
    if not structure:
        return 0
    
    count = structure.get("file_count", 0)
    for child in structure.get("children", []):
        count += _count_documents(child)
    
    return count

def _count_auto_folders(structure: Dict[str, Any]) -> int:
    """Compte les dossiers auto-créés"""
    if not structure or structure.get("type") != "folder":
        return 0
    
    count = 1 if structure.get("auto_created", False) else 0
    for child in structure.get("children", []):
        if child.get("type") == "folder":
            count += _count_auto_folders(child)
    
    return count

def _extract_emitters(emitter_counts: Dict[str, Any]) -> List[str]:
    """Extrait la liste des émetteurs"""
    emitters = []
    for category_emitters in emitter_counts.values():
        emitters.extend(category_emitters.keys())
    return list(set(emitters))

def _calculate_organization_level(structure_data: Dict[str, Any]) -> int:
    """Calcule le niveau d'organisation (pourcentage)"""
    stats = structure_data.get("statistics", {})
    total_docs = stats.get("total_documents", 1)
    organized_docs = stats.get("documents_organized", 0)
    return int((organized_docs / total_docs) * 100) if total_docs > 0 else 0

def _calculate_efficiency(structure_data: Dict[str, Any]) -> int:
    """Calcule l'efficacité du classement"""
    stats = structure_data.get("statistics", {})
    auto_folders = stats.get("auto_created_folders", 0)
    total_folders = stats.get("total_folders", 1)
    return int((auto_folders / total_folders) * 100) if total_folders > 0 else 85

@app.get("/")
async def root():
    """Page d'accueil du service"""
    return {
        "service": "DONUT CamemBERT Analyzer",
        "version": "0.2.0",
        "status": "Infrastructure prête (Étape 2)",
        "next_step": "Implémentation Service Core (Étape 3)",
        "endpoints": {
            "health": "/health",
            "models": "/models/status", 
            "organization/structure": "/organization/structure",
            "docs": "/docs"
        }
    }

def main():
    """Point d'entrée principal"""
    logger.info("🍩 Lancement DONUT CamemBERT Analyzer")
    logger.info(f"📍 http://localhost:{SERVICE_PORT}")
    
    uvicorn.run(
        "donut_camembert_analyzer:app",
        host=SERVICE_HOST,
        port=SERVICE_PORT,
        reload=False,  # Pas de reload pour éviter conflits modèles
        log_level="info"
    )

if __name__ == "__main__":
    main()