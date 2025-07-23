"""
Module d'optimisation pour Apple Silicon
Utilise MLX pour des performances optimales sur les puces M1/M2/M3/M4
"""

import logging
import platform
import time
from typing import Optional, Dict, Any, Union, List
from pathlib import Path
import os

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class AppleSiliconDetector:
    """
    Détecteur de puces Apple Silicon
    """
    
    @staticmethod
    def is_apple_silicon() -> bool:
        """Vérifie si on est sur Apple Silicon"""
        try:
            # Vérifier la plateforme
            if platform.system() != "Darwin":
                return False
            
            # Vérifier l'architecture
            arch = platform.machine()
            return arch == "arm64"
            
        except Exception as e:
            logger.debug(f"Erreur détection Apple Silicon: {e}")
            return False
    
    @staticmethod
    def get_chip_info() -> Dict[str, Any]:
        """Obtient les informations sur la puce"""
        info = {
            "is_apple_silicon": False,
            "architecture": platform.machine(),
            "system": platform.system(),
            "mlx_available": False,
            "mps_available": False
        }
        
        if AppleSiliconDetector.is_apple_silicon():
            info["is_apple_silicon"] = True
            
            # Vérifier MLX
            try:
                import mlx.core as mx
                info["mlx_available"] = True
                info["mlx_version"] = mx.__version__ if hasattr(mx, '__version__') else "unknown"
            except ImportError:
                pass
            
            # Vérifier MPS (Metal Performance Shaders via PyTorch)
            try:
                import torch
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    info["mps_available"] = True
            except ImportError:
                pass
        
        return info


