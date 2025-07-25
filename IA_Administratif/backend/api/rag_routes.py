"""
Routes API pour les fonctionnalités RAG (Recherche sémantique et Chat).
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, Query, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.database import get_db
from core.auth import get_current_user
from models.user import User
from rag.document_collections import collection_manager, DocumentType
from rag.mistral_wrapper import mistral_wrapper
from rag.prompt_system import prompt_system, PromptType
from rag.apple_silicon_optimizer import apple_optimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])

# === Modèles Pydantic ===

class SearchRequest(BaseModel):
    """Requête de recherche sémantique."""
    query: str = Field(..., min_length=3, max_length=500, description="Requête de recherche")
    document_type: Optional[str] = Field(None, description="Type de document à filtrer")
    max_results: int = Field(10, ge=1, le=50, description="Nombre maximum de résultats")
    include_metadata: bool = Field(True, description="Inclure les métadonnées")
    min_score: float = Field(0.0, ge=0.0, le=1.0, description="Score minimum de pertinence")

class SearchResult(BaseModel):
    """Résultat de recherche."""
    id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    document_type: str
    highlighted_text: Optional[str] = None

class SearchResponse(BaseModel):
    """Réponse de recherche sémantique."""
    query: str
    results: List[SearchResult]
    total_found: int
    search_time_ms: float
    suggestions: List[str] = []

class ChatRequest(BaseModel):
    """Requête de chat RAG."""
    message: str = Field(..., min_length=1, max_length=1000, description="Message utilisateur")
    conversation_id: Optional[str] = Field(None, description="ID de conversation")
    document_context: Optional[List[str]] = Field(None, description="IDs de documents pour contexte")
    stream_response: bool = Field(False, description="Réponse en streaming")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Créativité de la réponse")

class ChatResponse(BaseModel):
    """Réponse de chat RAG."""
    response: str
    conversation_id: str
    sources: List[Dict[str, Any]] = []
    confidence: float
    response_time_ms: float
    token_usage: Dict[str, int] = {}

class DocumentAnalysisRequest(BaseModel):
    """Requête d'analyse de document."""
    document_id: str = Field(..., description="ID du document à analyser")
    question: str = Field(..., min_length=5, max_length=500, description="Question sur le document")
    analysis_type: str = Field("general", description="Type d'analyse")

# === Endpoints de Recherche Sémantique ===

@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Recherche sémantique dans les documents indexés.
    """
    try:
        start_time = datetime.now()
        
        # Validation du type de document
        doc_type = None
        if request.document_type:
            try:
                doc_type = DocumentType[request.document_type.upper()]
            except KeyError:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Type de document invalide: {request.document_type}"
                )
        
        # Recherche dans les collections
        if doc_type:
            raw_results = collection_manager.search_in_collection(
                doc_type, 
                request.query, 
                request.max_results
            )
        else:
            raw_results = collection_manager.search_all_collections(
                request.query, 
                request.max_results
            )
        
        # Filtrage par score minimum
        filtered_results = [
            result for result in raw_results 
            if result.get("score", 0.0) >= request.min_score
        ]
        
        # Formatage des résultats
        search_results = []
        for result in filtered_results:
            metadata = result.get("metadata", {})
            
            search_result = SearchResult(
                id=result["id"],
                text=result["text"],
                score=result.get("score", 0.0),
                metadata=metadata if request.include_metadata else {},
                document_type=metadata.get("document_type", "unknown"),
                highlighted_text=_highlight_query_in_text(result["text"], request.query)
            )
            search_results.append(search_result)
        
        # Calcul du temps de recherche
        search_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Suggestions de recherche
        suggestions = _generate_search_suggestions(request.query, search_results)
        
        response = SearchResponse(
            query=request.query,
            results=search_results,
            total_found=len(search_results),
            search_time_ms=round(search_time, 2),
            suggestions=suggestions
        )
        
        logger.info(f"Recherche '{request.query}': {len(search_results)} résultats en {search_time:.0f}ms")
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur recherche sémantique: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur de recherche: {str(e)}")

@router.get("/search/suggestions")
async def get_search_suggestions(
    query: str = Query(..., min_length=2, description="Début de requête"),
    limit: int = Query(5, ge=1, le=10, description="Nombre de suggestions"),
    current_user: User = Depends(get_current_user)
):
    """
    Suggestions de recherche basées sur une requête partielle.
    """
    try:
        # Pour l'instant, suggestions basiques
        # TODO: Implémenter un système de suggestions plus avancé
        suggestions = [
            f"{query} dans les factures",
            f"{query} dans les contrats", 
            f"{query} montant",
            f"{query} date",
            f"résumé {query}"
        ]
        
        return {"suggestions": suggestions[:limit]}
        
    except Exception as e:
        logger.error(f"Erreur suggestions: {e}")
        raise HTTPException(status_code=500, detail="Erreur génération suggestions")

# === Endpoints de Chat RAG ===

@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat intelligent avec les documents indexés.
    """
    try:
        start_time = datetime.now()
        
        # Initialisation de Mistral si nécessaire
        if not mistral_wrapper.is_loaded:
            await mistral_wrapper.initialize()
        
        # Recherche du contexte pertinent
        context_results = collection_manager.search_all_collections(
            request.message, 
            n_results=5  # Top 5 documents pertinents
        )
        
        # Génération du prompt RAG
        prompt_data = prompt_system.get_rag_search_prompt(
            request.message,
            context_results
        )
        
        # Génération de la réponse
        if request.stream_response:
            # Réponse en streaming
            return StreamingResponse(
                _stream_chat_response(request, prompt_data, context_results),
                media_type="text/plain"
            )
        else:
            # Réponse standard
            response_text = await mistral_wrapper.generate_response(
                prompt_data["user_prompt"],
                temperature=request.temperature,
                system_prompt=prompt_data["system_prompt"],
                max_tokens=prompt_data["config"]["max_tokens"]
            )
        
        # Calcul du temps de réponse
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Formatage des sources
        sources = [
            {
                "document_id": result["id"],
                "filename": result.get("metadata", {}).get("filename", "Unknown"),
                "score": result.get("score", 0.0),
                "excerpt": result["text"][:200] + "..."
            }
            for result in context_results[:3]  # Top 3 sources
        ]
        
        # Estimation de la confiance
        confidence = _estimate_response_confidence(response_text, context_results)
        
        response = ChatResponse(
            response=response_text or "Désolé, je n'ai pas pu générer de réponse.",
            conversation_id=request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
            sources=sources,
            confidence=confidence,
            response_time_ms=round(response_time, 2),
            token_usage={"prompt_tokens": 0, "completion_tokens": 0}  # TODO: compter tokens
        )
        
        logger.info(f"Chat réponse générée en {response_time:.0f}ms")
        
        return response
        
    except Exception as e:
        logger.error(f"Erreur chat RAG: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur génération réponse: {str(e)}")

