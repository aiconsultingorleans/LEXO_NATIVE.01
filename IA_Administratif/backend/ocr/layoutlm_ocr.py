"""
Module OCR avec compréhension de structure utilisant LayoutLMv3
Analyse la structure des documents pour une extraction plus précise
"""

import logging
import time
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import torch
import numpy as np
from PIL import Image, ImageDraw
import cv2
from transformers import LayoutLMv3Processor, LayoutLMv3ForTokenClassification
import pytesseract

# Import des modules locaux
from .tesseract_ocr import OCRResult, TextBlock
from .image_preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class DocumentRegion(Enum):
    """Types de régions dans un document"""
    TITLE = "title"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FIGURE = "figure"
    HEADER = "header"
    FOOTER = "footer"
    LIST = "list"
    CAPTION = "caption"
    OTHER = "other"


@dataclass
class StructuredRegion:
    """Région structurée d'un document"""
    region_type: DocumentRegion
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    text: str
    confidence: float
    tokens: List[str]
    token_bboxes: List[Tuple[int, int, int, int]]
    semantic_label: Optional[str] = None


@dataclass
class LayoutLMConfig:
    """Configuration pour LayoutLMv3"""
    model_name: str = "microsoft/layoutlmv3-base"
    max_sequence_length: int = 512
    device: str = "auto"
    use_gpu: bool = True
    confidence_threshold: float = 0.7
    cache_dir: Optional[str] = None


