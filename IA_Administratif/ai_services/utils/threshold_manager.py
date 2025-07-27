"""
Gestionnaire Seuils Sous-dossiers - Étape 3.7
Algorithme intelligent pour création sous-dossiers basée sur fréquence émetteurs

Architecture simple LEXO :
- Seuils adaptatifs par catégorie
- Historique décisions pour apprentissage
- Configuration flexible utilisateur
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ThresholdManager:
    """
    Gestionnaire seuils intelligents pour création sous-dossiers
    
    Fonctionnalités :
    - Seuils adaptatifs par catégorie documentaire
    - Apprentissage patterns utilisateur
    - Prédiction besoins création dossiers
    - Configuration flexible et persistante
    """
    
    def __init__(self, config_path: str = "data/threshold_config.json"):
        """
        Initialise gestionnaire seuils
        
        Args:
            config_path: Chemin configuration seuils
        """
        self.config_path = Path(config_path)
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configuration seuils par défaut
        self.default_thresholds = {
            "factures": 2,      # Factures fréquentes = sous-dossier rapide
            "attestations": 3,  # Attestations moins fréquentes
            "rib": 1,          # RIB = sous-dossier immédiat (rare)
            "contrats": 2,      # Contrats = sous-dossier modéré
            "courriers": 4,     # Courriers nombreux = seuil plus élevé
            "rapports": 3,      # Rapports = seuil modéré
            "cartes_transport": 1,  # Transport = immédiat
            "documents_personnels": 5,  # Personnel = seuil élevé
            "default": 2        # Défaut pour nouvelles catégories
        }
        
        # Chargement configuration
        self.thresholds = self._load_thresholds()
        
        # Historique décisions (apprentissage)
        self.decision_history = []
        self.emitter_analytics = defaultdict(lambda: {
            "total_documents": 0,
            "categories": defaultdict(int),
            "first_seen": None,
            "last_seen": None,
            "folder_created": False,
            "creation_threshold": None
        })
        
        # Métriques performance
        self.performance_metrics = {
            "folders_created": 0,
            "decisions_made": 0,
            "threshold_adjustments": 0,
            "user_overrides": 0
        }
        
        logger.info(f"ThresholdManager initialisé - Config: {self.config_path}")
    
    def _load_thresholds(self) -> Dict[str, int]:
        """
        Charge configuration seuils depuis fichier
        
        Returns:
            Configuration seuils
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved_config = json.load(f)
                
                # Fusion avec défauts (nouvelles catégories)
                merged_config = self.default_thresholds.copy()
                merged_config.update(saved_config.get("thresholds", {}))
                
                logger.info(f"Configuration seuils chargée : {len(merged_config)} catégories")
                return merged_config
                
            except Exception as e:
                logger.warning(f"Erreur chargement config seuils : {e}")
        
        logger.info("Utilisation seuils par défaut")
        return self.default_thresholds.copy()
    
    def _save_thresholds(self):
        """Sauvegarde configuration seuils"""
        try:
            config_data = {
                "thresholds": self.thresholds,
                "last_updated": datetime.now().isoformat(),
                "performance_metrics": self.performance_metrics
            }
            
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"Erreur sauvegarde config seuils : {e}")
    
    def should_create_subfolder(self, 
                               category: str, 
                               emitter_name: str, 
                               current_count: int,
                               emitter_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Décision création sous-dossier basée sur seuils intelligents
        
        Args:
            category: Catégorie document
            emitter_name: Nom émetteur
            current_count: Nombre documents actuels
            emitter_info: Infos supplémentaires émetteur
            
        Returns:
            Décision avec justification
        """
        # Seuil pour cette catégorie
        threshold = self.thresholds.get(category, self.thresholds["default"])
        
        # Décision base sur seuil
        base_decision = current_count >= threshold
        
        # Facteurs ajustement intelligents
        adjustment_factors = self._calculate_adjustment_factors(
            category, emitter_name, current_count, emitter_info
        )
        
        # Application ajustements
        final_threshold = max(1, threshold + adjustment_factors["threshold_adjustment"])
        final_decision = current_count >= final_threshold
        
        # Mise à jour analytics
        self._update_emitter_analytics(category, emitter_name, current_count)
        
        # Log décision
        decision_info = {
            "should_create": final_decision,
            "category": category,
            "emitter": emitter_name,
            "current_count": current_count,
            "base_threshold": threshold,
            "adjusted_threshold": final_threshold,
            "adjustment_factors": adjustment_factors,
            "confidence": self._calculate_decision_confidence(adjustment_factors),
            "timestamp": time.time()
        }
        
        self._log_decision(decision_info)
        
        return decision_info
    
    def _calculate_adjustment_factors(self, 
                                    category: str, 
                                    emitter_name: str, 
                                    current_count: int,
                                    emitter_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Calcule facteurs ajustement seuils intelligents
        
        Args:
            category: Catégorie
            emitter_name: Émetteur
            current_count: Compte actuel
            emitter_info: Infos émetteur
            
        Returns:
            Facteurs ajustement avec justifications
        """
        factors = {
            "threshold_adjustment": 0,
            "reasons": [],
            "emitter_frequency": 0,
            "category_specificity": 0,
            "confidence_bonus": 0
        }
        
        # Facteur 1 : Fréquence émetteur globale
        emitter_stats = self.emitter_analytics.get(emitter_name, {})
        total_docs = emitter_stats.get("total_documents", 0)
        
        if total_docs > 10:  # Émetteur très fréquent
            factors["threshold_adjustment"] -= 1
            factors["reasons"].append("Émetteur très fréquent")
            factors["emitter_frequency"] = 1
        elif total_docs > 5:  # Émetteur modérément fréquent
            factors["threshold_adjustment"] -= 0.5
            factors["reasons"].append("Émetteur fréquent")
            factors["emitter_frequency"] = 0.5
        
        # Facteur 2 : Spécificité catégorie
        category_specificity = self._get_category_specificity(category)
        if category_specificity == "high":  # RIB, cartes transport
            factors["threshold_adjustment"] -= 1
            factors["reasons"].append("Catégorie haute spécificité")
            factors["category_specificity"] = 1
        elif category_specificity == "low":  # Documents personnels, courriers
            factors["threshold_adjustment"] += 1
            factors["reasons"].append("Catégorie basse spécificité")
            factors["category_specificity"] = -0.5
        
        # Facteur 3 : Confiance extraction émetteur
        if emitter_info and emitter_info.get("confidence", 0) > 0.9:
            factors["threshold_adjustment"] -= 0.5
            factors["reasons"].append("Haute confiance émetteur")
            factors["confidence_bonus"] = 0.5
        elif emitter_info and emitter_info.get("confidence", 0) < 0.7:
            factors["threshold_adjustment"] += 0.5
            factors["reasons"].append("Faible confiance émetteur")
            factors["confidence_bonus"] = -0.5
        
        # Facteur 4 : Patterns temporels
        time_factor = self._analyze_temporal_patterns(emitter_name, category)
        factors["threshold_adjustment"] += time_factor["adjustment"]
        if time_factor["reason"]:
            factors["reasons"].append(time_factor["reason"])
        
        # Arrondi ajustement final
        factors["threshold_adjustment"] = round(factors["threshold_adjustment"])
        
        return factors
    
    def _get_category_specificity(self, category: str) -> str:
        """
        Détermine spécificité catégorie pour ajustement seuils
        
        Args:
            category: Catégorie
            
        Returns:
            Niveau spécificité (high/medium/low)
        """
        high_specificity = {"rib", "cartes_transport", "permis_conduire", "carte_grise"}
        low_specificity = {"documents_personnels", "courriers", "non_classes"}
        
        if category in high_specificity:
            return "high"
        elif category in low_specificity:
            return "low"
        else:
            return "medium"
    
    def _analyze_temporal_patterns(self, emitter_name: str, category: str) -> Dict[str, Any]:
        """
        Analyse patterns temporels pour ajustement seuils
        
        Args:
            emitter_name: Nom émetteur
            category: Catégorie
            
        Returns:
            Ajustement temporel avec justification
        """
        emitter_stats = self.emitter_analytics.get(emitter_name, {})
        
        first_seen = emitter_stats.get("first_seen")
        last_seen = emitter_stats.get("last_seen")
        
        if not first_seen or not last_seen:
            return {"adjustment": 0, "reason": None}
        
        # Calcul fréquence récente
        now = time.time()
        days_since_first = (now - first_seen) / (24 * 3600)
        days_since_last = (now - last_seen) / (24 * 3600)
        
        # Émetteur très récent (< 7 jours) = patience
        if days_since_first < 7:
            return {"adjustment": 0.5, "reason": "Émetteur récent, observation"}
        
        # Émetteur inactif récemment (> 30 jours) = seuil plus élevé
        if days_since_last > 30:
            return {"adjustment": 1, "reason": "Émetteur inactif récemment"}
        
        # Émetteur très actif (documents fréquents) = seuil plus bas
        total_docs = emitter_stats.get("total_documents", 0)
        if days_since_first > 0:
            docs_per_day = total_docs / days_since_first
            if docs_per_day > 0.5:  # Plus d'un document tous les 2 jours
                return {"adjustment": -0.5, "reason": "Émetteur très actif"}
        
        return {"adjustment": 0, "reason": None}
    
    def _calculate_decision_confidence(self, adjustment_factors: Dict[str, Any]) -> float:
        """
        Calcule confiance décision basée sur facteurs
        
        Args:
            adjustment_factors: Facteurs ajustement
            
        Returns:
            Score confiance (0-1)
        """
        base_confidence = 0.7
        
        # Bonus confiance émetteur
        base_confidence += adjustment_factors.get("confidence_bonus", 0) * 0.2
        
        # Bonus fréquence émetteur
        base_confidence += adjustment_factors.get("emitter_frequency", 0) * 0.1
        
        # Bonus spécificité catégorie
        base_confidence += adjustment_factors.get("category_specificity", 0) * 0.1
        
        return min(1.0, max(0.0, base_confidence))
    
    def _update_emitter_analytics(self, category: str, emitter_name: str, current_count: int):
        """
        Met à jour analytics émetteur
        
        Args:
            category: Catégorie
            emitter_name: Nom émetteur
            current_count: Compte actuel
        """
        now = time.time()
        
        emitter_stats = self.emitter_analytics[emitter_name]
        
        # Première fois vu
        if emitter_stats["first_seen"] is None:
            emitter_stats["first_seen"] = now
        
        # Dernière fois vu
        emitter_stats["last_seen"] = now
        
        # Mise à jour compteurs
        emitter_stats["total_documents"] = max(emitter_stats["total_documents"], current_count)
        emitter_stats["categories"][category] = max(emitter_stats["categories"][category], current_count)
    
    def _log_decision(self, decision_info: Dict[str, Any]):
        """
        Log décision pour historique et apprentissage
        
        Args:
            decision_info: Infos décision complètes
        """
        self.decision_history.append(decision_info)
        
        # Limitation historique
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
        
        # Mise à jour métriques
        self.performance_metrics["decisions_made"] += 1
        
        if decision_info["should_create"]:
            self.performance_metrics["folders_created"] += 1
        
        # Sauvegarde périodique
        if self.performance_metrics["decisions_made"] % 10 == 0:
            self._save_thresholds()
    
    def adjust_threshold(self, category: str, new_threshold: int, reason: str = "user_override"):
        """
        Ajustement manuel seuil par utilisateur
        
        Args:
            category: Catégorie à ajuster
            new_threshold: Nouveau seuil
            reason: Raison ajustement
        """
        old_threshold = self.thresholds.get(category, self.thresholds["default"])
        
        self.thresholds[category] = max(1, new_threshold)
        
        # Log ajustement
        adjustment_log = {
            "timestamp": time.time(),
            "category": category,
            "old_threshold": old_threshold,
            "new_threshold": new_threshold,
            "reason": reason
        }
        
        logger.info(f"Seuil ajusté : {category} {old_threshold} → {new_threshold} ({reason})")
        
        # Métriques
        self.performance_metrics["threshold_adjustments"] += 1
        if reason == "user_override":
            self.performance_metrics["user_overrides"] += 1
        
        # Sauvegarde
        self._save_thresholds()
    
    def get_threshold_suggestions(self) -> List[Dict[str, Any]]:
        """
        Suggestions ajustements seuils basées sur historique
        
        Returns:
            Liste suggestions avec justifications
        """
        suggestions = []
        
        # Analyse patterns décisions récentes
        recent_decisions = [d for d in self.decision_history if time.time() - d["timestamp"] < 7 * 24 * 3600]
        
        if len(recent_decisions) < 5:
            return suggestions
        
        # Analyse par catégorie
        category_stats = defaultdict(lambda: {"created": 0, "total": 0, "avg_count": 0})
        
        for decision in recent_decisions:
            cat = decision["category"]
            category_stats[cat]["total"] += 1
            if decision["should_create"]:
                category_stats[cat]["created"] += 1
            category_stats[cat]["avg_count"] += decision["current_count"]
        
        # Suggestions ajustements
        for category, stats in category_stats.items():
            if stats["total"] < 3:
                continue
            
            creation_rate = stats["created"] / stats["total"]
            avg_count = stats["avg_count"] / stats["total"]
            current_threshold = self.thresholds.get(category, self.thresholds["default"])
            
            # Seuil trop bas (création excessive)
            if creation_rate > 0.8 and avg_count < current_threshold + 2:
                suggestions.append({
                    "category": category,
                    "current_threshold": current_threshold,
                    "suggested_threshold": current_threshold + 1,
                    "reason": f"Taux création élevé ({creation_rate:.1%})",
                    "priority": "medium",
                    "evidence": f"{stats['created']}/{stats['total']} créations récentes"
                })
            
            # Seuil trop élevé (sous-utilisation)
            elif creation_rate < 0.2 and avg_count > current_threshold + 1:
                suggestions.append({
                    "category": category,
                    "current_threshold": current_threshold,
                    "suggested_threshold": max(1, current_threshold - 1),
                    "reason": f"Taux création faible ({creation_rate:.1%})",
                    "priority": "low",
                    "evidence": f"{stats['created']}/{stats['total']} créations récentes"
                })
        
        return sorted(suggestions, key=lambda x: {"high": 3, "medium": 2, "low": 1}[x["priority"]], reverse=True)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Statistiques complètes gestionnaire seuils
        
        Returns:
            Métriques détaillées
        """
        return {
            "thresholds": dict(self.thresholds),
            "performance_metrics": dict(self.performance_metrics),
            "decision_history_size": len(self.decision_history),
            "tracked_emitters": len(self.emitter_analytics),
            "threshold_suggestions": len(self.get_threshold_suggestions()),
            "last_decision": self.decision_history[-1]["timestamp"] if self.decision_history else None
        }

# Fonction utilitaire
def should_create_folder(category: str, 
                        emitter: str, 
                        count: int,
                        config_path: str = "data/threshold_config.json") -> bool:
    """
    Décision rapide création dossier
    
    Args:
        category: Catégorie document
        emitter: Nom émetteur
        count: Nombre documents actuels
        config_path: Config seuils
        
    Returns:
        bool: True si création recommandée
    """
    manager = ThresholdManager(config_path)
    decision = manager.should_create_subfolder(category, emitter, count)
    return decision["should_create"]