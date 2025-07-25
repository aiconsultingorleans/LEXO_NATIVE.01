"""
Gestionnaire des collections de documents par type.
"""
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from datetime import datetime

from .chromadb_service import chroma_service

logger = logging.getLogger(__name__)

class DocumentType(Enum):
    """Types de documents supportés."""
    FACTURE = "factures"
    CONTRAT = "contrats"
    LEGAL = "documents_legaux"
    TRANSPORT = "titres_transport"
    IDENTITE = "pieces_identite"
    BANCAIRE = "documents_bancaires"
    ADMINISTRATIF = "documents_administratifs"
    COURRIER = "courriers"
    AUTRE = "autres"

class DocumentCollectionManager:
    """Gestionnaire des collections de documents."""
    
    def __init__(self):
        self.collections = {}
        self._initialize_collections()
    
    def _initialize_collections(self):
        """Initialise toutes les collections nécessaires."""
        try:
            for doc_type in DocumentType:
                collection_name = doc_type.value
                metadata = {
                    "type": doc_type.name.lower(),
                    "description": self._get_collection_description(doc_type),
                    "created_at": datetime.now().isoformat()
                }
                
                success = chroma_service.create_collection(collection_name, metadata)
                if success:
                    self.collections[doc_type] = collection_name
                    logger.info(f"Collection {collection_name} initialisée")
                else:
                    logger.error(f"Échec création collection {collection_name}")
            
            # Collection générale pour recherche globale
            chroma_service.create_collection("tous_documents", {
                "type": "global",
                "description": "Collection contenant tous les documents pour recherche globale",
                "created_at": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation des collections: {e}")
    
    def _get_collection_description(self, doc_type: DocumentType) -> str:
        """Description des collections par type."""
        descriptions = {
            DocumentType.FACTURE: "Factures, devis, bons de commande",
            DocumentType.CONTRAT: "Contrats, accords, conventions",
            DocumentType.LEGAL: "Documents juridiques, jugements, actes",
            DocumentType.TRANSPORT: "Titres de transport, cartes, abonnements",
            DocumentType.IDENTITE: "Pièces d'identité, passeports, permis",
            DocumentType.BANCAIRE: "RIB, relevés bancaires, virements",
            DocumentType.ADMINISTRATIF: "Certificats, attestations, formulaires",
            DocumentType.COURRIER: "Lettres, emails, communications",
            DocumentType.AUTRE: "Documents divers non classifiés"
        }
        return descriptions.get(doc_type, "Collection de documents")
    
    def add_document_to_collection(
        self, 
        doc_type: DocumentType, 
        document_id: str,
        text_content: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Ajoute un document à la collection appropriée."""
        try:
            collection_name = doc_type.value
            
            # Enrichissement des métadonnées
            enriched_metadata = {
                **metadata,
                "document_type": doc_type.name.lower(),
                "indexed_at": datetime.now().isoformat(),
                "collection": collection_name
            }
            
            # Préparation du document
            document = {
                "id": document_id,
                "text": text_content,
                "metadata": enriched_metadata
            }
            
            # Ajout à la collection spécifique
            success = chroma_service.add_documents(collection_name, [document])
            
            # Ajout à la collection globale
            if success:
                chroma_service.add_documents("tous_documents", [document])
                logger.info(f"Document {document_id} ajouté à {collection_name} et tous_documents")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout du document: {e}")
            return False
    
    def search_in_collection(
        self,
        doc_type: DocumentType,
        query: str,
        n_results: int = 5,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Recherche dans une collection spécifique."""
        try:
            collection_name = doc_type.value
            return chroma_service.search_similar(
                collection_name, 
                query, 
                n_results, 
                filters
            )
        except Exception as e:
            logger.error(f"Erreur lors de la recherche dans {doc_type.value}: {e}")
            return []
    
    def search_all_collections(
        self,
        query: str,
        n_results: int = 10,
        filters: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Recherche dans toutes les collections."""
        try:
            return chroma_service.search_similar(
                "tous_documents", 
                query, 
                n_results, 
                filters
            )
        except Exception as e:
            logger.error(f"Erreur lors de la recherche globale: {e}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Statistiques de toutes les collections."""
        try:
            stats = {}
            
            for doc_type in DocumentType:
                collection_name = doc_type.value
                collection_stats = chroma_service.get_collection_stats(collection_name)
                stats[doc_type.name.lower()] = collection_stats
            
            # Stats collection globale
            global_stats = chroma_service.get_collection_stats("tous_documents")
            stats["global"] = global_stats
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des stats: {e}")
            return {}
    
    def classify_and_add_document(
        self,
        document_id: str,
        text_content: str,
        metadata: Dict[str, Any],
        predicted_type: Optional[str] = None
    ) -> bool:
        """Classifie et ajoute un document à la bonne collection."""
        try:
            # Utilise le type prédit ou tente de classifier
            if predicted_type:
                try:
                    doc_type = DocumentType[predicted_type.upper()]
                except KeyError:
                    doc_type = DocumentType.AUTRE
            else:
                doc_type = self._classify_document(text_content, metadata)
            
            return self.add_document_to_collection(
                doc_type, 
                document_id, 
                text_content, 
                metadata
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la classification/ajout: {e}")
            return False
    
    def _classify_document(self, text: str, metadata: Dict[str, Any]) -> DocumentType:
        """Classification basique par mots-clés."""
        try:
            text_lower = text.lower()
            filename = metadata.get("filename", "").lower()
            
            # Règles de classification par mots-clés
            if any(word in text_lower for word in ["facture", "devis", "€", "tva", "total", "montant"]):
                return DocumentType.FACTURE
            
            elif any(word in text_lower for word in ["contrat", "accord", "convention", "signataire"]):
                return DocumentType.CONTRAT
            
            elif any(word in text_lower for word in ["transport", "sncf", "ratp", "métro", "bus", "carte"]):
                return DocumentType.TRANSPORT
            
            elif any(word in text_lower for word in ["iban", "rib", "banque", "virement", "compte"]):
                return DocumentType.BANCAIRE
            
            elif any(word in text_lower for word in ["identité", "passeport", "permis", "carte nationale"]):
                return DocumentType.IDENTITE
            
            elif any(word in text_lower for word in ["certificat", "attestation", "administratif"]):
                return DocumentType.ADMINISTRATIF
            
            elif any(word in text_lower for word in ["monsieur", "madame", "courrier", "lettre"]):
                return DocumentType.COURRIER
            
            elif any(word in text_lower for word in ["juridique", "tribunal", "jugement", "acte"]):
                return DocumentType.LEGAL
            
            else:
                return DocumentType.AUTRE
                
        except Exception as e:
            logger.error(f"Erreur lors de la classification: {e}")
            return DocumentType.AUTRE
    
    def update_document(
        self,
        document_id: str,
        new_text: str,
        new_metadata: Dict[str, Any],
        doc_type: Optional[DocumentType] = None
    ) -> bool:
        """Met à jour un document dans les collections."""
        try:
            # Si le type n'est pas fourni, on cherche dans toutes les collections
            if not doc_type:
                # Recherche dans la collection globale pour trouver le type
                results = chroma_service.search_similar("tous_documents", document_id, 1)
                if results:
                    doc_type_str = results[0]["metadata"].get("document_type")
                    doc_type = DocumentType[doc_type_str.upper()] if doc_type_str else DocumentType.AUTRE
                else:
                    doc_type = DocumentType.AUTRE
            
            collection_name = doc_type.value
            
            # Mise à jour dans la collection spécifique
            success = chroma_service.update_document(collection_name, document_id, new_text, new_metadata)
            
            # Mise à jour dans la collection globale
            if success:
                chroma_service.update_document("tous_documents", document_id, new_text, new_metadata)
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour: {e}")
            return False
    
    def delete_document(self, document_id: str, doc_type: Optional[DocumentType] = None) -> bool:
        """Supprime un document des collections."""
        try:
            # Si le type n'est pas fourni, supprime de toutes les collections
            if doc_type:
                collections_to_clean = [doc_type.value, "tous_documents"]
            else:
                collections_to_clean = [dt.value for dt in DocumentType] + ["tous_documents"]
            
            success = True
            for collection_name in collections_to_clean:
                try:
                    chroma_service.delete_document(collection_name, document_id)
                except Exception as e:
                    logger.warning(f"Document {document_id} non trouvé dans {collection_name}: {e}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression: {e}")
            return False

# Instance globale du gestionnaire
collection_manager = DocumentCollectionManager()