"""
Service d'analyse documentaire intelligent avec Mistral MLX
Analyse sémantique et classification avancée de documents
"""

import asyncio
import logging
import time
import json
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

# FastAPI pour l'API service
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# MLX pour Mistral
try:
    from mlx_lm import load, generate
except ImportError:
    logging.error("mlx_lm not installed. Run: pip install mlx-lm")
    raise

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types de documents supportés"""
    FACTURE = "facture"
    RIB = "rib"
    CONTRAT = "contrat"
    ATTESTATION = "attestation"
    COURRIER = "courrier"
    RAPPORT = "rapport"
    AUTRE = "autre"


class AnalysisType(Enum):
    """Types d'analyse disponibles"""
    CLASSIFICATION = "classification"
    SUMMARIZATION = "summarization"
    KEY_EXTRACTION = "key_extraction"
    SENTIMENT = "sentiment"
    COMPLIANCE = "compliance"


@dataclass
class DocumentAnalysisResult:
    """Résultat d'analyse documentaire"""
    document_type: DocumentType
    confidence: float
    summary: str
    key_information: Dict[str, Any]
    entities: List[Dict[str, Any]]
    sentiment: Optional[str] = None
    compliance_status: Optional[str] = None
    processing_time: float = 0.0
    raw_analysis: Optional[str] = None


class DocumentAnalysisRequest(BaseModel):
    """Requête d'analyse de document"""
    text: str
    analysis_types: List[str] = ["classification", "key_extraction"]
    document_context: Optional[str] = None
    custom_prompt: Optional[str] = None


class DocumentAnalyzer:
    """
    Analyseur de documents intelligent utilisant Mistral MLX
    """
    
    def __init__(self, model_path: str = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"):
        """
        Initialise l'analyseur de documents
        
        Args:
            model_path: Chemin vers le modèle Mistral MLX
        """
        self.model_path = model_path
        self.model = None
        self.tokenizer = None
        self.logger = logging.getLogger("document_analyzer")
        
        # Prompts spécialisés
        self.prompts = {
            "classification": """Tu es un expert en analyse documentaire. Analyse le document suivant et détermine son type principal parmi : facture, RIB, contrat, attestation, courrier, rapport, autre.

Document à analyser :
{text}

Réponds en JSON avec cette structure exacte :
{{"type": "type_du_document", "confidence": 0.95, "reasoning": "explication_courte"}}""",

            "key_extraction": """Tu es un expert en extraction d'informations. Extrais les informations clés de ce document administratif français.

Document :
{text}

Extrais et structure les informations importantes (dates, montants, noms, adresses, numéros de référence, etc.) en JSON :
{{"informations_cles": {{"dates": [], "montants": [], "personnes": [], "entreprises": [], "references": [], "autres": {{}}}}}""",

            "summarization": """Tu es un expert en synthèse documentaire. Créé un résumé concis et professionnel de ce document.

Document :
{text}

Résumé en 2-3 phrases maximum, en français professionnel :""",

            "compliance": """Tu es un expert en conformité documentaire. Évalue la conformité et la complétude de ce document administratif français.

Document :
{text}

Analyse en JSON :
{{"conformite": "conforme/non_conforme/partiel", "elements_manquants": [], "recommandations": []}}"""
        }
    
    async def initialize(self):
        """Initialise le modèle Mistral MLX"""
        try:
            self.logger.info(f"Chargement du modèle Mistral : {self.model_path}")
            self.model, self.tokenizer = load(self.model_path)
            self.logger.info("Document Analyzer initialisé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur initialisation Document Analyzer : {e}")
            raise
    
    async def analyze_document(
        self, 
        text: str, 
        analysis_types: List[AnalysisType] = None,
        document_context: Optional[str] = None
    ) -> DocumentAnalysisResult:
        """
        Analyse complète d'un document
        
        Args:
            text: Texte du document à analyser
            analysis_types: Types d'analyse à effectuer
            document_context: Contexte additionnel du document
            
        Returns:
            Résultat d'analyse structuré
        """
        start_time = time.time()
        
        if analysis_types is None:
            analysis_types = [AnalysisType.CLASSIFICATION, AnalysisType.KEY_EXTRACTION]
        
        try:
            result = DocumentAnalysisResult(
                document_type=DocumentType.AUTRE,
                confidence=0.0,
                summary="",
                key_information={},
                entities=[],
                processing_time=0.0
            )
            
            # Classification du document
            if AnalysisType.CLASSIFICATION in analysis_types:
                classification = await self._classify_document(text)
                result.document_type = classification.get("type", DocumentType.AUTRE)
                result.confidence = classification.get("confidence", 0.0)
            
            # Extraction d'informations clés
            if AnalysisType.KEY_EXTRACTION in analysis_types:
                key_info = await self._extract_key_information(text)
                result.key_information = key_info
            
            # Résumé
            if AnalysisType.SUMMARIZATION in analysis_types:
                result.summary = await self._summarize_document(text)
            
            # Analyse de conformité
            if AnalysisType.COMPLIANCE in analysis_types:
                compliance = await self._analyze_compliance(text)
                result.compliance_status = compliance.get("conformite", "non_évalué")
            
            result.processing_time = time.time() - start_time
            
            self.logger.info(f"Analyse terminée en {result.processing_time:.2f}s - Type: {result.document_type}")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse documentaire : {e}")
            raise HTTPException(status_code=500, detail=f"Erreur d'analyse : {str(e)}")
    
    async def _classify_document(self, text: str) -> Dict[str, Any]:
        """Classifie le type de document"""
        try:
            prompt = self.prompts["classification"].format(text=text[:2000])  # Limiter la taille
            
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=100,
                verbose=False
            )
            
            # Parser la réponse JSON
            try:
                # Extraire le JSON de la réponse
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                
                classification_data = json.loads(json_str)
                
                # Mapper vers notre enum
                doc_type_str = classification_data.get("type", "autre")
                try:
                    doc_type = DocumentType(doc_type_str)
                except ValueError:
                    doc_type = DocumentType.AUTRE
                
                return {
                    "type": doc_type,
                    "confidence": float(classification_data.get("confidence", 0.5)),
                    "reasoning": classification_data.get("reasoning", "")
                }
                
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Erreur parsing classification JSON : {e}")
                return {"type": DocumentType.AUTRE, "confidence": 0.3, "reasoning": "Erreur de parsing"}
                
        except Exception as e:
            self.logger.error(f"Erreur classification : {e}")
            return {"type": DocumentType.AUTRE, "confidence": 0.0, "reasoning": str(e)}
    
    async def _extract_key_information(self, text: str) -> Dict[str, Any]:
        """Extrait les informations clés du document"""
        try:
            prompt = self.prompts["key_extraction"].format(text=text[:2000])
            
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=200,
                verbose=False
            )
            
            # Parser la réponse JSON
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                
                key_info = json.loads(json_str)
                return key_info.get("informations_cles", {})
                
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Erreur parsing key extraction JSON : {e}")
                return {"error": "Erreur de parsing des informations clés"}
                
        except Exception as e:
            self.logger.error(f"Erreur extraction informations clés : {e}")
            return {"error": str(e)}
    
    async def _summarize_document(self, text: str) -> str:
        """Crée un résumé du document"""
        try:
            prompt = self.prompts["summarization"].format(text=text[:1500])
            
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=150,
                verbose=False
            )
            
            # Nettoyer la réponse
            summary = response.strip()
            # Supprimer le prompt echo éventuel
            if "Résumé en 2-3 phrases" in summary:
                summary = summary.split("Résumé en 2-3 phrases")[1].strip()
            
            return summary or "Résumé non disponible"
            
        except Exception as e:
            self.logger.error(f"Erreur résumé : {e}")
            return f"Erreur de résumé : {str(e)}"
    
    async def _analyze_compliance(self, text: str) -> Dict[str, Any]:
        """Analyse la conformité du document"""
        try:
            prompt = self.prompts["compliance"].format(text=text[:1500])
            
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=200,
                verbose=False
            )
            
            # Parser la réponse JSON
            try:
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                json_str = response[json_start:json_end]
                
                compliance_data = json.loads(json_str)
                return compliance_data
                
            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Erreur parsing compliance JSON : {e}")
                return {"conformite": "non_évalué", "error": "Erreur de parsing"}
                
        except Exception as e:
            self.logger.error(f"Erreur analyse conformité : {e}")
            return {"conformite": "erreur", "error": str(e)}
    
    def get_supported_document_types(self) -> List[str]:
        """Retourne la liste des types de documents supportés"""
        return [doc_type.value for doc_type in DocumentType]
    
    def get_supported_analysis_types(self) -> List[str]:
        """Retourne la liste des types d'analyse supportés"""
        return [analysis_type.value for analysis_type in AnalysisType]


