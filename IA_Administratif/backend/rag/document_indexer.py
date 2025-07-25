"""
Service d'indexation des documents dans ChromaDB.
Intégration avec le pipeline OCR pour indexation automatique.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncio
import uuid
from pathlib import Path

from .document_collections import collection_manager, DocumentType
from .text_chunking import text_chunker

logger = logging.getLogger(__name__)

class DocumentIndexer:
    """Service d'indexation des documents."""
    
    def __init__(self):
        self.processed_documents = set()
    
    async def index_document_from_ocr(
        self,
        document_data: Dict[str, Any],
        ocr_result: Dict[str, Any]
    ) -> bool:
        """
        Indexe un document à partir des résultats OCR.
        
        Args:
            document_data: Métadonnées du document (id, filename, etc.)
            ocr_result: Résultats de l'OCR avec texte extrait
        """
        try:
            document_id = document_data.get("id") or str(uuid.uuid4())
            
            if document_id in self.processed_documents:
                logger.warning(f"Document {document_id} déjà indexé")
                return True
            
            # Extraction du texte principal
            text_content = self._extract_text_from_ocr(ocr_result)
            if not text_content or len(text_content.strip()) < 10:
                logger.warning(f"Texte insuffisant pour l'indexation: {document_id}")
                return False
            
            # Préparation des métadonnées enrichies
            metadata = self._prepare_metadata(document_data, ocr_result)
            
            # Classification automatique du type de document
            predicted_type = self._predict_document_type(ocr_result)
            
            # Chunking du texte pour de meilleurs embeddings
            chunks = text_chunker.chunk_text(text_content, metadata)
            
            # Indexation par chunks
            success = True
            for i, chunk in enumerate(chunks):
                chunk_id = f"{document_id}_chunk_{i}"
                chunk_metadata = {
                    **metadata,
                    "chunk_index": i,
                    "total_chunks": len(chunks),
                    "parent_document_id": document_id
                }
                
                chunk_success = collection_manager.classify_and_add_document(
                    chunk_id,
                    chunk["text"],
                    chunk_metadata,
                    predicted_type
                )
                
                if not chunk_success:
                    success = False
                    logger.error(f"Échec indexation chunk {chunk_id}")
            
            if success:
                self.processed_documents.add(document_id)
                logger.info(f"Document {document_id} indexé avec succès ({len(chunks)} chunks)")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation: {e}")
            return False
    
    def _extract_text_from_ocr(self, ocr_result: Dict[str, Any]) -> str:
        """Extrait le texte principal des résultats OCR."""
        try:
            # Priorité au texte TrOCR si disponible
            if "trocr_text" in ocr_result and ocr_result["trocr_text"]:
                return ocr_result["trocr_text"]
            
            # Sinon texte Tesseract
            if "tesseract_text" in ocr_result and ocr_result["tesseract_text"]:
                return ocr_result["tesseract_text"]
            
            # Texte hybride
            if "hybrid_text" in ocr_result and ocr_result["hybrid_text"]:
                return ocr_result["hybrid_text"]
            
            # Fallback sur le texte brut
            if "text" in ocr_result and ocr_result["text"]:
                return ocr_result["text"]
            
            return ""
            
        except Exception as e:
            logger.error(f"Erreur extraction texte OCR: {e}")
            return ""
    
    def _prepare_metadata(
        self, 
        document_data: Dict[str, Any], 
        ocr_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prépare les métadonnées enrichies."""
        try:
            metadata = {
                "filename": document_data.get("filename", "unknown"),
                "file_path": document_data.get("file_path", ""),
                "file_size": document_data.get("file_size", 0),
                "created_at": document_data.get("created_at", datetime.now().isoformat()),
                "indexed_at": datetime.now().isoformat(),
                
                # Métadonnées OCR
                "ocr_confidence": ocr_result.get("confidence", 0.0),
                "ocr_engine": ocr_result.get("engine_used", "unknown"),
                "processing_time": ocr_result.get("processing_time", 0.0),
                
                # Entités extraites
                "entities": ocr_result.get("entities", {}),
                "extracted_dates": ocr_result.get("dates", []),
                "extracted_amounts": ocr_result.get("amounts", []),
                "extracted_names": ocr_result.get("names", []),
                
                # Structure du document
                "has_tables": bool(ocr_result.get("tables", [])),
                "page_count": ocr_result.get("page_count", 1),
                "language": ocr_result.get("detected_language", "fr"),
                
                # Classification
                "predicted_category": ocr_result.get("predicted_category", "unknown"),
                "category_confidence": ocr_result.get("category_confidence", 0.0)
            }
            
            # Ajout des métadonnées spécifiques selon le type
            if "structure_analysis" in ocr_result:
                metadata["structure"] = ocr_result["structure_analysis"]
            
            return metadata
            
        except Exception as e:
            logger.error(f"Erreur préparation métadonnées: {e}")
            return {}
    
    def _predict_document_type(self, ocr_result: Dict[str, Any]) -> Optional[str]:
        """Prédit le type de document à partir des résultats OCR."""
        try:
            # Utilise la classification du pipeline OCR si disponible
            if "predicted_category" in ocr_result:
                category = ocr_result["predicted_category"].upper()
                try:
                    DocumentType[category]
                    return category
                except KeyError:
                    pass
            
            # Classification basique par entités
            entities = ocr_result.get("entities", {})
            text = self._extract_text_from_ocr(ocr_result).lower()
            
            # Factures
            if entities.get("amounts") or "€" in text or "tva" in text:
                return "FACTURE"
            
            # Transport
            if "sncf" in text or "ratp" in text or "transport" in text:
                return "TRANSPORT"
            
            # Bancaire
            if "iban" in text or "rib" in text or entities.get("iban"):
                return "BANCAIRE"
            
            # Identité
            if "passeport" in text or "carte nationale" in text:
                return "IDENTITE"
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur prédiction type: {e}")
            return None
    
    async def reindex_document(self, document_id: str, new_ocr_result: Dict[str, Any]) -> bool:
        """Réindexe un document avec de nouveaux résultats OCR."""
        try:
            # Suppression de l'ancienne indexation
            await self.remove_document_from_index(document_id)
            
            # Réindexation
            document_data = {"id": document_id}
            return await self.index_document_from_ocr(document_data, new_ocr_result)
            
        except Exception as e:
            logger.error(f"Erreur lors de la réindexation: {e}")
            return False
    
    async def remove_document_from_index(self, document_id: str) -> bool:
        """Supprime un document de l'index."""
        try:
            # Suppression du document principal
            success = collection_manager.delete_document(document_id)
            
            # Suppression des chunks associés
            chunk_pattern = f"{document_id}_chunk_"
            # Note: ChromaDB ne supporte pas la recherche par pattern
            # Il faudrait maintenir une liste des chunks par document
            
            if document_id in self.processed_documents:
                self.processed_documents.remove(document_id)
            
            logger.info(f"Document {document_id} supprimé de l'index")
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            return False
    
    async def batch_index_documents(self, documents_data: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Indexation par batch de plusieurs documents."""
        try:
            results = {}
            
            # Traitement en parallèle avec limite
            semaphore = asyncio.Semaphore(5)  # Max 5 documents en parallèle
            
            async def process_document(doc_data):
                async with semaphore:
                    document_id = doc_data.get("id", str(uuid.uuid4()))
                    try:
                        if "ocr_result" in doc_data:
                            success = await self.index_document_from_ocr(
                                doc_data, 
                                doc_data["ocr_result"]
                            )
                            results[document_id] = success
                        else:
                            logger.warning(f"Pas de résultats OCR pour {document_id}")
                            results[document_id] = False
                    except Exception as e:
                        logger.error(f"Erreur traitement {document_id}: {e}")
                        results[document_id] = False
            
            # Lancement des tâches
            tasks = [process_document(doc) for doc in documents_data]
            await asyncio.gather(*tasks)
            
            successful = sum(1 for success in results.values() if success)
            total = len(results)
            
            logger.info(f"Batch indexation: {successful}/{total} documents indexés")
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de l'indexation batch: {e}")
            return {}
    
    def get_indexing_stats(self) -> Dict[str, Any]:
        """Statistiques d'indexation."""
        try:
            collection_stats = collection_manager.get_collection_stats()
            
            return {
                "processed_documents_count": len(self.processed_documents),
                "collection_stats": collection_stats,
                "total_indexed_chunks": sum(
                    stats.get("document_count", 0) 
                    for stats in collection_stats.values()
                ),
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération stats: {e}")
            return {}

# Instance globale de l'indexeur
document_indexer = DocumentIndexer()