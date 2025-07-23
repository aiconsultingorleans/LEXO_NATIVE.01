"""
Module de détection et extraction de tableaux dans les documents
Utilise OpenCV et des heuristiques pour détecter les structures tabulaires
"""

import logging
import time
from pathlib import Path
from typing import Union, Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

import cv2
import numpy as np
from PIL import Image, ImageDraw
import pandas as pd

# Import des modules locaux
from .tesseract_ocr import TesseractOCR, OCRResult
from .image_preprocessor import ImagePreprocessor

logger = logging.getLogger(__name__)


class TableDetectionMethod(Enum):
    """Méthodes de détection de tableaux"""
    HOUGH_LINES = "hough_lines"
    CONTOURS = "contours"
    MORPHOLOGY = "morphology"
    HYBRID = "hybrid"


@dataclass
class TableCell:
    """Cellule d'un tableau"""
    row: int
    col: int
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    text: str
    confidence: float
    is_header: bool = False


@dataclass
class DetectedTable:
    """Tableau détecté dans un document"""
    bbox: Tuple[int, int, int, int]  # x, y, width, height
    cells: List[TableCell]
    rows: int
    cols: int
    confidence: float
    extraction_method: str
    table_data: Optional[pd.DataFrame] = None


@dataclass
class TableDetectorConfig:
    """Configuration pour le détecteur de tableaux"""
    detection_method: TableDetectionMethod = TableDetectionMethod.HYBRID
    min_table_area: int = 1000  # Aire minimale pour considérer un tableau
    min_line_length: int = 100  # Longueur minimale des lignes détectées
    line_thickness_threshold: int = 3  # Épaisseur maximale des lignes
    cell_min_width: int = 20
    cell_min_height: int = 15
    merge_nearby_lines: bool = True
    line_merge_threshold: int = 10  # Distance pour fusionner les lignes proches
    confidence_threshold: float = 0.6


