"""
DONUT Document Processor - Core OCR-free extraction
Étape 3.1-3.2 : Classe principale pour traitement documents avec Donut

Architecture simple suivant guidelines LEXO :
- Code direct, pas de sur-ingénierie
- Gestion erreurs pragmatique
- Performance Apple Silicon optimisée
"""

import logging
import time
from typing import Dict, Any, Optional, Union, List
from pathlib import Path
import torch
from PIL import Image
from transformers import (
    DonutProcessor, 
    VisionEncoderDecoderModel,
    AutoTokenizer,
    AutoModel
)

# Configuration logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DonutDocumentProcessor:
    """
    Processeur principal pour extraction OCR-free avec Donut
    
    Fonctionnalités :
    - Extraction texte structuré depuis images/PDF
    - Optimisation Apple Silicon MPS
    - Fallback automatique vers CPU si nécessaire
    - Gestion erreurs simple et robuste
    """
    
    def __init__(self, models_path: str = "models/donut"):
        """
        Initialise le processeur Donut
        
        Args:
            models_path: Chemin vers modèles locaux
        """
        self.models_path = Path(models_path)
        self.device = self._get_optimal_device()
        
        # Modèles chargés à la demande (lazy loading)
        self.donut_processor = None
        self.donut_model = None
        self.is_loaded = False
        
        logger.info(f"DonutProcessor initialisé - Device: {self.device}")
    
    def _get_optimal_device(self) -> str:
        """Détection automatique device optimal Apple Silicon"""
        if torch.backends.mps.is_available():
            return "mps"  # Apple Silicon optimisé
        elif torch.cuda.is_available():
            return "cuda"
        else:
            return "cpu"
    
    def load_models(self) -> bool:
        """
        Charge les modèles Donut localement
        
        Returns:
            bool: True si succès, False sinon
        """
        try:
            start_time = time.time()
            
            # Chemin modèle Donut local
            donut_path = self.models_path / "donut-base-finetuned-cord-v2"
            
            if not donut_path.exists():
                logger.error(f"Modèle Donut non trouvé : {donut_path}")
                return False
            
            # Chargement processeur et modèle
            logger.info("Chargement modèle Donut...")
            self.donut_processor = DonutProcessor.from_pretrained(str(donut_path))
            self.donut_model = VisionEncoderDecoderModel.from_pretrained(str(donut_path))
            
            # Optimisation Apple Silicon
            if self.device == "mps":
                self.donut_model = self.donut_model.to("mps")
                logger.info("Modèle Donut optimisé Apple Silicon MPS")
            elif self.device == "cuda":
                self.donut_model = self.donut_model.to("cuda")
            
            # Configuration optimale pour génération
            self.donut_model.config.pad_token_id = self.donut_processor.tokenizer.pad_token_id
            self.donut_model.config.decoder_start_token_id = self.donut_processor.tokenizer.convert_tokens_to_ids(['<s>'])[0]
            
            load_time = time.time() - start_time
            self.is_loaded = True
            
            logger.info(f"Modèles Donut chargés avec succès en {load_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Erreur chargement modèles Donut : {e}")
            return False
    
    def extract_text_from_image(self, image_path: Union[str, Path], task_prompt: str = "<s_cord-v2>") -> Dict[str, Any]:
        """
        Extraction OCR-free texte depuis image avec Donut
        
        Args:
            image_path: Chemin vers image (PNG, JPG, TIFF)
            task_prompt: Prompt spécifique tâche Donut
            
        Returns:
            Dict contenant texte extrait et métadonnées
        """
        if not self.is_loaded:
            if not self.load_models():
                return {"error": "Impossible de charger les modèles Donut"}
        
        try:
            start_time = time.time()
            
            # Chargement et préparation image
            image = Image.open(image_path).convert("RGB")
            logger.info(f"Image chargée : {image.size}")
            
            # Préprocessing avec DonutProcessor
            pixel_values = self.donut_processor(image, return_tensors="pt").pixel_values
            
            # Optimisation device
            if self.device != "cpu":
                pixel_values = pixel_values.to(self.device)
            
            # Préparation prompt task
            decoder_input_ids = self.donut_processor.tokenizer(
                task_prompt, 
                add_special_tokens=False, 
                return_tensors="pt"
            ).input_ids
            
            if self.device != "cpu":
                decoder_input_ids = decoder_input_ids.to(self.device)
            
            # Génération avec paramètres optimisés
            with torch.no_grad():
                outputs = self.donut_model.generate(
                    pixel_values,
                    decoder_input_ids=decoder_input_ids,
                    max_length=self.donut_model.decoder.config.max_position_embeddings,
                    early_stopping=True,
                    pad_token_id=self.donut_processor.tokenizer.pad_token_id,
                    eos_token_id=self.donut_processor.tokenizer.eos_token_id,
                    use_cache=True,
                    num_beams=1,  # Plus rapide pour usage temps réel
                    bad_words_ids=[[self.donut_processor.tokenizer.unk_token_id]],
                    return_dict_in_generate=True,
                )
            
            # Décodage résultat
            sequence = outputs.sequences[0]
            decoded_text = self.donut_processor.batch_decode([sequence])[0]
            
            # Nettoyage et structuration
            cleaned_text = self._clean_donut_output(decoded_text, task_prompt)
            
            processing_time = time.time() - start_time
            
            result = {
                "extracted_text": cleaned_text,
                "raw_output": decoded_text,
                "processing_time": processing_time,
                "image_size": image.size,
                "device_used": self.device,
                "success": True
            }
            
            logger.info(f"Extraction Donut terminée en {processing_time:.3f}s - {len(cleaned_text)} caractères")
            return result
            
        except Exception as e:
            logger.error(f"Erreur extraction Donut : {e}")
            return {
                "error": str(e),
                "success": False,
                "extracted_text": "",
                "processing_time": 0
            }
    
    def _clean_donut_output(self, raw_text: str, task_prompt: str) -> str:
        """
        Nettoie la sortie brute Donut
        
        Args:
            raw_text: Texte brut généré par Donut
            task_prompt: Prompt utilisé pour extraction
            
        Returns:
            Texte nettoyé et structuré
        """
        # Suppression tokens spéciaux et prompt
        cleaned = raw_text.replace(task_prompt, "")
        cleaned = cleaned.replace("<s>", "").replace("</s>", "")
        cleaned = cleaned.replace("<pad>", "").replace("<unk>", "")
        
        # Nettoyage espaces multiples
        import re
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        return cleaned
    
    def process_document(self, document_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Point d'entrée principal pour traitement document
        
        Args:
            document_path: Chemin vers document (image ou PDF page)
            
        Returns:
            Résultat extraction avec métadonnées complètes
        """
        document_path = Path(document_path)
        
        if not document_path.exists():
            return {"error": f"Document non trouvé : {document_path}"}
        
        # Vérification format supporté
        supported_formats = {'.png', '.jpg', '.jpeg', '.tiff', '.tif'}
        if document_path.suffix.lower() not in supported_formats:
            return {"error": f"Format non supporté : {document_path.suffix}"}
        
        # Extraction avec métadonnées enrichies
        result = self.extract_text_from_image(document_path)
        
        if result.get("success"):
            result.update({
                "document_path": str(document_path),
                "document_name": document_path.name,
                "file_size_mb": document_path.stat().st_size / (1024 * 1024),
                "timestamp": time.time()
            })
        
        return result
    
    def unload_models(self):
        """Libère mémoire des modèles"""
        if self.donut_model is not None:
            del self.donut_model
            self.donut_model = None
        
        if self.donut_processor is not None:
            del self.donut_processor  
            self.donut_processor = None
        
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
        elif torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        self.is_loaded = False
        logger.info("Modèles Donut déchargés - Mémoire libérée")

# Fonction utilitaire pour usage simple
def extract_text_with_donut(document_path: Union[str, Path], models_path: str = "models/donut") -> Dict[str, Any]:
    """
    Fonction utilitaire pour extraction rapide
    
    Args:
        document_path: Chemin document
        models_path: Chemin modèles
        
    Returns:
        Résultat extraction
    """
    processor = DonutDocumentProcessor(models_path)
    return processor.process_document(document_path)