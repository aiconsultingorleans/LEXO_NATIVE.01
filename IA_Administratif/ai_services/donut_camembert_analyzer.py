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
from typing import Dict, List, Optional, Union
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger

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
    """Analyse document (placeholder pour Étape 3)"""
    # Placeholder pour Étape 3 - Service Core
    logger.info("📄 Demande d'analyse document (Étape 3 non implémentée)")
    
    return DocumentAnalysisResponse(
        success=False,
        error="Analyse documentaire implémentée dans Étape 3"
    )

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