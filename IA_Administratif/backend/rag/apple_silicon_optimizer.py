"""
Optimisations spécifiques Apple Silicon pour le stack RAG.
"""
import logging
import os
import platform
from typing import Dict, Any, Optional
import psutil

logger = logging.getLogger(__name__)

class AppleSiliconOptimizer:
    """Optimisations pour Apple Silicon (M1/M2/M3/M4)."""
    
    def __init__(self):
        self.is_apple_silicon = self._detect_apple_silicon()
        self.memory_gb = self._get_memory_info()
        self.cpu_cores = self._get_cpu_info()
        self.optimizations_applied = False
        
        if self.is_apple_silicon:
            logger.info(f"Apple Silicon détecté - RAM: {self.memory_gb}GB, Cores: {self.cpu_cores}")
        else:
            logger.info("Apple Silicon non détecté - optimisations désactivées")
    
    def _detect_apple_silicon(self) -> bool:
        """Détecte si on est sur Apple Silicon."""
        try:
            # Vérification macOS + ARM
            if platform.system() != "Darwin":
                return False
            
            # Vérification architecture ARM
            machine = platform.machine().lower()
            return machine in ["arm64", "aarch64"]
            
        except Exception as e:
            logger.warning(f"Erreur détection Apple Silicon: {e}")
            return False
    
    def _get_memory_info(self) -> int:
        """Récupère la RAM totale en GB."""
        try:
            return int(psutil.virtual_memory().total / (1024**3))
        except Exception as e:
            logger.warning(f"Erreur détection RAM: {e}")
            return 8  # Fallback
    
    def _get_cpu_info(self) -> int:
        """Récupère le nombre de cores."""
        try:
            return psutil.cpu_count(logical=False) or os.cpu_count() or 8
        except Exception as e:
            logger.warning(f"Erreur détection CPU: {e}")
            return 8  # Fallback
    
    def apply_all_optimizations(self) -> Dict[str, bool]:
        """Applique toutes les optimisations Apple Silicon."""
        try:
            if not self.is_apple_silicon:
                logger.info("Optimisations Apple Silicon ignorées (pas sur Apple Silicon)")
                return {"skipped": True}
            
            results = {}
            
            # Optimisations environnement
            results["env_vars"] = self._set_environment_variables()
            
            # Optimisations PyTorch/MLX
            results["pytorch"] = self._optimize_pytorch()
            results["mlx"] = self._optimize_mlx()
            
            # Optimisations ChromaDB
            results["chromadb"] = self._optimize_chromadb()
            
            # Optimisations mémoire
            results["memory"] = self._optimize_memory_usage()
            
            # Optimisations Sentence Transformers
            results["sentence_transformers"] = self._optimize_sentence_transformers()
            
            self.optimizations_applied = True
            logger.info("Optimisations Apple Silicon appliquées")
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur application optimisations: {e}")
            return {"error": str(e)}
    
    def _set_environment_variables(self) -> bool:
        """Configure les variables d'environnement optimales."""
        try:
            # Optimisations PyTorch Metal
            os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
            os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
            
            # Optimisations OpenMP pour performance
            os.environ["OMP_NUM_THREADS"] = str(min(8, self.cpu_cores))
            
            # Optimisations MLX
            os.environ["MLX_DISABLE_METAL"] = "0"  # Assure Metal activé
            
            # Optimisations générales macOS
            os.environ["VECLIB_MAXIMUM_THREADS"] = str(self.cpu_cores)
            
            logger.info("Variables d'environnement Apple Silicon configurées")
            return True
            
        except Exception as e:
            logger.error(f"Erreur config env vars: {e}")
            return False
    
    def _optimize_pytorch(self) -> bool:
        """Optimise PyTorch pour Apple Silicon."""
        try:
            import torch
            
            # Configuration MPS (Metal Performance Shaders)
            if torch.backends.mps.is_available():
                # Configuration mémoire MPS
                if hasattr(torch.mps, 'set_per_process_memory_fraction'):
                    memory_fraction = min(0.8, self.memory_gb / 32.0)  # Jusqu'à 80% ou proportionnel
                    torch.mps.set_per_process_memory_fraction(memory_fraction)
                    logger.info(f"MPS mémoire configurée: {memory_fraction:.1%}")
                
                # Cache vide pour démarrer proprement
                if hasattr(torch.mps, 'empty_cache'):
                    torch.mps.empty_cache()
                
                logger.info("PyTorch MPS optimisé")
                return True
            else:
                logger.warning("MPS non disponible")
                return False
                
        except ImportError:
            logger.warning("PyTorch non disponible pour optimisations")
            return False
        except Exception as e:
            logger.error(f"Erreur optimisation PyTorch: {e}")
            return False
    
    def _optimize_mlx(self) -> bool:
        """Optimise MLX pour Apple Silicon."""
        try:
            import mlx.core as mx
            
            # Configuration device par défaut
            device = mx.default_device()
            logger.info(f"MLX device: {device}")
            
            # Configuration mémoire MLX si disponible
            if hasattr(mx, 'set_memory_limit'):
                memory_limit = int(self.memory_gb * 0.7 * 1024**3)  # 70% de la RAM
                mx.set_memory_limit(memory_limit)
                logger.info(f"MLX mémoire limitée à {memory_limit // (1024**3)}GB")
            
            logger.info("MLX optimisé pour Apple Silicon")
            return True
            
        except ImportError:
            logger.warning("MLX non disponible")
            return False
        except Exception as e:
            logger.error(f"Erreur optimisation MLX: {e}")
            return False
    
    def _optimize_chromadb(self) -> bool:
        """Optimise ChromaDB pour Apple Silicon."""
        try:
            # Configuration threads pour ChromaDB
            chromadb_threads = min(self.cpu_cores, 8)  # Max 8 threads
            os.environ["CHROMADB_NUM_THREADS"] = str(chromadb_threads)
            
            # Optimisations ONNX Runtime (utilisé par ChromaDB)
            os.environ["ORT_NUM_THREADS"] = str(chromadb_threads)
            
            logger.info(f"ChromaDB optimisé: {chromadb_threads} threads")
            return True
            
        except Exception as e:
            logger.error(f"Erreur optimisation ChromaDB: {e}")
            return False
    
    def _optimize_memory_usage(self) -> bool:
        """Optimise l'utilisation mémoire globale."""
        try:
            # Configuration garbage collector
            import gc
            gc.set_threshold(700, 10, 10)  # Plus agressif sur Apple Silicon
            
            # Configuration cache sizes selon la RAM
            if self.memory_gb >= 32:
                cache_size = "large"
                batch_size = 64
            elif self.memory_gb >= 16:
                cache_size = "medium" 
                batch_size = 32
            else:
                cache_size = "small"
                batch_size = 16
            
            # Variables pour les composants
            os.environ["RAG_CACHE_SIZE"] = cache_size
            os.environ["RAG_BATCH_SIZE"] = str(batch_size)
            
            logger.info(f"Mémoire optimisée: {cache_size} cache, batch {batch_size}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur optimisation mémoire: {e}")
            return False
    
    def _optimize_sentence_transformers(self) -> bool:
        """Optimise Sentence Transformers pour Apple Silicon."""
        try:
            # Configuration optimale selon la RAM
            if self.memory_gb >= 16:
                # Peut charger des modèles plus gros
                os.environ["SENTENCE_TRANSFORMERS_HOME"] = "/tmp/sentence_transformers"
                os.environ["TOKENIZERS_PARALLELISM"] = "true"
            else:
                # Configuration économe
                os.environ["TOKENIZERS_PARALLELISM"] = "false"
            
            logger.info("Sentence Transformers optimisé")
            return True
            
        except Exception as e:
            logger.error(f"Erreur optimisation Sentence Transformers: {e}")
            return False
    
    def get_performance_recommendations(self) -> Dict[str, Any]:
        """Recommandations de performance pour Apple Silicon."""
        try:
            recommendations = {
                "hardware": {
                    "detected_chip": self._detect_chip_type(),
                    "memory_gb": self.memory_gb,
                    "cpu_cores": self.cpu_cores,
                    "optimal_batch_size": self._get_optimal_batch_size(),
                    "recommended_concurrent_users": self._get_concurrent_users_limit()
                },
                "configuration": {
                    "use_metal": True,
                    "use_mlx": True,
                    "enable_quantization": self.memory_gb < 32,
                    "cache_strategy": "memory" if self.memory_gb >= 16 else "disk"
                },
                "performance_tips": [
                    "Utiliser MLX pour Mistral (natif Apple Silicon)",
                    "Activer Metal Performance Shaders pour PyTorch",
                    "Limiter la mémoire GPU à 80% maximum",
                    "Utiliser quantization 4-bit si RAM < 32GB",
                    "Batch processing pour optimiser throughput"
                ]
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Erreur recommandations: {e}")
            return {}
    
    def _detect_chip_type(self) -> str:
        """Détecte le type de puce Apple Silicon."""
        try:
            # Heuristique basée sur les specs
            if self.cpu_cores >= 10 and self.memory_gb >= 32:
                return "M3/M4 Pro/Max"
            elif self.cpu_cores >= 8 and self.memory_gb >= 16:
                return "M2/M3"
            elif self.cpu_cores >= 8:
                return "M1 Pro/Max"
            else:
                return "M1"
        except:
            return "Apple Silicon"
    
    def _get_optimal_batch_size(self) -> int:
        """Calcule la taille de batch optimale."""
        try:
            # Basé sur la RAM disponible
            if self.memory_gb >= 32:
                return 64
            elif self.memory_gb >= 16:
                return 32
            else:
                return 16
        except:
            return 16
    
    def _get_concurrent_users_limit(self) -> int:
        """Limite d'utilisateurs concurrent recommandée."""
        try:
            # Basé sur CPU cores et RAM
            base_limit = min(self.cpu_cores, self.memory_gb // 4)
            return max(2, base_limit)
        except:
            return 4
    
    def monitor_performance(self) -> Dict[str, Any]:
        """Monitore les performances en temps réel."""
        try:
            # Métriques système
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            metrics = {
                "cpu_usage_percent": cpu_percent,
                "memory_used_gb": memory.used / (1024**3),
                "memory_available_gb": memory.available / (1024**3),
                "memory_percent": memory.percent,
                "is_optimized": self.optimizations_applied
            }
            
            # Métriques GPU si MLX disponible
            try:
                import mlx.core as mx
                metrics["gpu_device"] = str(mx.default_device())
            except:
                pass
            
            return metrics
            
        except Exception as e:
            logger.error(f"Erreur monitoring: {e}")
            return {}
    
    def cleanup_memory(self):
        """Nettoie la mémoire (garbage collection + caches)."""
        try:
            import gc
            
            # Python garbage collection
            collected = gc.collect()
            
            # Nettoyage cache PyTorch
            try:
                import torch
                if torch.backends.mps.is_available():
                    torch.mps.empty_cache()
            except:
                pass
            
            # Nettoyage cache MLX
            try:
                import mlx.core as mx
                # MLX gère automatiquement sa mémoire
                pass
            except:
                pass
            
            logger.info(f"Mémoire nettoyée: {collected} objets collectés")
            
        except Exception as e:
            logger.error(f"Erreur nettoyage mémoire: {e}")

# Instance globale de l'optimiseur
apple_optimizer = AppleSiliconOptimizer()