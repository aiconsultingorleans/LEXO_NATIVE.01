"""
Wrapper Python pour Mistral 7B avec MLX sur Apple Silicon.
"""
import logging
import time
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator
from pathlib import Path
import json
from dataclasses import dataclass

try:
    import mlx.core as mx
    from mlx_lm import load, generate
    MLX_AVAILABLE = True
except ImportError:
    MLX_AVAILABLE = False

from core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class MistralConfig:
    """Configuration pour Mistral."""
    model_path: str = "mlx-community/Mistral-7B-Instruct-v0.3-4bit"
    max_tokens: int = 512
    temperature: float = 0.7
    top_p: float = 0.9
    repetition_penalty: float = 1.1
    max_kv_size: int = None  # Cache KV automatique

class MistralWrapper:
    """Wrapper optimisé pour Mistral 7B avec MLX."""
    
    def __init__(self, config: Optional[MistralConfig] = None):
        self.config = config or MistralConfig()
        self.model = None
        self.tokenizer = None
        self.is_loaded = False
        self.device = mx.default_device() if MLX_AVAILABLE else None
        self.generation_cache = {}
        
        if not MLX_AVAILABLE:
            logger.error("MLX non disponible - Mistral ne fonctionnera pas")
            return
            
        logger.info(f"Mistral configuré pour device: {self.device}")
    
    async def initialize(self) -> bool:
        """Initialise le modèle Mistral de façon asynchrone."""
        try:
            if not MLX_AVAILABLE:
                logger.error("MLX non disponible")
                return False
                
            if self.is_loaded:
                logger.info("Modèle déjà chargé")
                return True
            
            logger.info(f"Chargement de Mistral: {self.config.model_path}")
            start_time = time.time()
            
            # Chargement asynchrone pour éviter de bloquer
            loop = asyncio.get_event_loop()
            self.model, self.tokenizer = await loop.run_in_executor(
                None, 
                lambda: load(self.config.model_path)
            )
            
            loading_time = time.time() - start_time
            logger.info(f"Mistral chargé en {loading_time:.2f}s")
            
            # Test de fonctionnement
            test_response = await self.generate_response(
                "Test de fonctionnement", 
                max_tokens=10
            )
            
            if test_response:
                self.is_loaded = True
                logger.info("Mistral initialisé et testé avec succès")
                return True
            else:
                logger.error("Échec du test Mistral")
                return False
                
        except Exception as e:
            logger.error(f"Erreur initialisation Mistral: {e}")
            return False
    
    async def generate_response(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        context: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Génère une réponse avec Mistral.
        
        Args:
            prompt: Question/requête utilisateur
            max_tokens: Limite de tokens
            temperature: Créativité (0.0-1.0)
            system_prompt: Instructions système
            context: Contexte de documents récupérés
        """
        try:
            if not self.is_loaded:
                logger.warning("Modèle non chargé")
                if not await self.initialize():
                    return None
            
            # Configuration génération
            gen_config = {
                "max_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
                "top_p": self.config.top_p,
                "repetition_penalty": self.config.repetition_penalty
            }
            
            # Construction du prompt complet
            full_prompt = self._build_prompt(prompt, system_prompt, context)
            
            # Génération
            start_time = time.time()
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: generate(
                    self.model,
                    self.tokenizer,
                    prompt=full_prompt,
                    **gen_config
                )
            )
            
            generation_time = time.time() - start_time
            
            if response:
                # Nettoyage de la réponse
                cleaned_response = self._clean_response(response, full_prompt)
                
                logger.info(f"Réponse générée en {generation_time:.2f}s ({len(cleaned_response)} chars)")
                return cleaned_response
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur génération réponse: {e}")
            return None
    
    async def generate_streaming_response(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
        context: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """Génère une réponse en streaming (token par token)."""
        try:
            if not self.is_loaded:
                if not await self.initialize():
                    return
            
            # Construction du prompt
            full_prompt = self._build_prompt(prompt, system_prompt, context)
            
            # Configuration
            gen_config = {
                "max_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
                "top_p": self.config.top_p,
                "repetition_penalty": self.config.repetition_penalty
            }
            
            # Note: MLX-LM ne supporte pas nativement le streaming
            # On simule en générant par chunks
            chunk_size = 50
            full_response = await self.generate_response(
                prompt, max_tokens, temperature, system_prompt, context
            )
            
            if full_response:
                for i in range(0, len(full_response), chunk_size):
                    chunk = full_response[i:i + chunk_size]
                    yield chunk
                    await asyncio.sleep(0.01)  # Simulation streaming
                    
        except Exception as e:
            logger.error(f"Erreur streaming: {e}")
            yield f"Erreur: {str(e)}"
    
    def _build_prompt(
        self, 
        user_prompt: str, 
        system_prompt: Optional[str] = None,
        context: Optional[List[str]] = None
    ) -> str:
        """Construit le prompt complet pour Mistral."""
        try:
            # Prompt système par défaut
            default_system = """Tu es un assistant IA spécialisé dans l'analyse de documents administratifs français.
Tu dois répondre de manière précise et factuelle en te basant uniquement sur les informations fournies.
Si tu ne trouves pas l'information, dit-le clairement."""
            
            system = system_prompt or default_system
            
            # Construction avec format Mistral Instruct
            prompt_parts = [f"<s>[INST] {system}"]
            
            # Ajout du contexte si fourni
            if context:
                context_text = "\n\n".join(context[:5])  # Max 5 documents
                prompt_parts.append(f"\nContexte des documents:\n{context_text}")
            
            # Question utilisateur
            prompt_parts.append(f"\nQuestion: {user_prompt} [/INST]")
            
            return "\n".join(prompt_parts)
            
        except Exception as e:
            logger.error(f"Erreur construction prompt: {e}")
            return user_prompt
    
    def _clean_response(self, response: str, original_prompt: str) -> str:
        """Nettoie la réponse générée."""
        try:
            # Suppression des artefacts courants
            cleaned = response.strip()
            
            # Suppression du prompt original si présent
            if original_prompt in cleaned:
                cleaned = cleaned.replace(original_prompt, "").strip()
            
            # Suppression des tokens spéciaux Mistral
            cleaned = cleaned.replace("<s>", "").replace("</s>", "")
            cleaned = cleaned.replace("[INST]", "").replace("[/INST]", "")
            
            # Suppression des répétitions
            lines = cleaned.split('\n')
            unique_lines = []
            for line in lines:
                if line.strip() and line not in unique_lines:
                    unique_lines.append(line)
            
            cleaned = '\n'.join(unique_lines)
            
            return cleaned.strip()
            
        except Exception as e:
            logger.warning(f"Erreur nettoyage réponse: {e}")
            return response
    
    async def analyze_document_content(
        self,
        document_text: str,
        question: str,
        document_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyse spécialisée d'un document."""
        try:
            # Prompt spécialisé pour l'analyse documentaire
            system_prompt = """Tu es un expert en analyse de documents administratifs français.
Analyse le document fourni et réponds à la question de manière structurée.
Fournis des informations factuelles et cite les passages pertinents."""
            
            context = [document_text]
            
            response = await self.generate_response(
                question,
                max_tokens=400,
                temperature=0.3,  # Plus factuel
                system_prompt=system_prompt,
                context=context
            )
            
            return {
                "answer": response,
                "confidence": self._estimate_confidence(response, document_text),
                "document_type": document_metadata.get("document_type") if document_metadata else "unknown",
                "processing_time": time.time()
            }
            
        except Exception as e:
            logger.error(f"Erreur analyse document: {e}")
            return {"answer": None, "error": str(e)}
    
    def _estimate_confidence(self, response: str, context: str) -> float:
        """Estime la confiance de la réponse (simple heuristique)."""
        try:
            if not response:
                return 0.0
            
            # Facteurs de confiance
            confidence = 0.5  # Base
            
            # Longueur appropriée
            if 50 <= len(response) <= 500:
                confidence += 0.2
            
            # Présence de mots d'incertitude
            uncertainty_words = ["je ne sais pas", "peut-être", "probablement", "incertain"]
            if any(word in response.lower() for word in uncertainty_words):
                confidence -= 0.3
            
            # Références au contexte
            if any(word in context.lower() for word in response.lower().split()[:10]):
                confidence += 0.2
            
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            logger.warning(f"Erreur estimation confiance: {e}")
            return 0.5
    
    def get_model_info(self) -> Dict[str, Any]:
        """Informations sur le modèle chargé."""
        try:
            return {
                "model_path": self.config.model_path,
                "is_loaded": self.is_loaded,
                "device": str(self.device) if self.device else "unknown",
                "mlx_available": MLX_AVAILABLE,
                "config": {
                    "max_tokens": self.config.max_tokens,
                    "temperature": self.config.temperature,
                    "top_p": self.config.top_p,
                    "repetition_penalty": self.config.repetition_penalty
                }
            }
        except Exception as e:
            logger.error(f"Erreur info modèle: {e}")
            return {}
    
    async def shutdown(self):
        """Libère les ressources du modèle."""
        try:
            # MLX gère automatiquement la mémoire
            self.model = None
            self.tokenizer = None
            self.is_loaded = False
            logger.info("Mistral déchargé")
        except Exception as e:
            logger.error(f"Erreur déchargement: {e}")

# Instance globale du wrapper
mistral_wrapper = MistralWrapper()