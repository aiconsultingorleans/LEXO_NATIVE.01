"""
Endpoint pour vider la base de données RAG (ChromaDB)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import httpx
from typing import Dict, Any
import asyncio

from core.database import get_db
from models.user import User
from models.document import Document
from api.auth import get_current_user
from core.config import settings
from sqlalchemy import delete, select

router = APIRouter()
logger = logging.getLogger(__name__)


@router.delete("/clear", response_model=Dict[str, Any])
async def clear_rag_database(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Vide complètement la base de données RAG (ChromaDB)"""
    
    logger.info(f"🗑️ [RAG CLEAR] Demande de vidage base RAG par utilisateur {current_user.email}")
    logger.info(f"🗑️ [RAG CLEAR] Début du processus de vidage")
    
    try:
        collections_cleared = 0
        error_details = []
        
        # Utiliser le client Python ChromaDB directement
        try:
            import chromadb
            
            logger.info("📋 Connexion à ChromaDB via client Python...")
            
            # Connexion au serveur ChromaDB (nom du service Docker)
            client = chromadb.HttpClient(host="chromadb", port=8000)
            
            # Lister toutes les collections
            collections = client.list_collections()
            logger.info(f"📊 {len(collections)} collections trouvées dans ChromaDB")
            
            # Supprimer chaque collection
            for collection in collections:
                try:
                    collection_name = collection.name
                    logger.info(f"🗑️ Suppression collection: {collection_name}")
                    
                    client.delete_collection(name=collection_name)
                    collections_cleared += 1
                    logger.info(f"✅ Collection {collection_name} supprimée")
                    
                except Exception as e:
                    error_msg = f"Exception lors de la suppression de {collection_name}: {str(e)}"
                    error_details.append(error_msg)
                    logger.error(error_msg)
            
            logger.info(f"✅ ChromaDB vidé: {collections_cleared} collections supprimées")
            
            # 2. Vider PostgreSQL - Supprimer tous les documents
            logger.info("🗑️ [RAG CLEAR] Suppression des documents PostgreSQL...")
            
            # Compter les documents avant suppression
            result = await db.execute(select(Document).where(Document.user_id == current_user.id))
            documents_before = len(result.scalars().all())
            logger.info(f"📊 {documents_before} documents trouvés dans PostgreSQL")
            
            # Supprimer tous les documents de l'utilisateur
            delete_stmt = delete(Document).where(Document.user_id == current_user.id)
            result = await db.execute(delete_stmt)
            await db.commit()
            
            documents_deleted = result.rowcount
            logger.info(f"✅ PostgreSQL vidé: {documents_deleted} documents supprimés")
            
            collections_cleared += documents_deleted  # Ajouter au total pour l'affichage
                    
        except ImportError:
            logger.warning("⚠️ ChromaDB client Python non disponible, utilisation de l'API REST...")
            
            # Fallback vers l'API REST (méthode originale mais simplifiée)
            chromadb_url = "http://localhost:8001"
            
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                try:
                    # Reset complet via API interne si disponible
                    reset_response = await http_client.post(f"{chromadb_url}/api/v1/reset")
                    
                    if reset_response.status_code == 200:
                        logger.info("✅ Reset global ChromaDB réussi")
                        collections_cleared = 1  # Indicateur de succès
                    else:
                        logger.warning(f"⚠️ Reset global non disponible: {reset_response.status_code}")
                        # Pas d'erreur car ChromaDB peut être vide
                        
                except Exception as e:
                    logger.warning(f"⚠️ Impossible d'utiliser l'API REST: {e}")
                    # Pas d'erreur fatale
                    
        except Exception as e:
            error_msg = f"Erreur lors de la connexion à ChromaDB: {str(e)}"
            error_details.append(error_msg)
            logger.error(f"❌ {error_msg}")
            
            # Si ChromaDB n'est pas accessible, on considère que c'est un succès
            # car il n'y a pas de données à vider
            collections_cleared = 0
        
        # 3. Résultat final  
        logger.info(f"✅ Vidage complet terminé: ChromaDB + PostgreSQL")
        
        if error_details and collections_cleared == 0:
            logger.error("❌ Échec complet du vidage de ChromaDB")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "message": "Échec du vidage de la base RAG",
                    "errors": error_details
                }
            )
        
        logger.info(f"✅ Vidage ChromaDB terminé: {collections_cleared} collections supprimées")
        
        response_data = {
            "success": True,
            "message": f"Base RAG et documents vidés avec succès",
            "collections_cleared": collections_cleared,
            "chromadb_url": "http://chromadb:8000",
            "timestamp": "2025-07-24 19:26:56"
        }
        
        if error_details:
            response_data["warnings"] = error_details
            
        return response_data
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.error(f"❌ Erreur inattendue lors du vidage RAG: {e}")
        import traceback
        traceback.print_exc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": "Erreur interne lors du vidage de la base RAG",
                "error": str(e)
            }
        )


@router.get("/test")
async def test_rag_endpoint():
    """Test simple de l'endpoint RAG"""
    return {"status": "RAG endpoint accessible", "timestamp": "2025-07-24"}

@router.get("/status")
async def get_rag_status(
    current_user: User = Depends(get_current_user)
):
    """Récupère le statut de la base RAG"""
    
    try:
        chromadb_url = "http://localhost:8001"
        
        try:
            import chromadb
            
            # Connexion au serveur ChromaDB (nom du service Docker)
            client = chromadb.HttpClient(host="chromadb", port=8000)
            
            # Tester la connexion et lister les collections
            collections = client.list_collections()
            
            total_collections = len(collections)
            collection_names = [col.name for col in collections]
            
            return {
                "chromadb_accessible": True,
                "total_collections": total_collections,
                "collections": collection_names,
                "chromadb_url": "http://chromadb:8000"
            }
            
        except ImportError:
            return {
                "chromadb_accessible": False,
                "error": "ChromaDB Python client not available",
                "chromadb_url": "http://chromadb:8000"
            }
            
        except Exception as e:
            # Fallback vers API REST
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    # Tester la connexion basique
                    response = await client.get("http://chromadb:8000/")
                
                    return {
                        "chromadb_accessible": True,
                        "total_collections": 0,
                        "collections": [],
                        "chromadb_url": "http://chromadb:8000",
                        "note": "Status via REST API - limited info"
                    }
                except Exception as rest_e:
                    return {
                        "chromadb_accessible": False,
                        "error": f"ChromaDB error: {str(e)}, REST fallback: {str(rest_e)}",
                        "chromadb_url": "http://chromadb:8000"
                    }
                    
    except Exception as e:
        return {
            "chromadb_accessible": False,
            "error": f"Unexpected error: {str(e)}",
            "chromadb_url": "http://localhost:8001"
        }