class LayoutLMEngine:
    """
    Moteur OCR avec compréhension de structure basé sur LayoutLMv3
    """
    
    def __init__(self, config: Optional[LayoutLMConfig] = None):
        """
        Initialise le moteur LayoutLM
        
        Args:
            config: Configuration personnalisée
        """
        self.config = config or LayoutLMConfig()
        self.processor = None
        self.model = None
        self.device = None
        self.preprocessor = ImagePreprocessor()
        
        # Labels de classification de tokens (exemple pour documents d'affaires)
        self.token_labels = {
            0: "O",          # Outside
            1: "B-HEADER",   # Début d'en-tête
            2: "I-HEADER",   # Suite d'en-tête
            3: "B-TITLE",    # Début de titre
            4: "I-TITLE",    # Suite de titre
            5: "B-DATE",     # Début de date
            6: "I-DATE",     # Suite de date
            7: "B-AMOUNT",   # Début de montant
            8: "I-AMOUNT",   # Suite de montant
            9: "B-ADDRESS",  # Début d'adresse
            10: "I-ADDRESS", # Suite d'adresse
            11: "B-COMPANY", # Début de nom de société
            12: "I-COMPANY", # Suite de nom de société
            13: "B-OTHER",   # Début d'autre entité
            14: "I-OTHER"    # Suite d'autre entité
        }
        
        self._initialize_model()
    
    def _initialize_model(self):
        """Initialise le modèle LayoutLMv3"""
        try:
            logger.info(f"Initialisation LayoutLMv3: {self.config.model_name}")
            
            # Détection du device
            if self.config.device == "auto":
                if torch.cuda.is_available() and self.config.use_gpu:
                    self.device = torch.device("cuda")
                    logger.info("GPU CUDA détecté pour LayoutLM")
                elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available() and self.config.use_gpu:
                    self.device = torch.device("mps")
                    logger.info("GPU Metal (Apple Silicon) détecté pour LayoutLM")
                else:
                    self.device = torch.device("cpu")
                    logger.info("Utilisation CPU pour LayoutLM")
            else:
                self.device = torch.device(self.config.device)
            
            # Chargement du processeur
            logger.info("Chargement du processeur LayoutLMv3...")
            self.processor = LayoutLMv3Processor.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir
            )
            
            # Chargement du modèle
            logger.info("Chargement du modèle LayoutLMv3...")
            self.model = LayoutLMv3ForTokenClassification.from_pretrained(
                self.config.model_name,
                cache_dir=self.config.cache_dir
            )
            
            self.model.to(self.device)
            self.model.eval()
            
            logger.info(f"LayoutLMv3 initialisé avec succès sur {self.device}")
            
        except Exception as e:
            logger.error(f"Erreur initialisation LayoutLMv3: {str(e)}")
            raise RuntimeError(f"Impossible d'initialiser LayoutLMv3: {str(e)}")
    
    def _convert_to_pil(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> Image.Image:
        """Convertit l'image vers PIL Image"""
        if isinstance(image_input, (str, Path)):
            return Image.open(image_input).convert('RGB')
        elif isinstance(image_input, np.ndarray):
            if len(image_input.shape) == 3:
                image_input = cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB)
            return Image.fromarray(image_input).convert('RGB')
        elif isinstance(image_input, Image.Image):
            return image_input.convert('RGB')
        else:
            raise ValueError(f"Format image non supporté: {type(image_input)}")
    
    def extract_structured_text(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        preprocess: bool = True
    ) -> Tuple[OCRResult, List[StructuredRegion]]:
        """
        Extrait le texte avec analyse de structure
        
        Args:
            image: Image à analyser
            preprocess: Appliquer le prétraitement
            
        Returns:
            Tuple (résultat OCR global, régions structurées)
        """
        start_time = time.time()
        
        try:
            # Conversion vers PIL
            pil_image = self._convert_to_pil(image)
            logger.info(f"Analyse structurée LayoutLM, taille: {pil_image.size}")
            
            # Prétraitement si demandé
            if preprocess:
                np_image = np.array(pil_image)
                if len(np_image.shape) == 3:
                    np_image = cv2.cvtColor(np_image, cv2.COLOR_RGB2BGR)
                
                processed_image = self.preprocessor.process_image_array(np_image)
                
                if len(processed_image.shape) == 3:
                    processed_image = cv2.cvtColor(processed_image, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(processed_image)
            
            # Extraction OCR basique avec Tesseract pour obtenir les mots et positions
            logger.debug("Extraction OCR basique pour les positions...")
            ocr_data = pytesseract.image_to_data(
                pil_image, 
                output_type=pytesseract.Output.DICT,
                lang='fra+eng'
            )
            
            # Construction des tokens et bounding boxes
            words = []
            boxes = []
            
            for i in range(len(ocr_data['text'])):
                word = ocr_data['text'][i].strip()
                if word and int(ocr_data['conf'][i]) > 30:  # Confiance minimum
                    words.append(word)
                    
                    # Bounding box normalisée (format LayoutLM)
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    
                    # Normalisation par rapport à la taille de l'image
                    img_width, img_height = pil_image.size
                    norm_box = [
                        int(1000 * x / img_width),
                        int(1000 * y / img_height),
                        int(1000 * (x + w) / img_width),
                        int(1000 * (y + h) / img_height)
                    ]
                    boxes.append(norm_box)
            
            if not words:
                logger.warning("Aucun mot détecté par OCR")
                return self._create_empty_result(time.time() - start_time)
            
            logger.info(f"Mots détectés: {len(words)}")
            
            # Préparation des inputs pour LayoutLMv3
            encoding = self.processor(
                pil_image,
                words,
                boxes=boxes,
                return_tensors="pt",
                truncation=True,
                max_length=self.config.max_sequence_length,
                padding="max_length"
            )
            
            # Déplacement vers le device
            for key in encoding:
                if isinstance(encoding[key], torch.Tensor):
                    encoding[key] = encoding[key].to(self.device)
            
            # Prédiction
            logger.debug("Prédiction LayoutLMv3...")
            with torch.no_grad():
                outputs = self.model(**encoding)
                predictions = torch.nn.functional.softmax(outputs.logits, dim=-1)
                predicted_token_class_ids = predictions.argmax(-1)
            
            # Extraction des prédictions
            token_boxes = encoding['bbox'][0]
            predicted_tokens = predicted_token_class_ids[0]
            
            # Construction du résultat OCR global
            full_text = " ".join(words)
            processing_time = time.time() - start_time
            
            ocr_result = OCRResult(
                text=full_text,
                confidence=float(predictions.max()),
                language="auto",
                processing_time=processing_time,
                word_count=len(words),
                line_count=len(full_text.split('\n')),
                bbox_data=[],
                detected_entities=self._extract_entities_from_predictions(words, predicted_tokens),
                quality_metrics={
                    "model_used": "LayoutLMv3",
                    "model_name": self.config.model_name,
                    "device": str(self.device),
                    "preprocessing_applied": preprocess,
                    "tokens_processed": len(words)
                }
            )
            
            # Construction des régions structurées
            structured_regions = self._build_structured_regions(
                words, boxes, predicted_tokens, pil_image.size
            )
            
            logger.info(f"LayoutLM terminé: {len(structured_regions)} régions, "
                       f"temps: {processing_time:.2f}s")
            
            return ocr_result, structured_regions
            
        except Exception as e:
            logger.error(f"Erreur LayoutLM: {str(e)}")
            processing_time = time.time() - start_time
            
            empty_result = OCRResult(
                text="",
                confidence=0.0,
                language="unknown",
                processing_time=processing_time,
                word_count=0,
                line_count=0,
                bbox_data=[],
                detected_entities={},
                quality_metrics={"error": str(e), "model_used": "LayoutLMv3_failed"}
            )
            
            return empty_result, []
    
    def _extract_entities_from_predictions(
        self, 
        words: List[str], 
        predictions: torch.Tensor
    ) -> Dict[str, List[str]]:
        """Extrait les entités basées sur les prédictions LayoutLM"""
        entities = {
            'headers': [],
            'titles': [],
            'dates': [],
            'amounts': [],
            'addresses': [],
            'companies': [],
            'others': []
        }
        
        current_entity = None
        current_tokens = []
        
        for i, (word, pred_id) in enumerate(zip(words, predictions)):
            pred_label = self.token_labels.get(int(pred_id), "O")
            
            if pred_label.startswith("B-"):  # Début d'entité
                # Sauvegarder l'entité précédente si elle existe
                if current_entity and current_tokens:
                    entity_text = " ".join(current_tokens)
                    entities[current_entity].append(entity_text)
                
                # Commencer une nouvelle entité
                entity_type = pred_label[2:].lower()
                if entity_type == "header":
                    current_entity = "headers"
                elif entity_type == "title":
                    current_entity = "titles"
                elif entity_type == "date":
                    current_entity = "dates"
                elif entity_type == "amount":
                    current_entity = "amounts"
                elif entity_type == "address":
                    current_entity = "addresses"
                elif entity_type == "company":
                    current_entity = "companies"
                else:
                    current_entity = "others"
                
                current_tokens = [word]
                
            elif pred_label.startswith("I-") and current_entity:  # Continuation d'entité
                current_tokens.append(word)
                
            else:  # O ou changement d'entité
                # Sauvegarder l'entité précédente
                if current_entity and current_tokens:
                    entity_text = " ".join(current_tokens)
                    entities[current_entity].append(entity_text)
                
                current_entity = None
                current_tokens = []
        
        # Sauvegarder la dernière entité
        if current_entity and current_tokens:
            entity_text = " ".join(current_tokens)
            entities[current_entity].append(entity_text)
        
        return entities
    
    def _build_structured_regions(
        self,
        words: List[str],
        boxes: List[List[int]],
        predictions: torch.Tensor,
        image_size: Tuple[int, int]
    ) -> List[StructuredRegion]:
        """Construit les régions structurées du document"""
        regions = []
        img_width, img_height = image_size
        
        current_region = None
        current_words = []
        current_boxes = []
        
        for i, (word, box, pred_id) in enumerate(zip(words, boxes, predictions)):
            pred_label = self.token_labels.get(int(pred_id), "O")
            
            # Déterminer le type de région
            if pred_label.startswith("B-"):
                # Terminer la région précédente
                if current_region and current_words:
                    region = self._create_region(
                        current_region, current_words, current_boxes, 
                        img_width, img_height
                    )
                    regions.append(region)
                
                # Commencer une nouvelle région
                entity_type = pred_label[2:].lower()
                current_region = self._map_entity_to_region(entity_type)
                current_words = [word]
                current_boxes = [box]
                
            elif pred_label.startswith("I-") and current_region:
                # Continuer la région actuelle
                current_words.append(word)
                current_boxes.append(box)
                
            else:
                # Terminer la région actuelle si elle existe
                if current_region and current_words:
                    region = self._create_region(
                        current_region, current_words, current_boxes,
                        img_width, img_height
                    )
                    regions.append(region)
                
                current_region = None
                current_words = []
                current_boxes = []
        
        # Terminer la dernière région
        if current_region and current_words:
            region = self._create_region(
                current_region, current_words, current_boxes,
                img_width, img_height
            )
            regions.append(region)
        
        return regions
    
    def _map_entity_to_region(self, entity_type: str) -> DocumentRegion:
        """Mappe un type d'entité vers un type de région"""
        mapping = {
            "header": DocumentRegion.HEADER,
            "title": DocumentRegion.TITLE,
            "date": DocumentRegion.PARAGRAPH,
            "amount": DocumentRegion.PARAGRAPH,
            "address": DocumentRegion.PARAGRAPH,
            "company": DocumentRegion.PARAGRAPH,
            "other": DocumentRegion.OTHER
        }
        return mapping.get(entity_type, DocumentRegion.OTHER)
    
    def _create_region(
        self,
        region_type: DocumentRegion,
        words: List[str],
        boxes: List[List[int]],
        img_width: int,
        img_height: int
    ) -> StructuredRegion:
        """Crée une région structurée"""
        # Calculer la bounding box globale
        min_x = min(box[0] for box in boxes) * img_width // 1000
        min_y = min(box[1] for box in boxes) * img_height // 1000
        max_x = max(box[2] for box in boxes) * img_width // 1000
        max_y = max(box[3] for box in boxes) * img_height // 1000
        
        global_bbox = (min_x, min_y, max_x - min_x, max_y - min_y)
        
        # Convertir les boxes individuelles
        token_bboxes = []
        for box in boxes:
            x1 = box[0] * img_width // 1000
            y1 = box[1] * img_height // 1000
            x2 = box[2] * img_width // 1000
            y2 = box[3] * img_height // 1000
            token_bboxes.append((x1, y1, x2 - x1, y2 - y1))
        
        # Calculer une confiance moyenne (simplifiée)
        confidence = 0.8  # LayoutLM est généralement fiable
        
        return StructuredRegion(
            region_type=region_type,
            bbox=global_bbox,
            text=" ".join(words),
            confidence=confidence,
            tokens=words,
            token_bboxes=token_bboxes
        )
    
    def _create_empty_result(self, processing_time: float) -> Tuple[OCRResult, List[StructuredRegion]]:
        """Crée un résultat vide en cas d'échec"""
        empty_result = OCRResult(
            text="",
            confidence=0.0,
            language="unknown",
            processing_time=processing_time,
            word_count=0,
            line_count=0,
            bbox_data=[],
            detected_entities={},
            quality_metrics={"model_used": "LayoutLMv3", "no_text_detected": True}
        )
        return empty_result, []
    
    def visualize_structure(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        regions: List[StructuredRegion],
        output_path: Optional[str] = None
    ) -> Image.Image:
        """
        Visualise la structure détectée sur l'image
        
        Args:
            image: Image originale
            regions: Régions structurées détectées
            output_path: Chemin de sauvegarde optionnel
            
        Returns:
            Image avec visualisation des régions
        """
        pil_image = self._convert_to_pil(image)
        img_vis = pil_image.copy()
        draw = ImageDraw.Draw(img_vis)
        
        # Couleurs pour chaque type de région
        colors = {
            DocumentRegion.TITLE: "red",
            DocumentRegion.HEADER: "blue", 
            DocumentRegion.PARAGRAPH: "green",
            DocumentRegion.TABLE: "purple",
            DocumentRegion.FIGURE: "orange",
            DocumentRegion.FOOTER: "brown",
            DocumentRegion.LIST: "pink",
            DocumentRegion.CAPTION: "gray",
            DocumentRegion.OTHER: "black"
        }
        
        for region in regions:
            color = colors.get(region.region_type, "black")
            x, y, w, h = region.bbox
            
            # Dessiner le rectangle
            draw.rectangle(
                [(x, y), (x + w, y + h)],
                outline=color,
                width=2
            )
            
            # Ajouter le label
            draw.text(
                (x, y - 15),
                f"{region.region_type.value} ({region.confidence:.2f})",
                fill=color
            )
        
        if output_path:
            img_vis.save(output_path)
            logger.info(f"Visualisation sauvegardée: {output_path}")
        
        return img_vis
    
    def get_model_info(self) -> Dict[str, Any]:
        """Retourne les informations sur le modèle LayoutLM"""
        return {
            "model_name": self.config.model_name,
            "device": str(self.device),
            "max_sequence_length": self.config.max_sequence_length,
            "confidence_threshold": self.config.confidence_threshold,
            "supported_labels": list(self.token_labels.values()),
            "regions_supported": [region.value for region in DocumentRegion]
        }


def extract_structured_text_simple(
    image: Union[str, Path, np.ndarray, Image.Image],
    model_name: str = "microsoft/layoutlmv3-base"
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Fonction simple pour extraction structurée
    
    Args:
        image: Image à analyser
        model_name: Modèle LayoutLM à utiliser
        
    Returns:
        Tuple (texte complet, régions avec métadonnées)
    """
    config = LayoutLMConfig(model_name=model_name)
    engine = LayoutLMEngine(config)
    
    ocr_result, regions = engine.extract_structured_text(image)
    
    regions_dict = []
    for region in regions:
        regions_dict.append({
            "type": region.region_type.value,
            "text": region.text,
            "bbox": region.bbox,
            "confidence": region.confidence,
            "tokens": region.tokens
        })
    
    return ocr_result.text, regions_dict