# Service FastAPI
document_analyzer = DocumentAnalyzer()

app = FastAPI(
    title="Document Analyzer Service (MLX Native)",
    description="Service d'analyse documentaire intelligent utilisant Mistral 7B MLX",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialise le service au démarrage"""
    await document_analyzer.initialize()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "document_analyzer",
        "model_loaded": document_analyzer.model is not None,
        "supported_types": document_analyzer.get_supported_document_types(),
        "supported_analyses": document_analyzer.get_supported_analysis_types()
    }


@app.post("/analyze")
async def analyze_document_endpoint(request: DocumentAnalysisRequest):
    """Analyse un document"""
    try:
        # Convertir les strings en enums
        analysis_types = []
        for analysis_str in request.analysis_types:
            try:
                analysis_types.append(AnalysisType(analysis_str))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Type d'analyse non supporté: {analysis_str}")
        
        result = await document_analyzer.analyze_document(
            text=request.text,
            analysis_types=analysis_types,
            document_context=request.document_context
        )
        
        # Convertir le résultat pour la sérialisation JSON
        return {
            "success": True,
            "result": {
                "document_type": result.document_type.value,
                "confidence": result.confidence,
                "summary": result.summary,
                "key_information": result.key_information,
                "entities": result.entities,
                "sentiment": result.sentiment,
                "compliance_status": result.compliance_status,
                "processing_time": result.processing_time
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur endpoint analyze : {e}")
        return {"success": False, "error": str(e)}


@app.get("/document-types")
async def get_document_types():
    """Retourne les types de documents supportés"""
    return {
        "document_types": document_analyzer.get_supported_document_types()
    }


@app.get("/analysis-types")  
async def get_analysis_types():
    """Retourne les types d'analyse supportés"""
    return {
        "analysis_types": document_analyzer.get_supported_analysis_types()
    }


if __name__ == "__main__":
    print("🔍 Démarrage Document Analyzer Service MLX")
    print("Port: 8004")
    print("Modèle: Mistral-7B-Instruct-v0.3-4bit")
    
    uvicorn.run(
        "document_analyzer:app",
        host="127.0.0.1",
        port=8004,
        reload=False,
        log_level="info"
    )