class MLXOptimizer:
    """
    Optimiseur utilisant MLX pour Apple Silicon
    """
    
    def __init__(self):
        """Initialise l'optimiseur MLX"""
        self.mlx_available = False
        self.mx = None
        
        if AppleSiliconDetector.is_apple_silicon():
            try:
                import mlx.core as mx
                import mlx.nn as nn
                self.mx = mx
                self.nn = nn
                self.mlx_available = True
                logger.info("MLX initialisé avec succès pour Apple Silicon")
            except ImportError:
                logger.warning("MLX non disponible, optimisations Apple Silicon désactivées")
    
    def optimize_image_processing(self, image: np.ndarray) -> np.ndarray:
        """
        Optimise le traitement d'image avec MLX
        
        Args:
            image: Image à traiter (numpy array)
            
        Returns:
            Image traitée
        """
        if not self.mlx_available:
            return image
        
        try:
            # Convertir vers MLX array
            mlx_image = self.mx.array(image)
            
            # Traitement optimisé (exemple: normalisation)
            if len(image.shape) == 3:
                # Normalisation par canal
                mean = self.mx.mean(mlx_image, axis=(0, 1), keepdims=True)
                std = self.mx.std(mlx_image, axis=(0, 1), keepdims=True)
                normalized = (mlx_image - mean) / (std + 1e-8)
            else:
                # Image en niveaux de gris
                mean = self.mx.mean(mlx_image)
                std = self.mx.std(mlx_image)
                normalized = (mlx_image - mean) / (std + 1e-8)
            
            # Reconvertir vers numpy
            return np.array(normalized)
            
        except Exception as e:
            logger.debug(f"Erreur MLX, fallback numpy: {e}")
            return image
    
    def batch_process_images(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """
        Traite un batch d'images de manière optimisée
        
        Args:
            images: Liste d'images à traiter
            
        Returns:
            Liste d'images traitées
        """
        if not self.mlx_available or not images:
            return images
        
        try:
            # Stack en un batch MLX
            batch = self.mx.stack([self.mx.array(img) for img in images])
            
            # Traitement batch
            processed_batch = self._apply_batch_transforms(batch)
            
            # Reconvertir vers liste numpy
            return [np.array(img) for img in processed_batch]
            
        except Exception as e:
            logger.debug(f"Erreur batch MLX: {e}")
            return images
    
    def _apply_batch_transforms(self, batch):
        """Applique des transformations sur un batch"""
        # Normalisation batch
        mean = self.mx.mean(batch, axis=(1, 2), keepdims=True)
        std = self.mx.std(batch, axis=(1, 2), keepdims=True)
        normalized = (batch - mean) / (std + 1e-8)
        
        return normalized


class MetalAccelerator:
    """
    Accélérateur utilisant Metal Performance Shaders
    """
    
    def __init__(self):
        """Initialise l'accélérateur Metal"""
        self.metal_available = False
        self.device = None
        
        if AppleSiliconDetector.is_apple_silicon():
            try:
                import torch
                if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                    self.device = torch.device("mps")
                    self.metal_available = True
                    logger.info("Metal Performance Shaders activé")
                else:
                    logger.info("MPS non disponible, utilisation CPU")
            except ImportError:
                logger.warning("PyTorch non disponible pour Metal")
    
    def accelerate_tensor_operations(self, data: np.ndarray) -> np.ndarray:
        """
        Accélère les opérations tensorielles avec Metal
        
        Args:
            data: Données à traiter
            
        Returns:
            Données traitées
        """
        if not self.metal_available:
            return data
        
        try:
            import torch
            
            # Convertir vers tensor PyTorch sur Metal
            tensor = torch.from_numpy(data).to(self.device)
            
            # Opérations accélérées (exemple)
            processed = torch.nn.functional.normalize(tensor, p=2, dim=-1)
            
            # Reconvertir vers numpy
            return processed.cpu().numpy()
            
        except Exception as e:
            logger.debug(f"Erreur Metal: {e}")
            return data


class AppleSiliconOCROptimizer:
    """
    Optimiseur principal pour OCR sur Apple Silicon
    """
    
    def __init__(self):
        """Initialise l'optimiseur OCR Apple Silicon"""
        self.chip_info = AppleSiliconDetector.get_chip_info()
        self.mlx_optimizer = MLXOptimizer() if self.chip_info["is_apple_silicon"] else None
        self.metal_accelerator = MetalAccelerator() if self.chip_info["is_apple_silicon"] else None
        
        logger.info(f"Optimiseur Apple Silicon: {self.chip_info}")
    
    def optimize_preprocessing(self, image: Union[np.ndarray, Image.Image]) -> np.ndarray:
        """
        Optimise le prétraitement d'image pour Apple Silicon
        
        Args:
            image: Image à prétraiter
            
        Returns:
            Image prétraitée
        """
        # Conversion vers numpy si nécessaire
        if isinstance(image, Image.Image):
            np_image = np.array(image)
        else:
            np_image = image.copy()
        
        # Optimisation MLX si disponible
        if self.mlx_optimizer and self.mlx_optimizer.mlx_available:
            return self.mlx_optimizer.optimize_image_processing(np_image)
        
        # Fallback standard
        return np_image
    
    def optimize_batch_inference(self, images: List[Union[np.ndarray, Image.Image]]) -> List[np.ndarray]:
        """
        Optimise l'inférence batch sur Apple Silicon
        
        Args:
            images: Images à traiter
            
        Returns:
            Images traitées
        """
        # Conversion vers numpy
        np_images = []
        for img in images:
            if isinstance(img, Image.Image):
                np_images.append(np.array(img))
            else:
                np_images.append(img.copy())
        
        # Traitement batch MLX si disponible
        if self.mlx_optimizer and self.mlx_optimizer.mlx_available:
            return self.mlx_optimizer.batch_process_images(np_images)
        
        return np_images
    
    def get_optimal_batch_size(self, image_size: tuple, available_memory_gb: float = 8.0) -> int:
        """
        Calcule la taille de batch optimale selon la mémoire disponible
        
        Args:
            image_size: Taille des images (width, height, channels)
            available_memory_gb: Mémoire disponible en GB
            
        Returns:
            Taille de batch recommandée
        """
        if not self.chip_info["is_apple_silicon"]:
            return 1  # Traitement séquentiel pour autres architectures
        
        # Calcul approximatif de la mémoire par image
        w, h = image_size[:2]
        channels = image_size[2] if len(image_size) > 2 else 1
        
        # Estimation mémoire par image (en bytes)
        # Float32 = 4 bytes par pixel
        memory_per_image = w * h * channels * 4
        
        # Apple Silicon a une mémoire unifiée efficace
        # Utiliser ~50% de la mémoire disponible pour le batch
        available_bytes = available_memory_gb * 1024**3 * 0.5
        
        optimal_batch_size = int(available_bytes / memory_per_image)
        
        # Limites raisonnables
        optimal_batch_size = max(1, min(optimal_batch_size, 16))
        
        logger.info(f"Taille de batch optimale: {optimal_batch_size} "
                   f"(image: {w}x{h}x{channels}, mémoire: {available_memory_gb}GB)")
        
        return optimal_batch_size
    
    def benchmark_performance(self, test_images: List[np.ndarray]) -> Dict[str, Any]:
        """
        Benchmarke les performances des optimisations
        
        Args:
            test_images: Images de test
            
        Returns:
            Résultats du benchmark
        """
        results = {
            "chip_info": self.chip_info,
            "test_images": len(test_images),
            "optimizations": {}
        }
        
        if not test_images:
            return results
        
        # Test standard (CPU)
        start_time = time.time()
        standard_results = self._process_images_standard(test_images)
        standard_time = time.time() - start_time
        
        results["optimizations"]["standard_cpu"] = {
            "time": standard_time,
            "throughput": len(test_images) / standard_time if standard_time > 0 else 0
        }
        
        # Test MLX si disponible
        if self.mlx_optimizer and self.mlx_optimizer.mlx_available:
            start_time = time.time()
            mlx_results = self.mlx_optimizer.batch_process_images(test_images.copy())
            mlx_time = time.time() - start_time
            
            results["optimizations"]["mlx"] = {
                "time": mlx_time,
                "throughput": len(test_images) / mlx_time if mlx_time > 0,
                "speedup": standard_time / mlx_time if mlx_time > 0 else 1.0
            }
        
        # Test Metal si disponible
        if self.metal_accelerator and self.metal_accelerator.metal_available:
            start_time = time.time()
            for img in test_images:
                self.metal_accelerator.accelerate_tensor_operations(img)
            metal_time = time.time() - start_time
            
            results["optimizations"]["metal"] = {
                "time": metal_time,
                "throughput": len(test_images) / metal_time if metal_time > 0,
                "speedup": standard_time / metal_time if metal_time > 0 else 1.0
            }
        
        # Recommandations
        results["recommendations"] = self._generate_performance_recommendations(results)
        
        return results
    
    def _process_images_standard(self, images: List[np.ndarray]) -> List[np.ndarray]:
        """Traitement standard CPU pour comparaison"""
        processed = []
        for img in images:
            # Normalisation simple
            if len(img.shape) == 3:
                normalized = (img - img.mean(axis=(0, 1))) / (img.std(axis=(0, 1)) + 1e-8)
            else:
                normalized = (img - img.mean()) / (img.std() + 1e-8)
            processed.append(normalized)
        return processed
    
    def _generate_performance_recommendations(self, benchmark_results: Dict[str, Any]) -> List[str]:
        """Génère des recommandations de performance"""
        recommendations = []
        
        if not self.chip_info["is_apple_silicon"]:
            recommendations.append("Considérer l'upgrade vers Apple Silicon pour de meilleures performances OCR")
            return recommendations
        
        optimizations = benchmark_results.get("optimizations", {})
        
        # Recommandations MLX
        if "mlx" in optimizations:
            speedup = optimizations["mlx"].get("speedup", 1.0)
            if speedup > 1.5:
                recommendations.append(f"MLX offre une accélération {speedup:.1f}x - recommandé pour traitement batch")
            elif speedup < 1.2:
                recommendations.append("MLX n'apporte pas d'amélioration significative pour cette charge")
        else:
            recommendations.append("Installer MLX pour de meilleures performances: pip install mlx")
        
        # Recommandations Metal
        if "metal" in optimizations:
            speedup = optimizations["metal"].get("speedup", 1.0)
            if speedup > 1.3:
                recommendations.append(f"Metal Performance Shaders accélère {speedup:.1f}x")
        
        # Recommandations générales
        if self.chip_info["mlx_available"] and self.chip_info["mps_available"]:
            recommendations.append("Configuration optimale détectée pour Apple Silicon")
        
        return recommendations
    
    def get_memory_info(self) -> Dict[str, Any]:
        """Obtient les informations mémoire Apple Silicon"""
        memory_info = {
            "is_apple_silicon": self.chip_info["is_apple_silicon"],
            "unified_memory": self.chip_info["is_apple_silicon"]  # Apple Silicon a une mémoire unifiée
        }
        
        if self.chip_info["is_apple_silicon"]:
            try:
                # Tentative d'obtenir la mémoire système (macOS)
                import subprocess
                result = subprocess.run(
                    ["sysctl", "hw.memsize"], 
                    capture_output=True, 
                    text=True
                )
                if result.returncode == 0:
                    memory_bytes = int(result.stdout.split(': ')[1])
                    memory_gb = memory_bytes / (1024**3)
                    memory_info["total_memory_gb"] = round(memory_gb, 1)
                    
                    # Recommandations selon la mémoire
                    if memory_gb >= 32:
                        memory_info["ocr_performance_tier"] = "excellent"
                        memory_info["recommended_batch_size"] = 8
                    elif memory_gb >= 16:
                        memory_info["ocr_performance_tier"] = "good"
                        memory_info["recommended_batch_size"] = 4
                    else:
                        memory_info["ocr_performance_tier"] = "basic"
                        memory_info["recommended_batch_size"] = 2
                        
            except Exception as e:
                logger.debug(f"Impossible d'obtenir les infos mémoire: {e}")
        
        return memory_info


# Fonctions utilitaires globales

def get_apple_silicon_config() -> Dict[str, Any]:
    """
    Obtient la configuration optimale pour Apple Silicon
    
    Returns:
        Configuration recommandée
    """
    optimizer = AppleSiliconOCROptimizer()
    
    config = {
        "chip_info": optimizer.chip_info,
        "memory_info": optimizer.get_memory_info(),
        "recommendations": []
    }
    
    if optimizer.chip_info["is_apple_silicon"]:
        config["recommendations"].extend([
            "Utiliser MLX pour les transformers et réseaux de neurones",
            "Activer Metal Performance Shaders pour PyTorch",
            "Privilégier le traitement batch pour maximiser l'efficacité",
            "Utiliser la mémoire unifiée pour éviter les copies"
        ])
        
        # Configuration spécifique selon les capacités
        if optimizer.chip_info["mlx_available"]:
            config["mlx_config"] = {
                "enabled": True,
                "recommended_for": ["trocr", "layoutlm", "transformers"]
            }
        
        if optimizer.chip_info["mps_available"]:
            config["metal_config"] = {
                "enabled": True,
                "pytorch_device": "mps",
                "recommended_for": ["tensor_operations", "neural_networks"]
            }
    
    return config


def optimize_for_apple_silicon(enable_mlx: bool = True, enable_metal: bool = True) -> AppleSiliconOCROptimizer:
    """
    Crée un optimiseur configuré pour Apple Silicon
    
    Args:
        enable_mlx: Activer les optimisations MLX
        enable_metal: Activer Metal Performance Shaders
        
    Returns:
        Optimiseur configuré
    """
    optimizer = AppleSiliconOCROptimizer()
    
    if not optimizer.chip_info["is_apple_silicon"]:
        logger.info("Pas sur Apple Silicon, optimisations désactivées")
        return optimizer
    
    if not enable_mlx:
        optimizer.mlx_optimizer = None
        
    if not enable_metal:
        optimizer.metal_accelerator = None
    
    logger.info(f"Optimiseur Apple Silicon configuré (MLX: {enable_mlx}, Metal: {enable_metal})")
    
    return optimizer