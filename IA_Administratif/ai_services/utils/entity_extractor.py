"""
Extraction Émetteurs avec NER Français - Étape 3.5
Reconnaissance entités nommées optimisée pour organismes français

Architecture simple LEXO :
- Base émetteurs auto-enrichie
- NER CamemBERT français spécialisé  
- Normalisation noms pour arborescence
"""

import logging
import re
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
from collections import defaultdict, Counter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FrenchEntityExtractor:
    """
    Extracteur entités nommées français pour émetteurs documents
    
    Fonctionnalités :
    - Reconnaissance organismes/sociétés français
    - Base émetteurs évolutive auto-enrichie
    - Normalisation noms pour système fichiers
    - Spécialisation entités administratives françaises
    """
    
    def __init__(self, models_path: str = "models/donut"):
        """
        Initialise extracteur NER français
        
        Args:
            models_path: Chemin modèles locaux
        """
        self.models_path = Path(models_path)
        self.device = self._get_optimal_device()
        
        # Modèle NER français
        self.ner_pipeline = None
        self.is_loaded = False
        
        # Base émetteurs français connue
        self.known_emitters = self._load_base_emitters()
        self.detected_emitters = defaultdict(int)  # Compteur fréquence
        
        # Patterns normalisation
        self.normalization_rules = self._load_normalization_rules()
        
        logger.info(f"FrenchEntityExtractor initialisé - Device: {self.device}")
    
    def _get_optimal_device(self) -> str:
        """Détection device optimal"""
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        return "cpu"
    
    def _load_base_emitters(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Base émetteurs français par catégorie
        
        Returns:
            Base structurée émetteurs connus
        """
        return {
            "factures": {
                "energie": ["EDF", "Engie", "Total", "Direct Energie", "Eni", "Vattenfall", "ENEDIS", "GRDF"],
                "telecom": ["Orange", "SFR", "Bouygues Telecom", "Free", "RED by SFR", "Sosh"],
                "eau": ["Veolia", "Suez", "Saur", "Eau de Paris"],
                "transport": ["SNCF", "RATP", "Transilien"]
            },
            "attestations": {
                "secu_sociale": ["CPAM", "CNAM", "MSA", "Régime Social des Indépendants"],
                "emploi": ["Pôle Emploi", "APEC", "Mission Locale"],
                "famille": ["CAF", "Caisse d'Allocations Familiales"],
                "retraite": ["CNAV", "AGIRC-ARRCO", "IRCANTEC"]
            },
            "rib": {
                "banques": [
                    "Crédit Agricole", "BNP Paribas", "Société Générale", "LCL",
                    "Caisse d'Epargne", "Banque Populaire", "Crédit Mutuel",
                    "La Banque Postale", "HSBC", "ING", "Boursorama", "Hello Bank"
                ]
            },
            "impots": {
                "services_fiscaux": ["DGFiP", "Direction Générale des Finances Publiques", "Trésor Public"]
            },
            "contrats": {
                "assurance": ["AXA", "Allianz", "Generali", "MAIF", "MACIF", "MMA", "Groupama"]
            }
        }
    
    def _load_normalization_rules(self) -> Dict[str, str]:
        """
        Règles normalisation noms pour système fichiers
        
        Returns:
            Mapping normalisation
        """
        return {
            # Caractères spéciaux → underscore
            "règle_caracteres": r"[^\w\s-]",
            # Espaces → underscore
            "règle_espaces": r"\s+",
            # Accents → equivalents
            "accents": {
                "é": "e", "è": "e", "ê": "e", "ë": "e",
                "à": "a", "â": "a", "ä": "a",
                "ô": "o", "ö": "o",
                "ù": "u", "û": "u", "ü": "u",
                "ç": "c", "î": "i", "ï": "i"
            },
            # Abréviations connues
            "abreviations": {
                "S.A.S": "SAS", "S.A.R.L": "SARL", "S.A": "SA",
                "E.D.F": "EDF", "G.R.D.F": "GRDF", "S.N.C.F": "SNCF",
                "C.P.A.M": "CPAM", "C.A.F": "CAF", "R.A.T.P": "RATP"
            }
        }
    
    def load_models(self) -> bool:
        """
        Charge modèle NER français CamemBERT
        
        Returns:
            bool: True si succès
        """
        try:
            start_time = time.time()
            
            ner_path = self.models_path / "camembert-ner"
            
            if not ner_path.exists():
                logger.error(f"Modèle NER non trouvé : {ner_path}")
                return False
            
            logger.info("Chargement CamemBERT NER français...")
            
            # Pipeline NER optimisé
            self.ner_pipeline = pipeline(
                "token-classification",
                model=str(ner_path),
                tokenizer=str(ner_path),
                aggregation_strategy="simple",
                device=0 if self.device == "cuda" else -1
            )
            
            # Test rapide
            test_result = self.ner_pipeline("Test EDF Orange")
            
            load_time = time.time() - start_time
            self.is_loaded = True
            
            logger.info(f"NER français chargé en {load_time:.2f}s - Test OK")
            return True
            
        except Exception as e:
            logger.error(f"Erreur chargement NER : {e}")
            return False
    
    def extract_emitters(self, text: str, category_hint: str = None) -> Dict[str, Any]:
        """
        Extraction émetteurs principaux du document
        
        Args:
            text: Texte document
            category_hint: Catégorie suggérée pour filtrage
            
        Returns:
            Émetteurs détectés avec confiance
        """
        if not self.is_loaded:
            if not self.load_models():
                return {"error": "Impossible de charger le modèle NER"}
        
        try:
            start_time = time.time()
            
            # Nettoyage texte pour NER
            clean_text = self._preprocess_for_ner(text)
            
            # Extraction NER CamemBERT
            ner_entities = self._extract_ner_entities(clean_text)
            
            # Recherche base émetteurs connue
            known_matches = self._match_known_emitters(clean_text, category_hint)
            
            # Fusion et scoring
            final_emitters = self._merge_and_score_emitters(ner_entities, known_matches)
            
            # Normalisation noms
            normalized_emitters = self._normalize_emitter_names(final_emitters)
            
            # Mise à jour stats
            self._update_emitter_stats(normalized_emitters)
            
            processing_time = time.time() - start_time
            
            result = {
                "primary_emitter": normalized_emitters[0] if normalized_emitters else None,
                "all_emitters": normalized_emitters,
                "ner_entities": ner_entities,
                "known_matches": known_matches,
                "processing_time": processing_time,
                "success": True
            }
            
            logger.info(f"Extraction émetteurs: {len(normalized_emitters)} trouvés - {processing_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Erreur extraction émetteurs : {e}")
            return {"error": str(e), "success": False}
    
    def _preprocess_for_ner(self, text: str) -> str:
        """
        Préparation texte optimale pour NER
        
        Args:
            text: Texte brut
            
        Returns:
            Texte nettoyé pour NER
        """
        # Limitation longueur pour performance NER
        text = text[:2000]  # 2000 premiers caractères suffisants
        
        # Normalisation espaces
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Conservation majuscules importantes pour NER
        return text
    
    def _extract_ner_entities(self, text: str) -> List[Dict[str, Any]]:
        """
        Extraction entités avec CamemBERT NER
        
        Args:
            text: Texte préparé
            
        Returns:
            Liste entités détectées
        """
        try:
            # NER avec CamemBERT
            ner_results = self.ner_pipeline(text)
            
            # Filtrage entités pertinentes (ORG, PER si entreprise)
            relevant_entities = []
            
            for entity in ner_results:
                label = entity.get("entity_group", "")
                score = entity.get("score", 0)
                word = entity.get("word", "").strip()
                
                # Filtre entités organisationnelles avec score minimal
                if (label in ["ORG", "MISC"] and score > 0.7 and len(word) > 2):
                    relevant_entities.append({
                        "text": word,
                        "label": label,
                        "confidence": score,
                        "source": "ner"
                    })
            
            return relevant_entities
            
        except Exception as e:
            logger.warning(f"Erreur NER : {e}")
            return []
    
    def _match_known_emitters(self, text: str, category_hint: str = None) -> List[Dict[str, Any]]:
        """
        Recherche émetteurs dans base connue
        
        Args:
            text: Texte document
            category_hint: Catégorie pour filtrage
            
        Returns:
            Émetteurs connus trouvés
        """
        text_lower = text.lower()
        matches = []
        
        # Filtre par catégorie si fournie
        categories_to_search = [category_hint] if category_hint in self.known_emitters else self.known_emitters.keys()
        
        for category in categories_to_search:
            category_emitters = self.known_emitters[category]
            
            for subcategory, emitters in category_emitters.items():
                for emitter in emitters:
                    emitter_lower = emitter.lower()
                    
                    # Recherche exacte et variantes
                    if emitter_lower in text_lower:
                        confidence = 0.9  # Haute confiance base connue
                        
                        # Bonus si correspondance exacte mot complet
                        pattern = r'\b' + re.escape(emitter_lower) + r'\b'
                        if re.search(pattern, text_lower):
                            confidence = 0.95
                        
                        matches.append({
                            "text": emitter,
                            "category": category,
                            "subcategory": subcategory,
                            "confidence": confidence,
                            "source": "known_db"
                        })
        
        return matches
    
    def _merge_and_score_emitters(self, ner_entities: List[Dict], known_matches: List[Dict]) -> List[Dict[str, Any]]:
        """
        Fusion et scoring émetteurs NER + base connue
        
        Args:
            ner_entities: Entités NER
            known_matches: Émetteurs base connue
            
        Returns:
            Liste émetteurs fusionnés et scorés
        """
        all_emitters = {}
        
        # Ajout émetteurs base connue (priorité élevée)
        for match in known_matches:
            name = match["text"]
            all_emitters[name] = {
                "name": name,
                "confidence": match["confidence"],
                "source": "known_db",
                "category": match.get("category"),
                "subcategory": match.get("subcategory")
            }
        
        # Ajout entités NER si pas déjà présentes
        for entity in ner_entities:
            name = entity["text"]
            
            # Éviter doublons avec base connue
            if not any(self._names_similar(name, known_name) for known_name in all_emitters.keys()):
                all_emitters[name] = {
                    "name": name,
                    "confidence": entity["confidence"] * 0.8,  # Score NER réduit vs base connue
                    "source": "ner",
                    "category": None,
                    "subcategory": None
                }
        
        # Tri par confiance décroissante
        sorted_emitters = sorted(all_emitters.values(), key=lambda x: x["confidence"], reverse=True)
        
        # Limitation top émetteurs
        return sorted_emitters[:5]
    
    def _names_similar(self, name1: str, name2: str) -> bool:
        """
        Test similarité noms (éviter doublons)
        
        Args:
            name1, name2: Noms à comparer
            
        Returns:
            bool: True si similaires
        """
        # Normalisation pour comparaison
        norm1 = re.sub(r'[^\w]', '', name1.lower())
        norm2 = re.sub(r'[^\w]', '', name2.lower())
        
        # Inclusion ou similarité élevée
        if norm1 in norm2 or norm2 in norm1:
            return True
        
        # Jaccard similarity
        set1, set2 = set(norm1), set(norm2)
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return (intersection / union) > 0.7 if union > 0 else False
    
    def _normalize_emitter_names(self, emitters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Normalisation noms émetteurs pour système fichiers
        
        Args:
            emitters: Liste émetteurs bruts
            
        Returns:
            Émetteurs avec noms normalisés
        """
        normalized = []
        
        for emitter in emitters:
            original_name = emitter["name"]
            normalized_name = self._normalize_single_name(original_name)
            
            normalized.append({
                **emitter,
                "normalized_name": normalized_name,
                "original_name": original_name
            })
        
        return normalized
    
    def _normalize_single_name(self, name: str) -> str:
        """
        Normalisation nom unique
        
        Args:
            name: Nom original
            
        Returns:
            Nom normalisé pour dossiers
        """
        # Application règles abréviations
        normalized = name
        for abbrev, full in self.normalization_rules["abreviations"].items():
            normalized = normalized.replace(abbrev, full)
        
        # Suppression accents
        for accent, replacement in self.normalization_rules["accents"].items():
            normalized = normalized.replace(accent, replacement)
        
        # Caractères spéciaux → underscore
        normalized = re.sub(self.normalization_rules["règle_caracteres"], "_", normalized)
        
        # Espaces → underscore
        normalized = re.sub(self.normalization_rules["règle_espaces"], "_", normalized)
        
        # Nettoyage final
        normalized = normalized.strip("_").replace("__", "_")
        
        # Limitation longueur (éviter noms dossiers trop longs)
        if len(normalized) > 50:
            normalized = normalized[:47] + "..."
        
        return normalized
    
    def _update_emitter_stats(self, emitters: List[Dict[str, Any]]):
        """
        Met à jour statistiques émetteurs détectés
        
        Args:
            emitters: Émetteurs trouvés
        """
        for emitter in emitters:
            name = emitter["normalized_name"]
            self.detected_emitters[name] += 1
    
    def get_frequent_emitters(self, category: str = None, min_frequency: int = 2) -> List[Dict[str, Any]]:
        """
        Émetteurs fréquents détectés
        
        Args:
            category: Filtre par catégorie
            min_frequency: Seuil fréquence minimale
            
        Returns:
            Liste émetteurs fréquents
        """
        frequent = []
        
        for emitter, count in self.detected_emitters.items():
            if count >= min_frequency:
                frequent.append({
                    "name": emitter,
                    "frequency": count,
                    "category": category  # À améliorer avec historique
                })
        
        return sorted(frequent, key=lambda x: x["frequency"], reverse=True)
    
    def suggest_new_folders(self, category: str, min_frequency: int = 2) -> List[str]:
        """
        Suggestions nouveaux dossiers basées sur fréquence
        
        Args:
            category: Catégorie cible
            min_frequency: Seuil création dossier
            
        Returns:
            Liste noms dossiers suggérés
        """
        frequent_emitters = self.get_frequent_emitters(category, min_frequency)
        
        suggested_folders = []
        for emitter in frequent_emitters[:10]:  # Top 10
            folder_name = f"{category.title()}/{emitter['name']}"
            suggested_folders.append(folder_name)
        
        return suggested_folders

# Fonctions utilitaires
def extract_emitter_from_text(text: str, category: str = None, models_path: str = "models/donut") -> Dict[str, Any]:
    """
    Extraction rapide émetteur principal
    
    Args:
        text: Texte document
        category: Catégorie document
        models_path: Chemin modèles
        
    Returns:
        Émetteur principal détecté
    """
    extractor = FrenchEntityExtractor(models_path)
    result = extractor.extract_emitters(text, category)
    
    if result.get("success"):
        return result.get("primary_emitter", {})
    else:
        return {"error": result.get("error")}

# Import manquant
import time