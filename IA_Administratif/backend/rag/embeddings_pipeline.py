"""
Pipeline optimisé de génération d'embeddings pour documents français.
"""
import logging
import time
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import hashlib
import pickle
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer
import torch

from core.config import settings

logger = logging.getLogger(__name__)

class EmbeddingsPipeline:
    """Pipeline optimisé pour la génération d'embeddings."""
    
    def __init__(self):
        self.model = None
        self.model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        self.device = self._get_optimal_device()
        self.cache_dir = Path(__file__).parent.parent / "data" / "embeddings_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.batch_size = 32
        self.max_workers = 4
        self._initialize_model()
    
    def _get_optimal_device(self) -> str:
        """Détermine le meilleur device disponible."""
        try:
            if torch.cuda.is_available():
                return "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return "mps"  # Apple Silicon GPU
            else:
                return "cpu"
        except Exception as e:
            logger.warning(f"Erreur détection device: {e}")
            return "cpu"
    
    def _initialize_model(self):
        """Initialise le modèle d'embeddings."""
        try:
            logger.info(f"Chargement du modèle {self.model_name} sur {self.device}")
            
            self.model = SentenceTransformer(
                self.model_name,
                device=self.device,
                cache_folder=str(self.cache_dir / "models")
            )
            
            # Configuration pour Apple Silicon
            if self.device == "mps":
                self.model.to('mps')
                logger.info("Modèle configuré pour Apple Silicon (Metal)")
            
            # Test du modèle
            test_embedding = self.model.encode(["Test de fonctionnement"])
            logger.info(f"Modèle initialisé - Dimension: {len(test_embedding[0])}")
            
        except Exception as e:
            logger.error(f"Erreur initialisation modèle: {e}")
            raise
    
    def generate_embeddings(
        self, 
        texts: List[str], 
        use_cache: bool = True,
        normalize: bool = True
    ) -> List[np.ndarray]:
        """
        Génère les embeddings pour une liste de textes.
        
        Args:
            texts: Liste des textes à encoder
            use_cache: Utiliser le cache si disponible
            normalize: Normaliser les embeddings
            
        Returns:
            Liste des embeddings
        """
        try:
            if not texts:
                return []
            
            # Nettoyage des textes
            cleaned_texts = [self._clean_text(text) for text in texts]
            
            # Vérification du cache
            embeddings = []
            texts_to_process = []
            cache_keys = []
            
            for text in cleaned_texts:
                cache_key = self._get_cache_key(text)
                cache_keys.append(cache_key)
                
                if use_cache:
                    cached_embedding = self._load_from_cache(cache_key)
                    if cached_embedding is not None:
                        embeddings.append(cached_embedding)
                        texts_to_process.append(None)  # Marqueur pour cache hit
                        continue
                
                embeddings.append(None)  # Placeholder
                texts_to_process.append(text)
            
            # Traitement des textes non cachés
            non_cached_texts = [t for t in texts_to_process if t is not None]
            if non_cached_texts:
                new_embeddings = self._encode_batch(non_cached_texts, normalize)
                
                # Mise en cache des nouveaux embeddings
                if use_cache:
                    self._cache_embeddings(non_cached_texts, new_embeddings, cache_keys)
                
                # Insertion des nouveaux embeddings dans la liste
                new_idx = 0
                for i, text in enumerate(texts_to_process):
                    if text is not None:  # Non caché
                        embeddings[i] = new_embeddings[new_idx]
                        new_idx += 1
            
            logger.info(f"Embeddings générés: {len(embeddings)} textes")
            return embeddings
            
        except Exception as e:
            logger.error(f"Erreur génération embeddings: {e}")
            return []
    
    async def generate_embeddings_async(
        self, 
        texts: List[str], 
        use_cache: bool = True,
        normalize: bool = True
    ) -> List[np.ndarray]:
        """Version asynchrone de la génération d'embeddings."""
        try:
            loop = asyncio.get_event_loop()
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future = executor.submit(
                    self.generate_embeddings, 
                    texts, 
                    use_cache, 
                    normalize
                )
                return await loop.run_in_executor(None, lambda: future.result())
                
        except Exception as e:
            logger.error(f"Erreur génération embeddings async: {e}")
            return []
    
    def _encode_batch(self, texts: List[str], normalize: bool = True) -> List[np.ndarray]:
        """Encode un batch de textes."""
        try:
            start_time = time.time()
            
            # Traitement par batch pour optimiser la mémoire
            all_embeddings = []
            
            for i in range(0, len(texts), self.batch_size):
                batch = texts[i:i + self.batch_size]
                
                # Génération des embeddings
                batch_embeddings = self.model.encode(
                    batch,
                    convert_to_numpy=True,
                    normalize_embeddings=normalize,
                    show_progress_bar=len(texts) > 100
                )
                
                all_embeddings.extend(batch_embeddings)
            
            processing_time = time.time() - start_time
            logger.info(f"Batch encodé: {len(texts)} textes en {processing_time:.2f}s")
            
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Erreur encodage batch: {e}")
            return []
    
    def _clean_text(self, text: str) -> str:
        """Nettoie un texte avant embeddings."""
        try:
            if not text:
                return ""
            
            # Suppression des caractères de contrôle
            text = ''.join(char for char in text if ord(char) >= 32)
            
            # Limitation de la longueur (modèle a une limite)
            max_length = 512  # Tokens approximatifs
            if len(text) > max_length * 4:  # ~4 chars par token
                text = text[:max_length * 4]
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Erreur nettoyage texte: {e}")
            return text
    
    def _get_cache_key(self, text: str) -> str:
        """Génère une clé de cache pour un texte."""
        try:
            # Hash du texte + modèle pour unicité
            content = f"{self.model_name}:{text}".encode('utf-8')
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception as e:
            logger.warning(f"Erreur génération clé cache: {e}")
            return ""
    
    def _load_from_cache(self, cache_key: str) -> Optional[np.ndarray]:
        """Charge un embedding depuis le cache."""
        try:
            cache_file = self.cache_dir / f"{cache_key}.pkl"
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
            return None
        except Exception as e:
            logger.debug(f"Cache miss pour {cache_key}: {e}")
            return None
    
    def _cache_embeddings(
        self, 
        texts: List[str], 
        embeddings: List[np.ndarray], 
        cache_keys: List[str]
    ):
        """Met en cache les embeddings."""
        try:
            relevant_keys = [key for key in cache_keys if key]
            text_idx = 0
            
            for i, key in enumerate(cache_keys):
                if key and i < len(texts) and text_idx < len(embeddings):
                    # Seuls les textes non cachés ont été traités
                    if any(texts[i] == t for t in texts if t is not None):
                        cache_file = self.cache_dir / f"{key}.pkl"
                        try:
                            with open(cache_file, 'wb') as f:
                                pickle.dump(embeddings[text_idx], f)
                            text_idx += 1
                        except Exception as e:
                            logger.warning(f"Erreur sauvegarde cache {key}: {e}")
                            
        except Exception as e:
            logger.warning(f"Erreur mise en cache: {e}")
    
    def compute_similarity(
        self, 
        embedding1: np.ndarray, 
        embedding2: np.ndarray
    ) -> float:
        """Calcule la similarité cosinus entre deux embeddings."""
        try:
            # Similarité cosinus
            dot_product = np.dot(embedding1, embedding2)
            norms = np.linalg.norm(embedding1) * np.linalg.norm(embedding2)
            
            if norms == 0:
                return 0.0
            
            return float(dot_product / norms)
            
        except Exception as e:
            logger.error(f"Erreur calcul similarité: {e}")
            return 0.0
    
    def find_most_similar(
        self, 
        query_embedding: np.ndarray, 
        candidate_embeddings: List[np.ndarray],
        top_k: int = 5
    ) -> List[Tuple[int, float]]:
        """Trouve les embeddings les plus similaires."""
        try:
            similarities = []
            
            for i, candidate in enumerate(candidate_embeddings):
                similarity = self.compute_similarity(query_embedding, candidate)
                similarities.append((i, similarity))
            
            # Tri par similarité décroissante
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Erreur recherche similarité: {e}")
            return []
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Statistiques du pipeline d'embeddings."""
        try:
            cache_files = list(self.cache_dir.glob("*.pkl"))
            cache_size_mb = sum(f.stat().st_size for f in cache_files) / (1024 * 1024)
            
            return {
                "model_name": self.model_name,
                "device": self.device,
                "embedding_dimension": self.model.get_sentence_embedding_dimension(),
                "batch_size": self.batch_size,
                "cache_entries": len(cache_files),
                "cache_size_mb": round(cache_size_mb, 2),
                "max_workers": self.max_workers
            }
            
        except Exception as e:
            logger.error(f"Erreur stats embeddings: {e}")
            return {}
    
    def clear_cache(self) -> bool:
        """Vide le cache des embeddings."""
        try:
            cache_files = list(self.cache_dir.glob("*.pkl"))
            for cache_file in cache_files:
                cache_file.unlink()
            
            logger.info(f"Cache vidé: {len(cache_files)} fichiers supprimés")
            return True
            
        except Exception as e:
            logger.error(f"Erreur vidage cache: {e}")
            return False
    
    def optimize_for_production(self):
        """Optimisations pour l'environnement de production."""
        try:
            # Augmentation des batch sizes pour production
            self.batch_size = 64
            self.max_workers = min(8, torch.get_num_threads())
            
            # Optimisations Apple Silicon
            if self.device == "mps":
                # Configuration spécifique Metal Performance Shaders
                torch.mps.set_per_process_memory_fraction(0.8)
                logger.info("Optimisations Apple Silicon activées")
            
            logger.info(f"Pipeline optimisé: batch_size={self.batch_size}, workers={self.max_workers}")
            
        except Exception as e:
            logger.warning(f"Erreur optimisations production: {e}")

# Instance globale du pipeline
embeddings_pipeline = EmbeddingsPipeline()