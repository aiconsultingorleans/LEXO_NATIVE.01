"""
Système de retrieval de contexte intelligent pour RAG.
Orchestration des composants de recherche et génération de contexte optimal.
"""
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import re

from .document_collections import collection_manager, DocumentType
from .embeddings_pipeline import embeddings_pipeline
from .mistral_wrapper import mistral_wrapper
from .prompt_system import prompt_system, PromptType

logger = logging.getLogger(__name__)

@dataclass
class RetrievalConfig:
    """Configuration pour le retrieval de contexte."""
    max_documents: int = 5
    min_similarity_score: float = 0.3
    context_length_limit: int = 4000
    enable_reranking: bool = True
    enable_query_expansion: bool = True
    diversify_sources: bool = True

class ContextRetriever:
    """Service de retrieval de contexte intelligent."""
    
    def __init__(self, config: Optional[RetrievalConfig] = None):
        self.config = config or RetrievalConfig()
        self.query_cache = {}
        self.retrieval_stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "avg_response_time": 0.0
        }
    
    async def retrieve_context(
        self,
        query: str,
        document_types: Optional[List[DocumentType]] = None,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Récupère le contexte optimal pour une requête.
        
        Args:
            query: Requête utilisateur
            document_types: Types de documents à privilégier
            user_context: Contexte utilisateur (historique, préférences)
            
        Returns:
            Contexte structuré avec documents pertinents
        """
        try:
            start_time = datetime.now()
            self.retrieval_stats["total_queries"] += 1
            
            # Vérification du cache
            cache_key = self._generate_cache_key(query, document_types)
            if cache_key in self.query_cache:
                self.retrieval_stats["cache_hits"] += 1
                logger.info(f"Cache hit pour requête: {query[:50]}...")
                return self.query_cache[cache_key]
            
            # Expansion de la requête si activée
            expanded_queries = await self._expand_query(query) if self.config.enable_query_expansion else [query]
            
            # Recherche multi-sources
            raw_results = await self._multi_source_search(expanded_queries, document_types)
            
            # Reranking si activé
            if self.config.enable_reranking and len(raw_results) > 1:
                reranked_results = await self._rerank_results(query, raw_results)
            else:
                reranked_results = raw_results
            
            # Diversification des sources
            if self.config.diversify_sources:
                diversified_results = self._diversify_sources(reranked_results)
            else:
                diversified_results = reranked_results
            
            # Construction du contexte final
            context = self._build_context(query, diversified_results, user_context)
            
            # Mise en cache
            retrieval_time = (datetime.now() - start_time).total_seconds()
            self.query_cache[cache_key] = context
            
            # Mise à jour des stats
            self._update_stats(retrieval_time)
            
            logger.info(f"Contexte récupéré: {len(context['documents'])} docs en {retrieval_time:.2f}s")
            
            return context
            
        except Exception as e:
            logger.error(f"Erreur retrieval contexte: {e}")
            return self._get_fallback_context(query)
    
    async def _expand_query(self, query: str) -> List[str]:
        """Expanse une requête avec des variantes."""
        try:
            expanded = [query]  # Requête originale
            
            # Expansion basique par synonymes
            synonyms_map = {
                "facture": ["devis", "invoice", "note"],
                "contrat": ["accord", "convention", "agreement"],
                "montant": ["somme", "prix", "coût", "total"],
                "date": ["échéance", "délai", "période"],
                "client": ["société", "entreprise", "company"]
            }
            
            query_lower = query.lower()
            for term, synonyms in synonyms_map.items():
                if term in query_lower:
                    for synonym in synonyms:
                        expanded.append(query_lower.replace(term, synonym))
            
            # Expansion par analyse grammaticale simple
            if "quel" in query_lower:
                expanded.append(query.replace("quel", "recherche"))
            if "où" in query_lower:
                expanded.append(query.replace("où", "lieu"))
            
            # Limitation du nombre d'expansions
            return expanded[:5]
            
        except Exception as e:
            logger.warning(f"Erreur expansion requête: {e}")
            return [query]
    
    async def _multi_source_search(
        self,
        queries: List[str],
        document_types: Optional[List[DocumentType]] = None
    ) -> List[Dict[str, Any]]:
        """Recherche dans plusieurs sources avec plusieurs requêtes."""
        try:
            all_results = []
            
            # Recherche pour chaque requête
            for query in queries:
                if document_types:
                    # Recherche dans types spécifiques
                    for doc_type in document_types:
                        results = collection_manager.search_in_collection(
                            doc_type,
                            query,
                            n_results=self.config.max_documents
                        )
                        all_results.extend(results)
                else:
                    # Recherche globale
                    results = collection_manager.search_all_collections(
                        query,
                        n_results=self.config.max_documents
                    )
                    all_results.extend(results)
            
            # Déduplication par ID
            seen_ids = set()
            unique_results = []
            for result in all_results:
                if result["id"] not in seen_ids:
                    seen_ids.add(result["id"])
                    unique_results.append(result)
            
            # Filtrage par score minimum
            filtered_results = [
                result for result in unique_results
                if result.get("score", 0.0) >= self.config.min_similarity_score
            ]
            
            # Tri par score décroissant
            filtered_results.sort(key=lambda x: x.get("score", 0.0), reverse=True)
            
            return filtered_results[:self.config.max_documents]
            
        except Exception as e:
            logger.error(f"Erreur recherche multi-sources: {e}")
            return []
    
    async def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerange les résultats avec un modèle plus sophistiqué."""
        try:
            if len(results) <= 1:
                return results
            
            # Pour l'instant, reranking simple basé sur plusieurs critères
            scored_results = []
            
            for result in results:
                score = result.get("score", 0.0)
                metadata = result.get("metadata", {})
                text = result.get("text", "")
                
                # Facteurs de reranking
                rerank_score = score
                
                # Bonus pour correspondance exacte de mots
                query_words = set(query.lower().split())
                text_words = set(text.lower().split())
                word_overlap = len(query_words.intersection(text_words)) / len(query_words)
                rerank_score += word_overlap * 0.2
                
                # Bonus pour documents récents
                indexed_at = metadata.get("indexed_at")
                if indexed_at:
                    try:
                        indexed_date = datetime.fromisoformat(indexed_at.replace('Z', '+00:00'))
                        days_old = (datetime.now() - indexed_date.replace(tzinfo=None)).days
                        if days_old < 30:  # Bonus pour docs < 30 jours
                            rerank_score += 0.1
                    except:
                        pass
                
                # Bonus pour certains types de documents
                doc_type = metadata.get("document_type")
                if doc_type in ["facture", "contrat"]:  # Types importants
                    rerank_score += 0.05
                
                # Pénalité pour documents très courts ou très longs
                text_length = len(text)
                if text_length < 100 or text_length > 5000:
                    rerank_score -= 0.1
                
                result_copy = result.copy()
                result_copy["rerank_score"] = rerank_score
                scored_results.append(result_copy)
            
            # Tri par nouveau score
            scored_results.sort(key=lambda x: x["rerank_score"], reverse=True)
            
            logger.info(f"Reranking: {len(results)} résultats réorganisés")
            
            return scored_results
            
        except Exception as e:
            logger.warning(f"Erreur reranking: {e}")
            return results
    
    def _diversify_sources(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Diversifie les sources pour éviter la redondance."""
        try:
            if len(results) <= 2:
                return results
            
            diversified = []
            seen_sources = set()
            seen_types = set()
            
            # Premier passage: prendre le meilleur de chaque source/type
            for result in results:
                metadata = result.get("metadata", {})
                filename = metadata.get("filename", "unknown")
                doc_type = metadata.get("document_type", "unknown")
                
                source_key = f"{filename}_{doc_type}"
                
                if source_key not in seen_sources:
                    diversified.append(result)
                    seen_sources.add(source_key)
                    seen_types.add(doc_type)
                
                if len(diversified) >= self.config.max_documents:
                    break
            
            # Deuxième passage: compléter si nécessaire
            if len(diversified) < self.config.max_documents:
                for result in results:
                    if result not in diversified:
                        diversified.append(result)
                        if len(diversified) >= self.config.max_documents:
                            break
            
            logger.info(f"Diversification: {len(seen_types)} types de docs, {len(seen_sources)} sources")
            
            return diversified
            
        except Exception as e:
            logger.warning(f"Erreur diversification: {e}")
            return results
    
    def _build_context(
        self,
        query: str,
        results: List[Dict[str, Any]],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Construit le contexte final structuré."""
        try:
            # Préparation des documents
            documents = []
            total_length = 0
            
            for i, result in enumerate(results):
                if total_length >= self.config.context_length_limit:
                    break
                
                text = result.get("text", "")
                metadata = result.get("metadata", {})
                
                # Troncature si nécessaire
                remaining_space = self.config.context_length_limit - total_length
                if len(text) > remaining_space:
                    text = text[:remaining_space - 3] + "..."
                
                document = {
                    "id": result["id"],
                    "text": text,
                    "score": result.get("score", 0.0),
                    "rerank_score": result.get("rerank_score", result.get("score", 0.0)),
                    "metadata": {
                        "filename": metadata.get("filename", f"document_{i+1}"),
                        "document_type": metadata.get("document_type", "unknown"),
                        "indexed_at": metadata.get("indexed_at"),
                        "confidence": metadata.get("ocr_confidence", 0.0)
                    }
                }
                
                documents.append(document)
                total_length += len(text)
            
            # Analyse du contexte
            context_analysis = self._analyze_context(query, documents)
            
            # Construction du contexte final
            context = {
                "query": query,
                "documents": documents,
                "total_documents": len(documents),
                "total_length": total_length,
                "retrieval_timestamp": datetime.now().isoformat(),
                "analysis": context_analysis,
                "config_used": {
                    "max_documents": self.config.max_documents,
                    "min_similarity_score": self.config.min_similarity_score,
                    "reranking_enabled": self.config.enable_reranking,
                    "diversification_enabled": self.config.diversify_sources
                }
            }
            
            # Ajout du contexte utilisateur si fourni
            if user_context:
                context["user_context"] = user_context
            
            return context
            
        except Exception as e:
            logger.error(f"Erreur construction contexte: {e}")
            return self._get_fallback_context(query)
    
    def _analyze_context(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse le contexte récupéré."""
        try:
            if not documents:
                return {"quality": "empty", "confidence": 0.0}
            
            # Statistiques de base
            scores = [doc["score"] for doc in documents]
            avg_score = sum(scores) / len(scores)
            max_score = max(scores)
            min_score = min(scores)
            
            # Types de documents
            doc_types = [doc["metadata"]["document_type"] for doc in documents]
            unique_types = set(doc_types)
            
            # Analyse de la qualité
            quality = "good"
            if avg_score < 0.4:
                quality = "low"
            elif avg_score < 0.6:
                quality = "medium"
            elif avg_score > 0.8:
                quality = "excellent"
            
            # Estimation de confiance
            confidence = min(1.0, avg_score + (len(unique_types) * 0.1))
            
            return {
                "quality": quality,
                "confidence": confidence,
                "avg_score": avg_score,
                "score_range": {"min": min_score, "max": max_score},
                "document_types": list(unique_types),
                "type_distribution": {doc_type: doc_types.count(doc_type) for doc_type in unique_types},
                "total_length": sum(len(doc["text"]) for doc in documents)
            }
            
        except Exception as e:
            logger.warning(f"Erreur analyse contexte: {e}")
            return {"quality": "unknown", "confidence": 0.5}
    
    def _generate_cache_key(self, query: str, document_types: Optional[List[DocumentType]]) -> str:
        """Génère une clé de cache pour la requête."""
        try:
            key_parts = [query.lower().strip()]
            if document_types:
                key_parts.append("_".join(sorted(dt.value for dt in document_types)))
            return "_".join(key_parts)[:100]  # Limitation longueur
        except:
            return query[:50]
    
    def _get_fallback_context(self, query: str) -> Dict[str, Any]:
        """Contexte de fallback en cas d'erreur."""
        return {
            "query": query,
            "documents": [],
            "total_documents": 0,
            "total_length": 0,
            "retrieval_timestamp": datetime.now().isoformat(),
            "analysis": {"quality": "empty", "confidence": 0.0},
            "error": "Aucun contexte récupéré"
        }
    
    def _update_stats(self, response_time: float):
        """Met à jour les statistiques."""
        try:
            current_avg = self.retrieval_stats["avg_response_time"]
            total_queries = self.retrieval_stats["total_queries"]
            
            # Moyenne mobile
            new_avg = ((current_avg * (total_queries - 1)) + response_time) / total_queries
            self.retrieval_stats["avg_response_time"] = new_avg
            
        except Exception as e:
            logger.warning(f"Erreur mise à jour stats: {e}")
    
    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Statistiques du système de retrieval."""
        try:
            stats = self.retrieval_stats.copy()
            stats["cache_hit_rate"] = (
                stats["cache_hits"] / max(1, stats["total_queries"])
            ) * 100
            stats["cache_size"] = len(self.query_cache)
            return stats
        except Exception as e:
            logger.error(f"Erreur stats retrieval: {e}")
            return {}
    
    def clear_cache(self):
        """Vide le cache de requêtes."""
        try:
            self.query_cache.clear()
            logger.info("Cache de retrieval vidé")
        except Exception as e:
            logger.error(f"Erreur vidage cache: {e}")
    
    async def benchmark_retrieval(self, test_queries: List[str]) -> Dict[str, Any]:
        """Benchmark du système de retrieval."""
        try:
            results = {
                "queries_tested": len(test_queries),
                "results": [],
                "avg_response_time": 0.0,
                "avg_documents_found": 0.0,
                "avg_confidence": 0.0
            }
            
            total_time = 0.0
            total_docs = 0
            total_confidence = 0.0
            
            for query in test_queries:
                start_time = datetime.now()
                context = await self.retrieve_context(query)
                response_time = (datetime.now() - start_time).total_seconds()
                
                result = {
                    "query": query,
                    "response_time": response_time,
                    "documents_found": context["total_documents"],
                    "confidence": context["analysis"]["confidence"]
                }
                
                results["results"].append(result)
                total_time += response_time
                total_docs += context["total_documents"]
                total_confidence += context["analysis"]["confidence"]
            
            # Calcul des moyennes
            if test_queries:
                results["avg_response_time"] = total_time / len(test_queries)
                results["avg_documents_found"] = total_docs / len(test_queries)
                results["avg_confidence"] = total_confidence / len(test_queries)
            
            logger.info(f"Benchmark terminé: {len(test_queries)} requêtes testées")
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur benchmark: {e}")
            return {"error": str(e)}

# Instance globale du retrieveur
context_retriever = ContextRetriever()