class TableDetector:
    """
    Détecteur de tableaux dans les documents
    """
    
    def __init__(self, config: Optional[TableDetectorConfig] = None):
        """
        Initialise le détecteur de tableaux
        
        Args:
            config: Configuration personnalisée
        """
        self.config = config or TableDetectorConfig()
        self.ocr_engine = TesseractOCR()
        self.preprocessor = ImagePreprocessor()
        
        logger.info(f"TableDetector initialisé avec méthode: {self.config.detection_method}")
    
    def detect_tables(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        preprocess: bool = True
    ) -> List[DetectedTable]:
        """
        Détecte les tableaux dans une image
        
        Args:
            image: Image à analyser
            preprocess: Appliquer le prétraitement
            
        Returns:
            Liste des tableaux détectés
        """
        start_time = time.time()
        
        try:
            # Conversion et préparation de l'image
            cv_image = self._convert_to_cv2(image)
            original_image = cv_image.copy()
            
            if preprocess:
                logger.debug("Prétraitement de l'image pour détection de tableaux")
                cv_image = self._preprocess_for_table_detection(cv_image)
            
            logger.info(f"Détection de tableaux avec méthode: {self.config.detection_method}")
            
            # Sélection de la méthode de détection
            if self.config.detection_method == TableDetectionMethod.HOUGH_LINES:
                table_regions = self._detect_tables_hough_lines(cv_image)
            elif self.config.detection_method == TableDetectionMethod.CONTOURS:
                table_regions = self._detect_tables_contours(cv_image)
            elif self.config.detection_method == TableDetectionMethod.MORPHOLOGY:
                table_regions = self._detect_tables_morphology(cv_image)
            elif self.config.detection_method == TableDetectionMethod.HYBRID:
                table_regions = self._detect_tables_hybrid(cv_image)
            else:
                raise ValueError(f"Méthode non supportée: {self.config.detection_method}")
            
            # Extraction du contenu des tableaux détectés
            detected_tables = []
            for i, region in enumerate(table_regions):
                logger.debug(f"Extraction du tableau {i+1}/{len(table_regions)}")
                
                table = self._extract_table_content(original_image, region)
                if table and table.cells:  # Vérifier que le tableau n'est pas vide
                    detected_tables.append(table)
            
            processing_time = time.time() - start_time
            logger.info(f"Détection terminée: {len(detected_tables)} tableaux trouvés "
                       f"en {processing_time:.2f}s")
            
            return detected_tables
            
        except Exception as e:
            logger.error(f"Erreur lors de la détection de tableaux: {str(e)}")
            return []
    
    def _convert_to_cv2(self, image_input: Union[str, Path, np.ndarray, Image.Image]) -> np.ndarray:
        """Convertit l'image vers le format OpenCV"""
        if isinstance(image_input, (str, Path)):
            return cv2.imread(str(image_input))
        elif isinstance(image_input, np.ndarray):
            return image_input.copy()
        elif isinstance(image_input, Image.Image):
            return cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
        else:
            raise ValueError(f"Format image non supporté: {type(image_input)}")
    
    def _preprocess_for_table_detection(self, image: np.ndarray) -> np.ndarray:
        """Prétraite l'image spécifiquement pour la détection de tableaux"""
        # Conversion en niveaux de gris
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # Amélioration du contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        # Débruitage léger
        denoised = cv2.bilateralFilter(enhanced, 9, 75, 75)
        
        # Binarisation adaptative pour mieux détecter les lignes
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return binary
    
    def _detect_tables_hough_lines(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Détecte les tableaux en utilisant la transformée de Hough pour les lignes"""
        logger.debug("Détection par lignes de Hough")
        
        # Détection des lignes horizontales
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        horizontal_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Détection des lignes verticales
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        vertical_lines = cv2.morphologyEx(image, cv2.MORPH_OPEN, vertical_kernel)
        
        # Combinaison des lignes
        table_mask = cv2.add(horizontal_lines, vertical_lines)
        
        # Détection des lignes avec HoughLinesP
        lines = cv2.HoughLinesP(
            table_mask, 1, np.pi/180, 
            threshold=50, minLineLength=self.config.min_line_length, maxLineGap=10
        )
        
        if lines is None:
            return []
        
        # Regroupement des lignes pour former des régions rectangulaires
        table_regions = self._group_lines_to_tables(lines, image.shape)
        
        return table_regions
    
    def _detect_tables_contours(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Détecte les tableaux en utilisant la détection de contours"""
        logger.debug("Détection par contours")
        
        # Inversion pour contours externes
        inverted = cv2.bitwise_not(image)
        
        # Dilatation pour connecter les éléments proches
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        dilated = cv2.dilate(inverted, kernel, iterations=2)
        
        # Détection des contours
        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        table_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.config.min_table_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Vérifier les proportions (tables généralement rectangulaires)
                aspect_ratio = w / h
                if 0.5 < aspect_ratio < 5.0:  # Filtre des formes trop étroites ou trop larges
                    table_regions.append((x, y, w, h))
        
        return table_regions
    
    def _detect_tables_morphology(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Détecte les tableaux en utilisant la morphologie mathématique"""
        logger.debug("Détection par morphologie")
        
        # Détection des structures horizontales
        horizontal_size = max(1, image.shape[1] // 20)
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
        horizontal = cv2.morphologyEx(image, cv2.MORPH_OPEN, horizontal_kernel)
        
        # Détection des structures verticales
        vertical_size = max(1, image.shape[0] // 20)
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
        vertical = cv2.morphologyEx(image, cv2.MORPH_OPEN, vertical_kernel)
        
        # Combinaison des structures
        table_structure = cv2.add(horizontal, vertical)
        
        # Dilatation pour combler les trous
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        table_structure = cv2.dilate(table_structure, kernel, iterations=2)
        
        # Détection des contours de tables
        contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        table_regions = []
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.config.min_table_area:
                x, y, w, h = cv2.boundingRect(contour)
                table_regions.append((x, y, w, h))
        
        return table_regions
    
    def _detect_tables_hybrid(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """Détecte les tableaux en combinant plusieurs méthodes"""
        logger.debug("Détection hybride")
        
        # Combiner les résultats de plusieurs méthodes
        hough_regions = self._detect_tables_hough_lines(image)
        contour_regions = self._detect_tables_contours(image)
        morph_regions = self._detect_tables_morphology(image)
        
        # Fusionner et filtrer les régions
        all_regions = hough_regions + contour_regions + morph_regions
        
        if not all_regions:
            return []
        
        # Supprimer les doublons et fusionner les régions qui se chevauchent
        merged_regions = self._merge_overlapping_regions(all_regions)
        
        return merged_regions
    
    def _group_lines_to_tables(self, lines: np.ndarray, image_shape: Tuple[int, int]) -> List[Tuple[int, int, int, int]]:
        """Regroupe les lignes détectées pour former des régions de tableaux"""
        if len(lines) == 0:
            return []
        
        # Séparer les lignes horizontales et verticales
        horizontal_lines = []
        vertical_lines = []
        
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi)
            
            if angle < 15 or angle > 165:  # Ligne horizontale
                horizontal_lines.append((min(x1, x2), y1, max(x1, x2), y1))
            elif 75 < angle < 105:  # Ligne verticale
                vertical_lines.append((x1, min(y1, y2), x1, max(y1, y2)))
        
        if not horizontal_lines or not vertical_lines:
            return []
        
        # Grouper les lignes pour former des rectangles
        table_regions = []
        
        # Approche simplifiée: créer des régions basées sur l'intersection des lignes
        for h_line in horizontal_lines:
            for v_line in vertical_lines:
                # Vérifier s'il y a intersection
                if (h_line[0] <= v_line[0] <= h_line[2] and 
                    v_line[1] <= h_line[1] <= v_line[3]):
                    
                    # Créer une région approximative
                    x = max(0, v_line[0] - 50)
                    y = max(0, h_line[1] - 50)
                    w = min(image_shape[1] - x, 200)
                    h = min(image_shape[0] - y, 150)
                    
                    if w > self.config.cell_min_width and h > self.config.cell_min_height:
                        table_regions.append((x, y, w, h))
        
        return table_regions
    
    def _merge_overlapping_regions(self, regions: List[Tuple[int, int, int, int]]) -> List[Tuple[int, int, int, int]]:
        """Fusionne les régions qui se chevauchent"""
        if not regions:
            return []
        
        # Trier par position x, puis y
        sorted_regions = sorted(regions, key=lambda r: (r[0], r[1]))
        merged = [sorted_regions[0]]
        
        for current in sorted_regions[1:]:
            last_merged = merged[-1]
            
            # Calculer l'intersection
            x1 = max(last_merged[0], current[0])
            y1 = max(last_merged[1], current[1])
            x2 = min(last_merged[0] + last_merged[2], current[0] + current[2])
            y2 = min(last_merged[1] + last_merged[3], current[1] + current[3])
            
            # Vérifier s'il y a chevauchement
            if x1 < x2 and y1 < y2:
                intersection_area = (x2 - x1) * (y2 - y1)
                current_area = current[2] * current[3]
                
                # Fusionner si plus de 30% de chevauchement
                if intersection_area > 0.3 * current_area:
                    # Créer une région fusionnée
                    new_x = min(last_merged[0], current[0])
                    new_y = min(last_merged[1], current[1])
                    new_x2 = max(last_merged[0] + last_merged[2], current[0] + current[2])
                    new_y2 = max(last_merged[1] + last_merged[3], current[1] + current[3])
                    
                    merged[-1] = (new_x, new_y, new_x2 - new_x, new_y2 - new_y)
                else:
                    merged.append(current)
            else:
                merged.append(current)
        
        return merged
    
    def _extract_table_content(self, image: np.ndarray, table_region: Tuple[int, int, int, int]) -> Optional[DetectedTable]:
        """Extrait le contenu d'une région de tableau"""
        x, y, w, h = table_region
        
        # Extraire la région du tableau
        table_image = image[y:y+h, x:x+w]
        
        if table_image.size == 0:
            return None
        
        try:
            # Détection de la grille du tableau
            grid_lines = self._detect_table_grid(table_image)
            
            if not grid_lines:
                logger.debug("Aucune grille détectée, utilisation OCR simple")
                # Fallback: OCR simple sur toute la région
                return self._extract_table_content_simple(table_image, table_region)
            
            # Extraction du contenu cellule par cellule
            cells = self._extract_cells_from_grid(table_image, grid_lines, table_region)
            
            if not cells:
                return None
            
            # Création du tableau structuré
            rows = max(cell.row for cell in cells) + 1
            cols = max(cell.col for cell in cells) + 1
            
            # Calcul de confiance globale
            confidence = sum(cell.confidence for cell in cells) / len(cells) if cells else 0.0
            
            # Création du DataFrame pandas
            table_data = self._create_dataframe_from_cells(cells, rows, cols)
            
            return DetectedTable(
                bbox=table_region,
                cells=cells,
                rows=rows,
                cols=cols,
                confidence=confidence,
                extraction_method=str(self.config.detection_method),
                table_data=table_data
            )
            
        except Exception as e:
            logger.error(f"Erreur extraction contenu tableau: {str(e)}")
            return None
    
    def _detect_table_grid(self, table_image: np.ndarray) -> Dict[str, List[int]]:
        """Détecte la grille d'un tableau (lignes horizontales et verticales)"""
        # Conversion en niveaux de gris si nécessaire
        if len(table_image.shape) == 3:
            gray = cv2.cvtColor(table_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = table_image.copy()
        
        # Binarisation
        _, binary = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        # Détection des lignes horizontales
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (table_image.shape[1]//4, 1))
        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        
        # Détection des lignes verticales
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, table_image.shape[0]//4))
        v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
        
        # Extraction des positions des lignes
        horizontal_positions = []
        vertical_positions = []
        
        # Lignes horizontales
        for y in range(h_lines.shape[0]):
            if np.sum(h_lines[y, :]) > h_lines.shape[1] * 0.5 * 255:
                horizontal_positions.append(y)
        
        # Lignes verticales
        for x in range(v_lines.shape[1]):
            if np.sum(v_lines[:, x]) > v_lines.shape[0] * 0.5 * 255:
                vertical_positions.append(x)
        
        # Filtrer les lignes trop proches
        horizontal_positions = self._filter_close_lines(horizontal_positions)
        vertical_positions = self._filter_close_lines(vertical_positions)
        
        return {
            'horizontal': horizontal_positions,
            'vertical': vertical_positions
        }
    
    def _filter_close_lines(self, positions: List[int]) -> List[int]:
        """Filtre les lignes trop proches les unes des autres"""
        if not positions:
            return []
        
        filtered = [positions[0]]
        for pos in positions[1:]:
            if pos - filtered[-1] > self.config.line_merge_threshold:
                filtered.append(pos)
        
        return filtered
    
    def _extract_cells_from_grid(
        self, 
        table_image: np.ndarray, 
        grid_lines: Dict[str, List[int]], 
        table_region: Tuple[int, int, int, int]
    ) -> List[TableCell]:
        """Extrait les cellules d'un tableau basé sur sa grille"""
        h_lines = grid_lines['horizontal']
        v_lines = grid_lines['vertical']
        
        if len(h_lines) < 2 or len(v_lines) < 2:
            return []
        
        cells = []
        table_x, table_y, _, _ = table_region
        
        # Créer les cellules entre les lignes de grille
        for row in range(len(h_lines) - 1):
            for col in range(len(v_lines) - 1):
                # Coordonnées de la cellule
                y1, y2 = h_lines[row], h_lines[row + 1]
                x1, x2 = v_lines[col], v_lines[col + 1]
                
                # Vérifier la taille minimale
                if (x2 - x1) < self.config.cell_min_width or (y2 - y1) < self.config.cell_min_height:
                    continue
                
                # Extraire l'image de la cellule
                cell_image = table_image[y1:y2, x1:x2]
                
                # OCR sur la cellule
                try:
                    # Conversion pour PIL si nécessaire
                    if len(cell_image.shape) == 3:
                        pil_cell = Image.fromarray(cv2.cvtColor(cell_image, cv2.COLOR_BGR2RGB))
                    else:
                        pil_cell = Image.fromarray(cell_image)
                    
                    ocr_result = self.ocr_engine.extract_text(pil_cell, preprocess=False)
                    
                    # Créer la cellule
                    cell = TableCell(
                        row=row,
                        col=col,
                        bbox=(table_x + x1, table_y + y1, x2 - x1, y2 - y1),
                        text=ocr_result.text.strip(),
                        confidence=ocr_result.confidence,
                        is_header=(row == 0)  # Première ligne = header
                    )
                    
                    cells.append(cell)
                    
                except Exception as e:
                    logger.debug(f"Erreur OCR cellule ({row}, {col}): {e}")
                    # Ajouter une cellule vide
                    cell = TableCell(
                        row=row,
                        col=col,
                        bbox=(table_x + x1, table_y + y1, x2 - x1, y2 - y1),
                        text="",
                        confidence=0.0,
                        is_header=(row == 0)
                    )
                    cells.append(cell)
        
        return cells
    
    def _extract_table_content_simple(
        self, 
        table_image: np.ndarray, 
        table_region: Tuple[int, int, int, int]
    ) -> Optional[DetectedTable]:
        """Extraction simple d'un tableau sans grille détectée"""
        try:
            # Conversion pour PIL
            if len(table_image.shape) == 3:
                pil_image = Image.fromarray(cv2.cvtColor(table_image, cv2.COLOR_BGR2RGB))
            else:
                pil_image = Image.fromarray(table_image)
            
            # OCR sur toute la région
            ocr_result = self.ocr_engine.extract_text(pil_image, preprocess=True)
            
            # Créer une cellule unique
            cells = [TableCell(
                row=0,
                col=0,
                bbox=table_region,
                text=ocr_result.text,
                confidence=ocr_result.confidence,
                is_header=False
            )]
            
            return DetectedTable(
                bbox=table_region,
                cells=cells,
                rows=1,
                cols=1,
                confidence=ocr_result.confidence,
                extraction_method="simple_ocr"
            )
            
        except Exception as e:
            logger.error(f"Erreur extraction simple: {str(e)}")
            return None
    
    def _create_dataframe_from_cells(self, cells: List[TableCell], rows: int, cols: int) -> pd.DataFrame:
        """Crée un DataFrame pandas à partir des cellules"""
        # Initialiser une matrice vide
        data_matrix = [["" for _ in range(cols)] for _ in range(rows)]
        
        # Remplir la matrice avec les données des cellules
        for cell in cells:
            if 0 <= cell.row < rows and 0 <= cell.col < cols:
                data_matrix[cell.row][cell.col] = cell.text
        
        # Créer le DataFrame
        df = pd.DataFrame(data_matrix)
        
        # Utiliser la première ligne comme header si elle semble être un en-tête
        if rows > 1 and any(cells[0].is_header for cells in cells if cells.row == 0):
            df.columns = df.iloc[0]
            df = df.drop(df.index[0])
            df.reset_index(drop=True, inplace=True)
        
        return df
    
    def visualize_detected_tables(
        self,
        image: Union[str, Path, np.ndarray, Image.Image],
        detected_tables: List[DetectedTable],
        output_path: Optional[str] = None
    ) -> Image.Image:
        """
        Visualise les tableaux détectés sur l'image
        
        Args:
            image: Image originale
            detected_tables: Tableaux détectés
            output_path: Chemin de sauvegarde optionnel
            
        Returns:
            Image avec visualisation des tableaux
        """
        # Conversion vers PIL
        if isinstance(image, (str, Path)):
            pil_image = Image.open(image).convert('RGB')
        elif isinstance(image, np.ndarray):
            if len(image.shape) == 3:
                pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            else:
                pil_image = Image.fromarray(image).convert('RGB')
        else:
            pil_image = image.convert('RGB')
        
        img_vis = pil_image.copy()
        draw = ImageDraw.Draw(img_vis)
        
        for i, table in enumerate(detected_tables):
            # Couleur pour le tableau
            color = f"hsl({(i * 60) % 360}, 70%, 50%)"
            
            # Dessiner le contour du tableau
            x, y, w, h = table.bbox
            draw.rectangle(
                [(x, y), (x + w, y + h)],
                outline=color,
                width=3
            )
            
            # Label du tableau
            draw.text(
                (x, y - 20),
                f"Table {i+1} ({table.rows}x{table.cols}) - {table.confidence:.2f}",
                fill=color
            )
            
            # Dessiner les cellules
            for cell in table.cells[:20]:  # Limiter à 20 cellules pour la lisibilité
                cx, cy, cw, ch = cell.bbox
                draw.rectangle(
                    [(cx, cy), (cx + cw, cy + ch)],
                    outline=color,
                    width=1
                )
        
        if output_path:
            img_vis.save(output_path)
            logger.info(f"Visualisation sauvegardée: {output_path}")
        
        return img_vis
    
    def extract_table_as_dict(self, table: DetectedTable) -> Dict[str, Any]:
        """
        Convertit un tableau détecté en dictionnaire
        
        Args:
            table: Tableau détecté
            
        Returns:
            Représentation dictionnaire du tableau
        """
        return {
            "bbox": table.bbox,
            "dimensions": {
                "rows": table.rows,
                "cols": table.cols
            },
            "confidence": table.confidence,
            "extraction_method": table.extraction_method,
            "cells": [
                {
                    "row": cell.row,
                    "col": cell.col,
                    "text": cell.text,
                    "confidence": cell.confidence,
                    "is_header": cell.is_header,
                    "bbox": cell.bbox
                }
                for cell in table.cells
            ],
            "data_matrix": table.table_data.values.tolist() if table.table_data is not None else [],
            "headers": table.table_data.columns.tolist() if table.table_data is not None else []
        }


def detect_tables_simple(
    image: Union[str, Path, np.ndarray, Image.Image],
    method: TableDetectionMethod = TableDetectionMethod.HYBRID
) -> List[Dict[str, Any]]:
    """
    Fonction simple pour détecter des tableaux
    
    Args:
        image: Image à analyser
        method: Méthode de détection
        
    Returns:
        Liste des tableaux sous forme de dictionnaires
    """
    config = TableDetectorConfig(detection_method=method)
    detector = TableDetector(config)
    
    detected_tables = detector.detect_tables(image)
    
    return [detector.extract_table_as_dict(table) for table in detected_tables]