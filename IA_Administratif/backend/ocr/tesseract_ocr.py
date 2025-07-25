"""
Module OCR basé sur Tesseract pour l'extraction de texte
Intègre la détection de langue, l'extraction par zones et les scores de confiance
"""

import pytesseract
import cv2
import numpy as np
from PIL import Image, ImageEnhance
from typing import Dict, List, Tuple, Optional, Union, Any
import logging
import re
import json
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime
import tempfile
import os

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Résultat de l'OCR avec métadonnées"""
    text: str
    confidence: float
    language: str
    processing_time: float
    word_count: int
    line_count: int
    bbox_data: List[Dict[str, Any]]
    detected_entities: Dict[str, List[str]]
    quality_metrics: Dict[str, float]


@dataclass
class TextBlock:
    """Bloc de texte avec position et métadonnées"""
    text: str
    bbox: Tuple[int, int, int, int]  # (x, y, width, height)
    confidence: float
    level: int  # Niveau hiérarchique (0=page, 1=bloc, 2=paragraphe, 3=ligne, 4=mot)


class TesseractOCR:
    """
    Wrapper Python pour Tesseract avec fonctionnalités avancées
    """
    
    def __init__(self, 
                 default_lang: str = 'fra+eng',
                 psm: int = 3,
                 oem: int = 3):
        """
        Initialise le wrapper Tesseract
        
        Args:
            default_lang: Langue par défaut (fra+eng pour français + anglais)
            psm: Page Segmentation Mode (3 = automatic page segmentation)
            oem: OCR Engine Mode (3 = Default, based on what is available)
        """
        self.default_lang = default_lang
        self.psm = psm
        self.oem = oem
        
        # Configuration Tesseract
        self.config = f'--oem {oem} --psm {psm}'
        
        # Langues supportées
        self.supported_languages = {
            'fra': 'Français',
            'eng': 'English', 
            'deu': 'Deutsch',
            'ita': 'Italiano',
            'spa': 'Español',
            'por': 'Português',
            'nld': 'Nederlands'
        }
        
        # Patterns pour extraction d'entités
        self.entity_patterns = {
            'dates': [
                r'\b\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}\b',  # DD/MM/YYYY
                r'\b\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b',
                r'\b\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2}\b'  # YYYY/MM/DD
            ],
            'amounts': [
                r'\b\d{1,3}(?:\s?\d{3})*[,\.]\d{2}\s*€?\b',  # Montants euros
                r'\b€\s*\d{1,3}(?:\s?\d{3})*[,\.]\d{2}\b',
                r'\b\d+[,\.]\d{2}\s*EUR\b'
            ],
            'emails': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'phones': [
                r'\b(?:\+33|0)[1-9](?:[.\-\s]?\d{2}){4}\b',  # Téléphones français
                r'\b\d{10}\b'
            ],
            'siret': [
                r'\b\d{14}\b'  # Numéro SIRET
            ],
            'iban': [
                r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}[A-Z0-9]{1,16}\b'
            ]
        }
        
        logger.info(f"TesseractOCR initialisé - Langue: {default_lang}, PSM: {psm}, OEM: {oem}")
    
    def extract_text(self, 
                    image: Union[np.ndarray, str, Image.Image],
                    lang: Optional[str] = None,
                    preprocess: bool = True) -> OCRResult:
        """
        Extrait le texte d'une image avec métadonnées complètes
        
        Args:
            image: Image (numpy array, chemin fichier, ou PIL Image)
            lang: Langue spécifique (None = auto-détection)
            preprocess: Appliquer le prétraitement
            
        Returns:
            OCRResult: Résultat complet de l'OCR
        """
        start_time = datetime.now()
        
        try:
            # Conversion vers PIL Image
            pil_image = self._convert_to_pil(image)
            
            # Prétraitement si demandé
            if preprocess:
                pil_image = self._preprocess_for_ocr(pil_image)
            
            # Détection de langue si non spécifiée
            if lang is None:
                lang = self._detect_language(pil_image)
            
            # Configuration pour cette extraction
            config = f'{self.config} -l {lang}'
            
            # Extraction du texte
            text = pytesseract.image_to_string(pil_image, config=config).strip()
            
            # Extraction des données détaillées
            data = pytesseract.image_to_data(pil_image, config=config, output_type=pytesseract.Output.DICT)
            
            # Calcul de la confiance moyenne
            confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            # Construction des bboxes
            bbox_data = self._build_bbox_data(data)
            
            # Extraction d'entités
            entities = self._extract_entities(text)
            
            # Métriques de qualité
            quality_metrics = self._calculate_quality_metrics(data, text)
            
            # Temps de traitement
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Statistiques du texte
            word_count = len(text.split())
            line_count = len([line for line in text.split('\n') if line.strip()])
            
            logger.info(f"OCR réussi: {word_count} mots, confiance: {avg_confidence:.1f}%")
            
            return OCRResult(
                text=text,
                confidence=avg_confidence / 100.0,  # Normaliser entre 0 et 1
                language=lang,
                processing_time=processing_time,
                word_count=word_count,
                line_count=line_count,
                bbox_data=bbox_data,
                detected_entities=entities,
                quality_metrics=quality_metrics
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de l'OCR: {str(e)}")
            raise
    
    def extract_text_from_zones(self,
                               image: Union[np.ndarray, str, Image.Image],
                               zones: List[Tuple[int, int, int, int]],
                               lang: Optional[str] = None) -> List[OCRResult]:
        """
        Extrait le texte de zones spécifiques de l'image
        
        Args:
            image: Image source
            zones: Liste des zones (x, y, width, height)
            lang: Langue pour l'OCR
            
        Returns:
            List[OCRResult]: Résultats pour chaque zone
        """
        pil_image = self._convert_to_pil(image)
        results = []
        
        for i, (x, y, w, h) in enumerate(zones):
            try:
                # Découpage de la zone
                cropped = pil_image.crop((x, y, x + w, y + h))
                
                # OCR sur la zone
                result = self.extract_text(cropped, lang=lang, preprocess=True)
                
                # Ajuster les coordonnées des bboxes
                for bbox in result.bbox_data:
                    bbox['left'] += x
                    bbox['top'] += y
                
                results.append(result)
                logger.debug(f"Zone {i+1}/{len(zones)} traitée: {result.word_count} mots")
                
            except Exception as e:
                logger.warning(f"Erreur sur zone {i+1}: {str(e)}")
                # Créer un résultat vide pour cette zone
                results.append(OCRResult(
                    text="", confidence=0.0, language=lang or self.default_lang,
                    processing_time=0.0, word_count=0, line_count=0,
                    bbox_data=[], detected_entities={}, quality_metrics={}
                ))
        
        return results
    
    def extract_from_pdf(self, 
                        pdf_path: str,
                        pages: Optional[List[int]] = None,
                        dpi: int = 300) -> List[OCRResult]:
        """
        Extrait le texte d'un PDF page par page
        
        Args:
            pdf_path: Chemin vers le PDF
            pages: Pages à traiter (None = toutes)
            dpi: Résolution pour la conversion
            
        Returns:
            List[OCRResult]: Résultats par page
        """
        try:
            from pdf2image import convert_from_path
            
            # Conversion du PDF en images
            logger.info(f"Conversion PDF {pdf_path} en images (DPI: {dpi})")
            images = convert_from_path(pdf_path, dpi=dpi, first_page=pages[0] if pages else None,
                                    last_page=pages[-1] if pages else None)
            
            results = []
            total_pages = len(images)
            
            for i, image in enumerate(images):
                logger.info(f"Traitement page {i+1}/{total_pages}")
                
                # OCR sur la page
                result = self.extract_text(image, preprocess=True)
                results.append(result)
            
            logger.info(f"PDF traité: {total_pages} pages")
            return results
            
        except ImportError:
            logger.error("pdf2image non installé. Utilisez: pip install pdf2image")
            raise
        except Exception as e:
            logger.error(f"Erreur lors du traitement PDF: {str(e)}")
            raise
    
    def get_text_blocks(self, 
                       image: Union[np.ndarray, str, Image.Image],
                       lang: Optional[str] = None,
                       level: int = 2) -> List[TextBlock]:
        """
        Extrait les blocs de texte avec leur position
        
        Args:
            image: Image source
            lang: Langue pour l'OCR
            level: Niveau de granularité (1=bloc, 2=paragraphe, 3=ligne, 4=mot)
            
        Returns:
            List[TextBlock]: Blocs de texte avec positions
        """
        pil_image = self._convert_to_pil(image)
        
        if lang is None:
            lang = self._detect_language(pil_image)
        
        config = f'{self.config} -l {lang}'
        
        # Extraction des données détaillées
        data = pytesseract.image_to_data(pil_image, config=config, output_type=pytesseract.Output.DICT)
        
        blocks = []
        current_text = ""
        current_bbox = None
        current_confidences = []
        
        for i in range(len(data['text'])):
            if int(data['level'][i]) == level and data['text'][i].strip():
                # Nouveau bloc
                if current_text and current_bbox:
                    avg_conf = np.mean(current_confidences) if current_confidences else 0
                    blocks.append(TextBlock(
                        text=current_text.strip(),
                        bbox=current_bbox,
                        confidence=avg_conf / 100.0,
                        level=level
                    ))
                
                # Initialiser nouveau bloc
                current_text = data['text'][i]
                current_bbox = (data['left'][i], data['top'][i], 
                              data['width'][i], data['height'][i])
                current_confidences = [int(data['conf'][i])] if int(data['conf'][i]) > 0 else []
                
            elif int(data['level'][i]) > level and data['text'][i].strip():
                # Ajouter au bloc courant
                if current_text:
                    current_text += " " + data['text'][i]
                else:
                    current_text = data['text'][i]
                
                if int(data['conf'][i]) > 0:
                    current_confidences.append(int(data['conf'][i]))
                
                # Étendre la bbox
                if current_bbox:
                    left = min(current_bbox[0], data['left'][i])
                    top = min(current_bbox[1], data['top'][i])
                    right = max(current_bbox[0] + current_bbox[2], 
                              data['left'][i] + data['width'][i])
                    bottom = max(current_bbox[1] + current_bbox[3], 
                               data['top'][i] + data['height'][i])
                    current_bbox = (left, top, right - left, bottom - top)
        
        # Ajouter le dernier bloc
        if current_text and current_bbox:
            avg_conf = np.mean(current_confidences) if current_confidences else 0
            blocks.append(TextBlock(
                text=current_text.strip(),
                bbox=current_bbox,
                confidence=avg_conf / 100.0,
                level=level
            ))
        
        logger.info(f"Extraction de {len(blocks)} blocs de niveau {level}")
        return blocks
    
    def _convert_to_pil(self, image: Union[np.ndarray, str, Image.Image]) -> Image.Image:
        """Convertit différents formats d'image vers PIL Image, y compris PDF"""
        if isinstance(image, str):
            # Gestion spéciale pour les PDFs
            if image.lower().endswith('.pdf'):
                try:
                    from pdf2image import convert_from_path
                    logger.info(f"Conversion PDF vers image: {image}")
                    
                    # Convertir la première page du PDF en image
                    pages = convert_from_path(image, first_page=1, last_page=1, dpi=300)
                    if pages:
                        return pages[0].convert('RGB')
                    else:
                        raise ValueError("PDF vide ou non lisible")
                        
                except ImportError:
                    raise RuntimeError("pdf2image non installé - Impossible de traiter les PDFs")
                except Exception as e:
                    raise ValueError(f"Erreur conversion PDF: {e}")
            else:
                return Image.open(image)
        elif isinstance(image, np.ndarray):
            # OpenCV vers PIL
            if len(image.shape) == 3:
                return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            else:
                return Image.fromarray(image)
        elif isinstance(image, Image.Image):
            return image
        else:
            raise ValueError(f"Format d'image non supporté: {type(image)}")
    
    def _preprocess_for_ocr(self, image: Image.Image) -> Image.Image:
        """Prétraitement spécifique pour améliorer l'OCR"""
        # Conversion en niveaux de gris si nécessaire
        if image.mode != 'L':
            image = image.convert('L')
        
        # Amélioration du contraste
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.2)
        
        # Amélioration de la netteté
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.1)
        
        return image
    
    def _detect_language(self, image: Image.Image) -> str:
        """Détecte automatiquement la langue du document"""
        try:
            # Utiliser OSD (Orientation and Script Detection)
            osd_data = pytesseract.image_to_osd(image, output_type=pytesseract.Output.DICT)
            
            # Tenter une détection rapide sur un échantillon
            sample_text = pytesseract.image_to_string(image, config='--psm 6 -l eng+fra', 
                                                    timeout=10)[:200]
            
            # Heuristiques simples pour détecter le français
            french_indicators = ['le ', 'la ', 'les ', 'de ', 'du ', 'des ', 'et ', 'à ', 'pour ', 'avec ']
            french_score = sum(1 for indicator in french_indicators if indicator in sample_text.lower())
            
            if french_score > 2:
                return 'fra+eng'  # Français + anglais
            else:
                return 'eng+fra'  # Anglais + français
                
        except Exception as e:
            logger.warning(f"Détection de langue échouée: {str(e)}")
            return self.default_lang
    
    def _build_bbox_data(self, data: Dict) -> List[Dict[str, Any]]:
        """Construit les données de bounding boxes"""
        bbox_data = []
        
        for i in range(len(data['text'])):
            if data['text'][i].strip() and int(data['conf'][i]) > 0:
                bbox_data.append({
                    'text': data['text'][i],
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i],
                    'confidence': int(data['conf'][i]),
                    'level': int(data['level'][i])
                })
        
        return bbox_data
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extrait les entités nommées du texte"""
        entities = {}
        
        for entity_type, patterns in self.entity_patterns.items():
            matches = []
            for pattern in patterns:
                matches.extend(re.findall(pattern, text, re.IGNORECASE))
            
            # Nettoyer et dédupliquer
            cleaned_matches = list(set([match.strip() for match in matches if match.strip()]))
            if cleaned_matches:
                entities[entity_type] = cleaned_matches
        
        return entities
    
    def _calculate_quality_metrics(self, data: Dict, text: str) -> Dict[str, float]:
        """Calcule les métriques de qualité de l'OCR"""
        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
        
        metrics = {
            'avg_confidence': np.mean(confidences) if confidences else 0.0,
            'min_confidence': min(confidences) if confidences else 0.0,
            'max_confidence': max(confidences) if confidences else 0.0,
            'std_confidence': np.std(confidences) if confidences else 0.0,
            'text_density': len(text.replace(' ', '')) / max(len(text), 1),
            'word_reliability': len([c for c in confidences if c > 70]) / max(len(confidences), 1)
        }
        
        return metrics
    
    def benchmark_performance(self, test_images: List[str]) -> Dict[str, Any]:
        """
        Benchmark des performances sur un ensemble d'images de test
        
        Args:
            test_images: Liste des chemins vers les images de test
            
        Returns:
            Dict: Statistiques de performance
        """
        results = {
            'total_images': len(test_images),
            'processing_times': [],
            'confidences': [],
            'word_counts': [],
            'errors': 0,
            'avg_processing_time': 0.0,
            'avg_confidence': 0.0,
            'total_words': 0
        }
        
        logger.info(f"Début benchmark sur {len(test_images)} images")
        
        for i, image_path in enumerate(test_images):
            try:
                result = self.extract_text(image_path)
                
                results['processing_times'].append(result.processing_time)
                results['confidences'].append(result.confidence)
                results['word_counts'].append(result.word_count)
                
                logger.debug(f"Image {i+1}/{len(test_images)}: {result.word_count} mots, "
                           f"{result.confidence:.3f} confiance")
                
            except Exception as e:
                logger.error(f"Erreur sur image {image_path}: {str(e)}")
                results['errors'] += 1
        
        # Calcul des moyennes
        if results['processing_times']:
            results['avg_processing_time'] = np.mean(results['processing_times'])
            results['avg_confidence'] = np.mean(results['confidences'])
            results['total_words'] = sum(results['word_counts'])
        
        logger.info(f"Benchmark terminé: {results['avg_processing_time']:.2f}s/image, "
                   f"{results['avg_confidence']:.3f} confiance moyenne")
        
        return results


# Fonction utilitaire pour l'usage simple
def extract_text_simple(image_path: str, lang: str = 'fra+eng') -> str:
    """
    Fonction simple pour extraire du texte d'une image
    
    Args:
        image_path: Chemin vers l'image
        lang: Langue pour l'OCR
        
    Returns:
        str: Texte extrait
    """
    ocr = TesseractOCR(default_lang=lang)
    result = ocr.extract_text(image_path)
    return result.text


if __name__ == "__main__":
    # Test du module
    logging.basicConfig(level=logging.INFO)
    
    # Exemple d'utilisation
    ocr = TesseractOCR()
    print("✅ Module TesseractOCR initialisé")
    print(f"✅ Langues supportées: {list(ocr.supported_languages.keys())}")
    print("✅ Prêt pour l'extraction de texte")