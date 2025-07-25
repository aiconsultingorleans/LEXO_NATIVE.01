"""
Service ChromaDB pour la gestion des embeddings et recherche vectorielle.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import numpy as np

from core.config import settings

logger = logging.getLogger(__name__)

class ChromaDBService:
    """Service pour gérer ChromaDB et les opérations vectorielles."""
    
    def __init__(self):
        self.client = None
        self.embedding_function = None
        self.collections = {}
        self._initialize_client()
        self._initialize_embedding_function()
    
    def _initialize_client(self):
        """Initialise le client ChromaDB."""
        try:
            # Chemin de stockage pour ChromaDB
            chroma_db_path = Path(__file__).parent.parent / "data" / "chromadb"
            chroma_db_path.mkdir(parents=True, exist_ok=True)
            
            # Configuration ChromaDB avec persistance
            self.client = chromadb.PersistentClient(
                path=str(chroma_db_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            logger.info(f"ChromaDB initialisé avec persistance dans: {chroma_db_path}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation ChromaDB: {e}")
            raise
    
    def _initialize_embedding_function(self):
        """Initialise la fonction d'embeddings avec un modèle français."""
        try:
            # Modèle multilingue optimisé pour le français
            model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            
            self.embedding_function = SentenceTransformerEmbeddingFunction(
                model_name=model_name,
                device="cpu"  # Utilisera Metal sur Apple Silicon automatiquement
            )
            
            logger.info(f"Fonction d'embeddings initialisée avec le modèle: {model_name}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des embeddings: {e}")
            raise
    
    def create_collection(self, name: str, metadata: Optional[Dict] = None) -> bool:
        """Crée une nouvelle collection."""
        try:
            if name in self.collections:
                logger.warning(f"Collection {name} existe déjà")
                return True
            
            collection = self.client.get_or_create_collection(
                name=name,
                embedding_function=self.embedding_function,
                metadata=metadata or {}
            )
            
            self.collections[name] = collection
            logger.info(f"Collection '{name}' créée avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la collection {name}: {e}")
            return False
    
    def get_collection(self, name: str):
        """Récupère une collection existante."""
        try:
            if name not in self.collections:
                collection = self.client.get_collection(
                    name=name,
                    embedding_function=self.embedding_function
                )
                self.collections[name] = collection
            
            return self.collections[name]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la collection {name}: {e}")
            return None
    
    def add_documents(self, collection_name: str, documents: List[Dict[str, Any]]) -> bool:
        """Ajoute des documents à une collection."""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.error(f"Collection {collection_name} introuvable")
                return False
            
            # Préparation des données
            ids = [doc["id"] for doc in documents]
            texts = [doc["text"] for doc in documents]
            metadatas = [doc.get("metadata", {}) for doc in documents]
            
            # Ajout des documents (ChromaDB génère automatiquement les embeddings)
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
            
            logger.info(f"Ajouté {len(documents)} documents à la collection {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de documents: {e}")
            return False
    
    def search_similar(
        self, 
        collection_name: str, 
        query: str, 
        n_results: int = 5,
        where_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Recherche de documents similaires."""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                logger.error(f"Collection {collection_name} introuvable")
                return []
            
            # Recherche vectorielle
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_filter
            )
            
            # Formatage des résultats
            formatted_results = []
            if results["ids"] and len(results["ids"]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i],
                        "score": 1 - results["distances"][0][i]  # Conversion distance -> similarité
                    })
            
            logger.info(f"Recherche effectuée: {len(formatted_results)} résultats pour '{query[:50]}...'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Erreur lors de la recherche: {e}")
            return []
    
    def delete_document(self, collection_name: str, document_id: str) -> bool:
        """Supprime un document d'une collection."""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return False
            
            collection.delete(ids=[document_id])
            logger.info(f"Document {document_id} supprimé de {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            return False
    
    def update_document(self, collection_name: str, document_id: str, new_text: str, new_metadata: Dict = None) -> bool:
        """Met à jour un document."""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return False
            
            collection.update(
                ids=[document_id],
                documents=[new_text],
                metadatas=[new_metadata or {}]
            )
            
            logger.info(f"Document {document_id} mis à jour dans {collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour: {e}")
            return False
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Statistiques d'une collection."""
        try:
            collection = self.get_collection(collection_name)
            if not collection:
                return {}
            
            count = collection.count()
            return {
                "name": collection_name,
                "document_count": count,
                "embedding_function": str(self.embedding_function)
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {e}")
            return {}
    
    def list_collections(self) -> List[str]:
        """Liste toutes les collections."""
        try:
            collections = self.client.list_collections()
            return [c.name for c in collections]
        except Exception as e:
            logger.error(f"Erreur lors du listage des collections: {e}")
            return []
    
    def reset_collection(self, collection_name: str) -> bool:
        """Vide complètement une collection."""
        try:
            collection = self.get_collection(collection_name)
            if collection:
                self.client.delete_collection(collection_name)
                self.create_collection(collection_name)
                if collection_name in self.collections:
                    del self.collections[collection_name]
                logger.info(f"Collection {collection_name} réinitialisée")
                return True
            return False
        except Exception as e:
            logger.error(f"Erreur lors de la réinitialisation: {e}")
            return False

# Instance globale du service
chroma_service = ChromaDBService()