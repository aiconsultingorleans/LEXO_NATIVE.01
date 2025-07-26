"""
Service d'analyse documentaire intelligent avec Mistral MLX
Analyse sémantique et classification avancée de documents
"""

import asyncio
import logging
import time
import json
import re
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
from enum import Enum
from functools import wraps
import threading

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

# Configuration logging détaillé
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration timeouts
MISTRAL_TIMEOUT = 30  # secondes
MISTRAL_MAX_RETRIES = 2


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


class ChatRequest(BaseModel):
    """Requête de chat conversationnel"""
    message: str
    conversation_id: Optional[str] = "default"
    max_tokens: Optional[int] = 2000
    system_prompt: Optional[str] = None


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

Extrais et structure les informations importantes (dates, montants, noms, adresses, numéros de référence, etc.) en JSON strict avec cette structure exacte :
{{"dates": [], "montants": [], "personnes": [], "entreprises": [], "references": [], "autres": {{}}}}

Réponds UNIQUEMENT par le JSON, sans texte supplémentaire.""",

            "summarization": """Tu es un expert en synthèse documentaire. Créé un résumé concis et professionnel de ce document.

Document :
{text}

Résumé en 2-3 phrases maximum, en français professionnel, sans reprendre le prompt :""",

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
            
            self.logger.info(f"Analyse terminée en {result.processing_time:.2f}s - Type: {result.document_type.value if hasattr(result.document_type, 'value') else result.document_type} (conf: {result.confidence:.2f})")
            return result
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse documentaire : {e}")
            raise HTTPException(status_code=500, detail=f"Erreur d'analyse : {str(e)}")
    
    def _timeout_wrapper(self, func, *args, **kwargs):
        """Wrapper pour ajouter timeout aux générations Mistral"""
        result = {'value': None, 'error': None}
        
        def target():
            try:
                result['value'] = func(*args, **kwargs)
            except Exception as e:
                result['error'] = e
        
        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=MISTRAL_TIMEOUT)
        
        if thread.is_alive():
            self.logger.error(f"Timeout Mistral après {MISTRAL_TIMEOUT}s")
            # Note: Impossible de killer proprement le thread MLX
            raise TimeoutError(f"Génération Mistral timeout après {MISTRAL_TIMEOUT}s")
        
        if result['error']:
            raise result['error']
        
        return result['value']
    
    def _robust_json_parse(self, response: str, expected_keys: List[str] = None) -> Dict[str, Any]:
        """Parse JSON robuste avec gestion d'erreurs améliorée"""
        self.logger.debug(f"Parsing JSON: {response[:200]}...")
        
        # Nettoyer la réponse
        clean_response = response.strip()
        
        # Méthode 1: Chercher le JSON dans la réponse
        json_patterns = [
            r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # JSON simple
            r'\{.*?\}',  # JSON basique
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, clean_response, re.DOTALL)
            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict):
                        # Vérifier les clés attendues si spécifiées
                        if expected_keys:
                            if any(key in parsed for key in expected_keys):
                                return parsed
                        else:
                            return parsed
                except json.JSONDecodeError:
                    continue
        
        # Méthode 2: Extraction par regex si JSON introuvable
        self.logger.warning(f"JSON non trouvé, tentative extraction regex: {clean_response[:100]}")
        
        # Fallback pour classification
        if 'type' in clean_response.lower():
            type_match = re.search(r'["\']?type["\']?\s*:\s*["\']?([^,}"\'\n]+)', clean_response, re.IGNORECASE)
            conf_match = re.search(r'["\']?confidence["\']?\s*:\s*([0-9.]+)', clean_response)
            
            if type_match:
                return {
                    'type': type_match.group(1).strip().strip('"\''),
                    'confidence': float(conf_match.group(1)) if conf_match else 0.5,
                    'reasoning': 'Extraction par regex'
                }
        
        # Fallback final
        self.logger.error(f"Impossible de parser JSON: {clean_response}")
        return {'error': 'Parsing JSON échoué', 'raw_response': clean_response[:200]}
    
    async def _classify_document(self, text: str) -> Dict[str, Any]:
        """Classifie le type de document avec gestion d'erreurs robuste"""
        for attempt in range(MISTRAL_MAX_RETRIES + 1):
            try:
                self.logger.info(f"Classification tentative {attempt + 1}/{MISTRAL_MAX_RETRIES + 1}")
                
                prompt = self.prompts["classification"].format(text=text[:2000])
                self.logger.debug(f"Prompt classification: {prompt[:100]}...")
                
                # Génération avec timeout
                response = self._timeout_wrapper(
                    generate,
                    self.model,
                    self.tokenizer,
                    prompt=prompt,
                    max_tokens=100,
                    verbose=False
                )
                
                self.logger.info(f"Réponse Mistral classification: {response[:100]}...")
            
                # Parser avec méthode robuste
                classification_data = self._robust_json_parse(response, ['type', 'confidence'])
                
                if 'error' in classification_data:
                    if attempt < MISTRAL_MAX_RETRIES:
                        self.logger.warning(f"Tentative {attempt + 1} échouée, retry...")
                        await asyncio.sleep(1)  # Petite pause avant retry
                        continue
                    else:
                        self.logger.error(f"Toutes les tentatives échouées: {classification_data}")
                        return {"type": DocumentType.AUTRE, "confidence": 0.2, "reasoning": "Parsing JSON échoué"}
                
                # Mapper vers notre enum
                doc_type_str = classification_data.get("type", "autre").lower()
                try:
                    # Mapper les variantes possibles
                    type_mapping = {
                        'rib': DocumentType.RIB,
                        'relevé identité bancaire': DocumentType.RIB,
                        'facture': DocumentType.FACTURE,
                        'invoice': DocumentType.FACTURE,
                        'contrat': DocumentType.CONTRAT,
                        'contract': DocumentType.CONTRAT,
                        'attestation': DocumentType.ATTESTATION,
                        'courrier': DocumentType.COURRIER,
                        'rapport': DocumentType.RAPPORT,
                        'autre': DocumentType.AUTRE
                    }
                    
                    doc_type = type_mapping.get(doc_type_str, DocumentType.AUTRE)
                except Exception:
                    doc_type = DocumentType.AUTRE
                
                confidence = float(classification_data.get("confidence", 0.5))
                confidence = max(0.0, min(1.0, confidence))  # Clamp entre 0 et 1
                
                result = {
                    "type": doc_type,
                    "confidence": confidence,
                    "reasoning": classification_data.get("reasoning", "")
                }
                
                self.logger.info(f"Classification réussie: {doc_type.value} (conf: {confidence:.2f})")
                return result
                
            except TimeoutError as e:
                self.logger.error(f"Timeout classification tentative {attempt + 1}: {e}")
                if attempt < MISTRAL_MAX_RETRIES:
                    continue
                else:
                    return {"type": DocumentType.AUTRE, "confidence": 0.1, "reasoning": "Timeout Mistral"}
                    
            except Exception as e:
                self.logger.error(f"Erreur classification tentative {attempt + 1}: {e}")
                if attempt < MISTRAL_MAX_RETRIES:
                    await asyncio.sleep(2)  # Pause plus longue en cas d'erreur
                    continue
                else:
                    return {"type": DocumentType.AUTRE, "confidence": 0.0, "reasoning": f"Erreur: {str(e)}"}
        
        # Fallback final si toutes les tentatives échouent
        return {"type": DocumentType.AUTRE, "confidence": 0.0, "reasoning": "Toutes tentatives échouées"}
    
    async def _extract_key_information(self, text: str) -> Dict[str, Any]:
        """Extrait les informations clés du document avec parsing robuste"""
        for attempt in range(MISTRAL_MAX_RETRIES + 1):
            try:
                self.logger.info(f"Extraction informations tentative {attempt + 1}/{MISTRAL_MAX_RETRIES + 1}")
                
                prompt = self.prompts["key_extraction"].format(text=text[:2000])
                self.logger.debug(f"Prompt extraction: {prompt[:100]}...")
                
                # Génération avec timeout
                response = self._timeout_wrapper(
                    generate,
                    self.model,
                    self.tokenizer,
                    prompt=prompt,
                    max_tokens=200,
                    verbose=False
                )
                
                self.logger.info(f"Réponse Mistral extraction: {response[:150]}...")
                
                # Parser avec méthode robuste (sans clé 'informations_cles' maintenant)
                key_info = self._robust_json_parse(response, ['dates', 'montants', 'personnes'])
                
                if 'error' in key_info:
                    if attempt < MISTRAL_MAX_RETRIES:
                        self.logger.warning(f"Extraction tentative {attempt + 1} échouée, retry...")
                        await asyncio.sleep(1)
                        continue
                    else:
                        # Fallback: Extraction basique par regex
                        self.logger.warning("Fallback extraction regex")
                        return self._fallback_extraction(text)
                
                # Valider et nettoyer la structure
                validated_info = self._validate_extracted_info(key_info)
                
                self.logger.info(f"Extraction réussie: {len(validated_info)} catégories")
                return validated_info
                
            except TimeoutError as e:
                self.logger.error(f"Timeout extraction tentative {attempt + 1}: {e}")
                if attempt < MISTRAL_MAX_RETRIES:
                    continue
                else:
                    return self._fallback_extraction(text)
                    
            except Exception as e:
                self.logger.error(f"Erreur extraction tentative {attempt + 1}: {e}")
                if attempt < MISTRAL_MAX_RETRIES:
                    await asyncio.sleep(2)
                    continue
                else:
                    return self._fallback_extraction(text)
        
        # Fallback final
        return self._fallback_extraction(text)
    
    def _validate_extracted_info(self, info: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et nettoie les informations extraites"""
        validated = {
            "dates": [],
            "montants": [],
            "personnes": [],
            "entreprises": [],
            "references": [],
            "autres": {}
        }
        
        for key in validated.keys():
            if key in info:
                value = info[key]
                if isinstance(value, list):
                    validated[key] = [str(item) for item in value if item]  # Nettoyer les valeurs vides
                elif isinstance(value, dict):
                    validated[key] = {k: str(v) for k, v in value.items() if v}
                else:
                    if key == "autres":
                        validated[key] = {"info": str(value)} if value else {}
                    else:
                        validated[key] = [str(value)] if value else []
        
        return validated
    
    def _fallback_extraction(self, text: str) -> Dict[str, Any]:
        """Extraction de secours par regex si Mistral échoue"""
        self.logger.info("Utilisation extraction fallback par regex")
        
        result = {
            "dates": [],
            "montants": [],
            "personnes": [],
            "entreprises": [],
            "references": [],
            "autres": {"extraction_type": "fallback_regex"}
        }
        
        # Extraction dates
        date_patterns = [
            r'\b\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}\b',
            r'\b\d{1,2}\s+[a-zéèêôà]+\s+\d{4}\b'
        ]
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            result["dates"].extend(matches[:5])  # Limiter à 5
        
        # Extraction montants
        montant_patterns = [
            r'\b\d+[,\.]\d{2}\s*€\b',
            r'\b\d+[,\.]\d{2}\s*euros?\b',
            r'\btotal\s*:?\s*\d+[,\.]\d{2}\b'
        ]
        for pattern in montant_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            result["montants"].extend(matches[:3])  # Limiter à 3
        
        # Extraction références
        ref_patterns = [
            r'\bn[u°\s]*\d{6,}\b',
            r'\bref[\s\.:]*\w+\d+\b',
            r'\bfacture[\s\.:]*\w*\d+\b'
        ]
        for pattern in ref_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            result["references"].extend(matches[:3])
        
        # Nettoyer et dédupliquer
        for key in ["dates", "montants", "references"]:
            result[key] = list(set(result[key]))[:5]  # Dédoublonner et limiter
        
        return result
    
    async def _summarize_document(self, text: str) -> str:
        """Crée un résumé du document"""
        try:
            # Nettoyer le texte d'entrée
            clean_text = text.replace('\n', ' ').strip()[:1500]
            prompt = self.prompts["summarization"].format(text=clean_text)
            
            self.logger.info(f"Génération résumé avec prompt de {len(prompt)} caractères")
            
            response = generate(
                self.model,
                self.tokenizer,
                prompt=prompt,
                max_tokens=200,
                verbose=False
            )
            
            self.logger.info(f"Réponse Mistral brute: {response[:100]}...")
            
            # Nettoyer la réponse en profondeur
            summary = response.strip()
            
            # Supprimer le prompt entier qui peut être répété
            prompt_phrases = [
                "Tu es un expert en synthèse documentaire",
                "Créé un résumé concis",
                "Document :",
                "Résumé en 2-3 phrases",
                "maximum, en français professionnel",
                "sans reprendre le prompt"
            ]
            
            for phrase in prompt_phrases:
                if phrase in summary:
                    parts = summary.split(phrase)
                    summary = parts[-1].strip()
            
            # Supprimer les éventuels préfixes et suffixes
            prefixes_to_remove = [":", "Document", "Résumé", "-"]
            for prefix in prefixes_to_remove:
                if summary.startswith(prefix):
                    summary = summary[len(prefix):].strip()
            
            # Supprimer les répétitions de texte original
            if len(summary) > 200 and clean_text[:50] in summary:
                # Le résumé contient le texte original, on extrait seulement la fin
                summary_start = summary.rfind(clean_text[:50])
                if summary_start > 0:
                    summary = summary[summary_start + len(clean_text[:50]):].strip()
            
            # Nettoyer les lignes vides et les caractères indésirables
            summary = ' '.join(summary.split())
            
            # Si le résumé contient encore des fragments du prompt, le raccourcir
            if any(p in summary.lower() for p in ["expert", "analyse", "document :", "résumé"]):
                sentences = summary.split('.')
                clean_sentences = []
                for sentence in sentences:
                    if not any(p in sentence.lower() for p in ["expert", "analyse document", "tu es"]):
                        clean_sentences.append(sentence.strip())
                summary = '. '.join(clean_sentences).strip()
                if summary and not summary.endswith('.'):
                    summary += '.'
            
            # Validation finale
            if len(summary) < 10:
                summary = f"Document analysé contenant {len(text.split())} mots. Contenu principal extrait."
            
            return summary[:500]  # Limiter la taille
            
        except Exception as e:
            self.logger.error(f"Erreur résumé : {e}")
            return f"Document traité automatiquement. Contenu de {len(text.split()) if text else 0} mots analysé."
    
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

# Stockage des conversations en mémoire (simple pour MVP)
conversations_storage = {}

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
    allow_methods=["GET", "POST", "DELETE"],
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


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Endpoint de chat conversationnel avec Mistral"""
    try:
        # Prompt système par défaut
        default_system_prompt = """Tu es Mistral, un assistant IA spécialisé dans l'analyse de documents administratifs pour LEXO v1.

CONTEXTE:
- Tu aides les utilisateurs à analyser leurs documents (factures, RIB, impôts, attestations, contrats)
- Tu peux expliquer le contenu des documents, extraire des informations clés, et répondre aux questions
- Les documents ont déjà été traités par OCR et analyse préliminaire

CAPACITÉS:
- Analyse et résumé de documents
- Extraction d'informations clés (dates, montants, entités)
- Classification et catégorisation
- Réponse aux questions sur le contenu
- Conseils sur l'organisation documentaire

STYLE:
- Sois professionnel mais accessible
- Utilise un langage clair et précis
- Structure tes réponses avec des puces ou sections si nécessaire
- Cite les éléments spécifiques du document quand pertinent
- Si tu n'es pas sûr, indique-le clairement

SÉCURITÉ:
- Ne jamais révéler d'informations personnelles sensibles
- Respecter la confidentialité
- Signaler si un document semble contenir des données sensibles"""

        # Utiliser le prompt système fourni ou celui par défaut
        system_prompt = request.system_prompt or default_system_prompt
        
        # Construire le prompt complet
        full_prompt = f"{system_prompt}\n\nUser: {request.message}\nAssistant:"
        
        # Générer la réponse avec Mistral
        if document_analyzer.model is None:
            raise HTTPException(status_code=503, detail="Modèle Mistral non chargé")
        
        start_time = time.time()
        
        # Générer la réponse
        response = generate(
            document_analyzer.model,
            document_analyzer.tokenizer,
            prompt=full_prompt,
            max_tokens=request.max_tokens,
            verbose=False
        )
        
        processing_time = time.time() - start_time
        
        # Nettoyer la réponse (retirer le prompt)
        if response.startswith(full_prompt):
            response = response[len(full_prompt):].strip()
        
        # Compter les tokens (approximation)
        tokens_used = len(response.split())
        
        # Stocker dans l'historique des conversations
        if request.conversation_id not in conversations_storage:
            conversations_storage[request.conversation_id] = {"messages": []}
        
        # Ajouter le message utilisateur et la réponse à l'historique
        conversations_storage[request.conversation_id]["messages"].extend([
            {
                "role": "user",
                "content": request.message,
                "timestamp": time.time()
            },
            {
                "role": "assistant", 
                "content": response,
                "timestamp": time.time(),
                "tokens_used": tokens_used
            }
        ])
        
        return {
            "response": response,
            "conversation_id": request.conversation_id,
            "tokens_used": tokens_used,
            "processing_time": processing_time,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Erreur endpoint chat : {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de génération: {str(e)}")


@app.get("/conversations/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """Récupérer l'historique d'une conversation"""
    try:
        conversation = conversations_storage.get(conversation_id, {"messages": []})
        return {
            "conversation_id": conversation_id,
            "messages": conversation["messages"]
        }
    except Exception as e:
        logger.error(f"Erreur récupération conversation : {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/conversations/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Effacer une conversation"""
    try:
        if conversation_id in conversations_storage:
            del conversations_storage[conversation_id]
        return {
            "success": True,
            "message": f"Conversation {conversation_id} effacée"
        }
    except Exception as e:
        logger.error(f"Erreur effacement conversation : {e}")
        raise HTTPException(status_code=500, detail=str(e))


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