@router.post("/analyze-document", response_model=Dict[str, Any])
async def analyze_document(
    request: DocumentAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyse spécialisée d'un document spécifique.
    """
    try:
        # Recherche du document dans les collections
        document_found = None
        for doc_type in DocumentType:
            results = collection_manager.search_in_collection(
                doc_type,
                request.document_id,
                n_results=1,
                filters={"document_id": request.document_id}
            )
            if results:
                document_found = results[0]
                break
        
        if not document_found:
            raise HTTPException(
                status_code=404, 
                detail=f"Document {request.document_id} non trouvé"
            )
        
        # Analyse avec Mistral
        if not mistral_wrapper.is_loaded:
            await mistral_wrapper.initialize()
        
        analysis_result = await mistral_wrapper.analyze_document_content(
            document_found["text"],
            request.question,
            document_found.get("metadata", {})
        )
        
        return {
            "document_id": request.document_id,
            "question": request.question,
            "analysis": analysis_result,
            "document_metadata": document_found.get("metadata", {}),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur analyse document: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur analyse: {str(e)}")

# === Endpoints Utilitaires ===

@router.get("/stats")
async def get_rag_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Statistiques du système RAG.
    """
    try:
        # Stats collections
        collection_stats = collection_manager.get_collection_stats()
        
        # Stats modèle
        model_info = mistral_wrapper.get_model_info()
        
        # Stats système
        system_stats = apple_optimizer.monitor_performance()
        
        return {
            "collections": collection_stats,
            "model": model_info,
            "system": system_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur stats RAG: {e}")
        raise HTTPException(status_code=500, detail="Erreur récupération statistiques")

@router.post("/optimize")
async def optimize_system(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """
    Lance les optimisations Apple Silicon en arrière-plan.
    """
    try:
        background_tasks.add_task(apple_optimizer.apply_all_optimizations)
        
        return {
            "message": "Optimisations lancées en arrière-plan",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Erreur lancement optimisations: {e}")
        raise HTTPException(status_code=500, detail="Erreur lancement optimisations")

# === Fonctions Utilitaires ===

def _highlight_query_in_text(text: str, query: str) -> str:
    """Surligne les termes de la requête dans le texte."""
    try:
        # Simple highlighting (à améliorer)
        words = query.lower().split()
        highlighted = text
        
        for word in words:
            if len(word) > 2:  # Mots de plus de 2 caractères
                highlighted = highlighted.replace(
                    word, 
                    f"**{word}**"
                )
        
        return highlighted
        
    except Exception as e:
        logger.warning(f"Erreur highlighting: {e}")
        return text

def _generate_search_suggestions(query: str, results: List[SearchResult]) -> List[str]:
    """Génère des suggestions de recherche."""
    try:
        suggestions = []
        
        # Suggestions basées sur les types de documents trouvés
        doc_types = set(result.document_type for result in results)
        for doc_type in doc_types:
            suggestions.append(f"{query} dans {doc_type}")
        
        # Suggestions génériques
        suggestions.extend([
            f"résumé {query}",
            f"{query} montant",
            f"{query} date"
        ])
        
        return suggestions[:5]
        
    except Exception as e:
        logger.warning(f"Erreur suggestions: {e}")
        return []

async def _stream_chat_response(
    request: ChatRequest, 
    prompt_data: Dict[str, Any], 
    context_results: List[Dict[str, Any]]
):
    """Génère une réponse en streaming."""
    try:
        async for chunk in mistral_wrapper.generate_streaming_response(
            prompt_data["user_prompt"],
            temperature=request.temperature,
            system_prompt=prompt_data["system_prompt"],
            max_tokens=prompt_data["config"]["max_tokens"]
        ):
            yield f"data: {chunk}\n\n"
        
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Erreur streaming: {e}")
        yield f"data: Erreur: {str(e)}\n\n"

def _estimate_response_confidence(response: str, context_results: List[Dict[str, Any]]) -> float:
    """Estime la confiance dans la réponse."""
    try:
        if not response or not context_results:
            return 0.0
        
        # Facteurs de confiance
        confidence = 0.5  # Base
        
        # Longueur appropriée
        if 50 <= len(response) <= 1000:
            confidence += 0.2
        
        # Présence de sources
        if len(context_results) >= 3:
            confidence += 0.2
        
        # Score moyen des sources
        avg_score = sum(r.get("score", 0.0) for r in context_results) / len(context_results)
        confidence += avg_score * 0.3
        
        return min(1.0, max(0.0, confidence))
        
    except Exception as e:
        logger.warning(f"Erreur estimation confiance: {e}")
        return 0.5