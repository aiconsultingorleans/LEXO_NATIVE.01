"""
Module de prétraitement d'images pour le pipeline OCR
Implémente les fonctionnalités de correction, débruitage et optimisation d'images
"""

import cv2
import numpy as np
from typing import Tuple, Optional, List
import logging
from pathlib import Path
from PIL import Image, ImageEnhance
import math
from pdf2image import convert_from_path

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Classe principale pour le prétraitement d'images avant OCR
    """
    
    def __init__(self):
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.tiff', '.tif', '.bmp', '.pdf'}
        
    def process_image(self, image_path: str, output_path: Optional[str] = None) -> np.ndarray:
        """
        Pipeline principal de prétraitement d'image
        
        Args:
            image_path: Chemin vers l'image source
            output_path: Chemin de sauvegarde (optionnel)
            
        Returns:
            np.ndarray: Image prétraitée
        """
        try:
            # Chargement de l'image
            image = self.load_image(image_path)
            logger.info(f"Image chargée: {image_path}, dimensions: {image.shape}")
            
            # Pipeline de prétraitement
            image = self.correct_rotation(image)
            image = self.denoise_image(image)
            image = self.detect_and_crop_borders(image)
            image = self.optimize_contrast_brightness(image)
            
            # Sauvegarde si demandée
            if output_path:
                cv2.imwrite(output_path, image)
                logger.info(f"Image prétraitée sauvegardée: {output_path}")
                
            return image
            
        except Exception as e:
            logger.error(f"Erreur lors du prétraitement de {image_path}: {str(e)}")
            raise
    
    def load_image(self, image_path: str) -> np.ndarray:
        """
        Charge une image et gère différents formats (y compris PDF)
        
        Args:
            image_path: Chemin vers l'image ou PDF
            
        Returns:
            np.ndarray: Image en format OpenCV
        """
        path = Path(image_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Image non trouvée: {image_path}")
            
        if path.suffix.lower() not in self.supported_formats:
            raise ValueError(f"Format non supporté: {path.suffix}")
        
        # Traitement spécial pour les PDF
        if path.suffix.lower() == '.pdf':
            try:
                # Convertir la première page du PDF en image
                pages = convert_from_path(str(path), first_page=1, last_page=1, dpi=300)
                if not pages:
                    raise ValueError(f"PDF vide ou illisible: {image_path}")
                
                # Convertir PIL Image en format OpenCV
                pil_image = pages[0]
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
                logger.info(f"PDF converti en image: {image.shape}")
                
            except Exception as e:
                raise ValueError(f"Erreur lors de la conversion PDF: {str(e)}")
        else:
            # Chargement avec OpenCV pour les formats d'images standards
            image = cv2.imread(str(path))
            
            if image is None:
                raise ValueError(f"Impossible de charger l'image: {image_path}")
            
        return image
    
    def correct_rotation(self, image: np.ndarray) -> np.ndarray:
        """
        Détecte et corrige la rotation de l'image
        
        Args:
            image: Image source
            
        Returns:
            np.ndarray: Image avec rotation corrigée
        """
        try:
            # Conversion en niveaux de gris pour la détection
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Détection des contours
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Détection des lignes avec la transformée de Hough
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None and len(lines) > 0:
                angles = []
                
                for line in lines[:20]:  # Prendre les 20 premières lignes
                    if len(line[0]) >= 2:  # Vérifier que la ligne a au moins 2 éléments
                        rho, theta = line[0][:2]
                        angle = theta * 180 / np.pi
                        
                        # Normaliser l'angle entre -45 et 45 degrés
                        if angle > 135:
                            angle = angle - 180
                        elif angle > 45:
                            angle = angle - 90
                            
                        angles.append(angle)
                
                if angles:
                    # Angle moyen de rotation
                    rotation_angle = np.median(angles)
                    
                    # Seulement corriger si l'angle est significatif (> 0.5°)
                    if abs(rotation_angle) > 0.5:
                        logger.info(f"Correction de rotation: {rotation_angle:.2f}°")
                        return self._rotate_image(image, rotation_angle)
            
            return image
            
        except Exception as e:
            logger.warning(f"Erreur lors de la correction de rotation: {str(e)}")
            return image
    
    def _rotate_image(self, image: np.ndarray, angle: float) -> np.ndarray:
        """
        Fait tourner l'image d'un angle donné
        
        Args:
            image: Image source
            angle: Angle de rotation en degrés
            
        Returns:
            np.ndarray: Image tournée
        """
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        
        # Matrice de rotation
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        
        # Calcul des nouvelles dimensions
        cos = np.abs(M[0, 0])
        sin = np.abs(M[0, 1])
        
        new_w = int((h * sin) + (w * cos))
        new_h = int((h * cos) + (w * sin))
        
        # Ajustement de la translation
        M[0, 2] += (new_w / 2) - center[0]
        M[1, 2] += (new_h / 2) - center[1]
        
        # Application de la rotation
        rotated = cv2.warpAffine(image, M, (new_w, new_h), 
                                flags=cv2.INTER_CUBIC, 
                                borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    def denoise_image(self, image: np.ndarray) -> np.ndarray:
        """
        Applique un débruitage intelligent à l'image
        
        Args:
            image: Image source
            
        Returns:
            np.ndarray: Image débruitée
        """
        try:
            # Débruitage avec Non-Local Means (préserve les détails)
            denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
            
            logger.debug("Débruitage appliqué avec succès")
            return denoised
            
        except Exception as e:
            logger.warning(f"Erreur lors du débruitage: {str(e)}")
            return image
    
    def detect_and_crop_borders(self, image: np.ndarray) -> np.ndarray:
        """
        Détecte et supprime les bordures noires/blanches
        
        Args:
            image: Image source
            
        Returns:
            np.ndarray: Image avec bordures supprimées
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Seuillage pour détecter le contenu
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Inversion si nécessaire (fond noir)
            if np.mean(thresh) < 127:
                thresh = cv2.bitwise_not(thresh)
            
            # Trouver le contour principal
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Plus grand contour
                largest_contour = max(contours, key=cv2.contourArea)
                
                # Rectangle englobant
                x, y, w, h = cv2.boundingRect(largest_contour)
                
                # Ajouter une marge de 10 pixels
                margin = 10
                x = max(0, x - margin)
                y = max(0, y - margin)
                w = min(image.shape[1] - x, w + 2 * margin)
                h = min(image.shape[0] - y, h + 2 * margin)
                
                # Découpage
                cropped = image[y:y+h, x:x+w]
                
                logger.debug(f"Bordures détectées et supprimées: {x},{y},{w},{h}")
                return cropped
            
            return image
            
        except Exception as e:
            logger.warning(f"Erreur lors de la détection des bordures: {str(e)}")
            return image
    
    def optimize_contrast_brightness(self, image: np.ndarray) -> np.ndarray:
        """
        Optimise le contraste et la luminosité automatiquement
        
        Args:
            image: Image source
            
        Returns:
            np.ndarray: Image optimisée
        """
        try:
            # Conversion en LAB pour travailler sur la luminance
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # CLAHE (Contrast Limited Adaptive Histogram Equalization)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            
            # Recomposition
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            logger.debug("Optimisation contraste/luminosité appliquée")
            return enhanced
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'optimisation: {str(e)}")
            return image
    
    def split_pages(self, image: np.ndarray) -> List[np.ndarray]:
        """
        Découpe automatiquement les pages multiples (ex: scan de livre ouvert)
        
        Args:
            image: Image source
            
        Returns:
            List[np.ndarray]: Liste des pages détectées
        """
        try:
            height, width = image.shape[:2]
            
            # Si l'image est plus large que haute, possible double page
            if width > height * 1.5:  # Seuil plus strict
                # Division simple au milieu
                mid = width // 2
                
                left_page = image[:, :mid]
                right_page = image[:, mid:]
                
                logger.info("Double page détectée et divisée")
                return [left_page, right_page]
            
            # Sinon, retourner l'image unique
            return [image]
            
        except Exception as e:
            logger.warning(f"Erreur lors du découpage: {str(e)}")
            return [image]
    
    def get_image_quality_score(self, image: np.ndarray) -> float:
        """
        Évalue la qualité de l'image pour OCR (0-1)
        
        Args:
            image: Image à évaluer
            
        Returns:
            float: Score de qualité (0=mauvais, 1=excellent)
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Métriques de qualité
            scores = []
            
            # 1. Netteté (variance du Laplacien)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            sharpness_score = min(laplacian_var / 1000, 1.0)
            scores.append(sharpness_score)
            
            # 2. Contraste (écart-type des pixels)
            contrast_score = gray.std() / 128.0
            scores.append(min(contrast_score, 1.0))
            
            # 3. Résolution (taille de l'image)
            resolution_score = min((gray.shape[0] * gray.shape[1]) / (1920 * 1080), 1.0)
            scores.append(resolution_score)
            
            # Score final pondéré
            quality_score = np.mean(scores)
            
            logger.debug(f"Score de qualité: {quality_score:.3f}")
            return quality_score
            
        except Exception as e:
            logger.warning(f"Erreur lors de l'évaluation qualité: {str(e)}")
            return 0.5  # Score neutre en cas d'erreur


def preprocess_for_ocr(image_path: str, output_dir: Optional[str] = None) -> List[str]:
    """
    Fonction utilitaire pour prétraiter une image pour OCR
    
    Args:
        image_path: Chemin vers l'image source
        output_dir: Dossier de sortie (optionnel)
        
    Returns:
        List[str]: Liste des chemins des images prétraitées
    """
    preprocessor = ImagePreprocessor()
    
    try:
        # Chargement et prétraitement
        image = preprocessor.load_image(image_path)
        processed_image = preprocessor.process_image(image_path)
        
        # Découpage en pages si nécessaire
        pages = preprocessor.split_pages(processed_image)
        
        output_paths = []
        
        for i, page in enumerate(pages):
            if output_dir:
                # Génération du nom de fichier
                input_path = Path(image_path)
                if len(pages) > 1:
                    output_filename = f"{input_path.stem}_page{i+1}_processed{input_path.suffix}"
                else:
                    output_filename = f"{input_path.stem}_processed{input_path.suffix}"
                
                output_path = Path(output_dir) / output_filename
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Sauvegarde
                cv2.imwrite(str(output_path), page)
                output_paths.append(str(output_path))
                
                logger.info(f"Page {i+1} sauvegardée: {output_path}")
        
        return output_paths
        
    except Exception as e:
        logger.error(f"Erreur lors du prétraitement: {str(e)}")
        raise


if __name__ == "__main__":
    # Test du module
    logging.basicConfig(level=logging.INFO)
    
    # Exemple d'utilisation
    test_image = "test_document.jpg"
    if Path(test_image).exists():
        output_paths = preprocess_for_ocr(test_image, "output")
        print(f"Images prétraitées: {output_paths}")