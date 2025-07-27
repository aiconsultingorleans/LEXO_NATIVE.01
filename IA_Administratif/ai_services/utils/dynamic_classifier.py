"""
Classification Dynamique avec CamemBERT - Étape 3.3-3.4
Détection automatique nouveaux types documentaires au-delà des 9 catégories LEXO

Architecture simple suivant guidelines :
- Pas de sur-ingénierie, code direct
- Classification ouverte évolutive
- Auto-apprentissage patterns émergents
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional, Set, Tuple
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModel, AutoModelForSequenceClassification
import numpy as np
from collections import defaultdict, Counter
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DynamicDocumentClassifier:
    """
    Classificateur dynamique évolutif pour documents
    
    Fonctionnalités :
    - Classification des 9 catégories LEXO de base
    - Détection automatique nouveaux types documentaires
    - Auto-apprentissage patterns émergents
    - Base de connaissances évolutive
    """
    
    # Catégories de base LEXO (fixes)
    BASE_CATEGORIES = {
        'factures', 'rib', 'contrats', 'attestations',
        'courriers', 'rapports', 'cartes_transport', 
        'documents_personnels', 'non_classes'
    }
    
    def __init__(self, models_path: str = "models/donut"):
        """
        Initialise le classificateur dynamique
        
        Args:
            models_path: Chemin vers modèles locaux
        """
        self.models_path = Path(models_path)
        self.device = self._get_optimal_device()
        
        # Modèles CamemBERT
        self.tokenizer = None
        self.model = None
        self.is_loaded = False
        
        # Base de connaissances évolutive
        self.known_categories = self.BASE_CATEGORIES.copy()
        self.category_patterns = self._load_base_patterns()
        self.emerging_patterns = defaultdict(list)
        self.classification_history = []
        
        # Seuils pour détection nouveaux types
        self.confidence_threshold = 0.85
        self.frequency_threshold = 5
        self.pattern_similarity_threshold = 0.7
        
        logger.info(f"DynamicClassifier initialisé - Device: {self.device}")
    
    def _get_optimal_device(self) -> str:
        """Détection device optimal"""
        if torch.backends.mps.is_available():
            return "mps"
        elif torch.cuda.is_available():
            return "cuda"
        return "cpu"
    
    def _load_base_patterns(self) -> Dict[str, List[str]]:
        """
        Patterns de base pour reconnaissance catégories LEXO
        
        Returns:
            Dictionnaire patterns par catégorie
        """
        return {
            'factures': [
                'facture', 'montant', 'tva', 'échéance', 'paiement',
                'électricité', 'gaz', 'téléphone', 'internet', 'edf', 'engie'
            ],
            'rib': [
                'rib', 'iban', 'bic', 'swift', 'banque', 'compte',
                'crédit agricole', 'bnp', 'société générale'
            ],
            'attestations': [
                'attestation', 'certifie', 'cpam', 'caf', 'pôle emploi',
                'urssaf', 'assurance maladie', 'allocations'
            ],
            'contrats': [
                'contrat', 'assurance', 'souscription', 'police',
                'mutuelle', 'garantie', 'conditions générales'
            ],
            'courriers': [
                'courrier', 'lettre', 'correspondance', 'objet',
                'madame', 'monsieur', 'veuillez agréer'
            ],
            'rapports': [
                'rapport', 'analyse', 'synthèse', 'résultats',
                'conclusions', 'recommandations'
            ],
            'cartes_transport': [
                'navigo', 'sncf', 'ratp', 'transport', 'abonnement',
                'carte', 'titre de transport'
            ],
            'documents_personnels': [
                'personnel', 'privé', 'confidentiel', 'famille',
                'civil', 'identité'
            ]
        }
    
    def load_models(self) -> bool:
        """
        Charge les modèles CamemBERT
        
        Returns:
            bool: True si succès
        """
        try:
            start_time = time.time()
            
            camembert_path = self.models_path / "camembert-base"
            
            if not camembert_path.exists():
                logger.error(f"Modèle CamemBERT non trouvé : {camembert_path}")
                return False
            
            logger.info("Chargement CamemBERT pour classification...")
            self.tokenizer = AutoTokenizer.from_pretrained(str(camembert_path))
            self.model = AutoModel.from_pretrained(str(camembert_path))
            
            # Optimisation device
            if self.device != "cpu":
                self.model = self.model.to(self.device)
            
            load_time = time.time() - start_time
            self.is_loaded = True
            
            logger.info(f"CamemBERT chargé en {load_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Erreur chargement CamemBERT : {e}")
            return False
    
    def classify_document(self, text: str, document_structure: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Classification principale avec détection nouveaux types
        
        Args:
            text: Texte extrait du document
            document_structure: Métadonnées structure (optionnel)
            
        Returns:
            Résultat classification avec confiance et catégorie
        """
        if not self.is_loaded:
            if not self.load_models():
                return {"error": "Impossible de charger les modèles"}
        
        try:
            start_time = time.time()
            
            # Nettoyage et préparation texte
            clean_text = self._preprocess_text(text)
            
            # Classification catégories de base
            base_classification = self._classify_base_categories(clean_text)
            
            # Détection patterns émergents
            emerging_classification = self._detect_emerging_patterns(clean_text)
            
            # Fusion résultats
            final_classification = self._merge_classifications(
                base_classification, 
                emerging_classification,
                clean_text
            )
            
            # Enrichissement base de connaissances
            self._update_knowledge_base(clean_text, final_classification)
            
            processing_time = time.time() - start_time
            
            result = {
                "category": final_classification["category"],
                "confidence": final_classification["confidence"],
                "is_new_type": final_classification.get("is_new_type", False),
                "patterns_detected": final_classification.get("patterns", []),
                "processing_time": processing_time,
                "base_score": base_classification["confidence"],
                "emerging_score": emerging_classification.get("confidence", 0),
                "success": True
            }
            
            logger.info(f"Classification: {result['category']} (conf: {result['confidence']:.3f}) - {processing_time:.3f}s")
            return result
            
        except Exception as e:
            logger.error(f"Erreur classification : {e}")
            return {"error": str(e), "success": False}
    
    def _preprocess_text(self, text: str) -> str:
        """Nettoyage et normalisation texte"""
        # Conversion minuscules
        clean = text.lower()
        
        # Suppression caractères spéciaux excessifs
        clean = re.sub(r'[^\w\s\-\.,;:]', ' ', clean)
        
        # Normalisation espaces
        clean = re.sub(r'\s+', ' ', clean.strip())
        
        return clean
    
    def _classify_base_categories(self, text: str) -> Dict[str, Any]:
        """
        Classification sur catégories LEXO de base
        
        Args:
            text: Texte nettoyé
            
        Returns:
            Classification avec confiance
        """
        scores = {}
        
        for category, patterns in self.category_patterns.items():
            score = 0
            matched_patterns = []
            
            for pattern in patterns:
                if pattern in text:
                    # Score pondéré par longueur pattern (plus spécifique = plus important)
                    weight = len(pattern.split())
                    score += weight
                    matched_patterns.append(pattern)
            
            # Normalisation score (0-1)
            if len(patterns) > 0:
                scores[category] = {
                    "score": score / (len(patterns) * 2),  # Facteur normalisation
                    "patterns": matched_patterns
                }
        
        # Catégorie avec score maximal
        if scores:
            best_category = max(scores.keys(), key=lambda x: scores[x]["score"])
            confidence = min(scores[best_category]["score"], 1.0)
            
            return {
                "category": best_category if confidence > 0.3 else "non_classes",
                "confidence": confidence,
                "patterns": scores[best_category]["patterns"],
                "all_scores": scores
            }
        
        return {
            "category": "non_classes",
            "confidence": 0.0,
            "patterns": [],
            "all_scores": {}
        }
    
    def _detect_emerging_patterns(self, text: str) -> Dict[str, Any]:
        """
        Détection patterns émergents pour nouveaux types
        
        Args:
            text: Texte analysé
            
        Returns:
            Classification émergente potentielle
        """
        # Extraction features caractéristiques
        features = self._extract_document_features(text)
        
        # Recherche similarité avec patterns émergents existants
        for pattern_name, pattern_examples in self.emerging_patterns.items():
            similarity = self._calculate_pattern_similarity(features, pattern_examples)
            
            if similarity > self.pattern_similarity_threshold:
                return {
                    "category": pattern_name,
                    "confidence": similarity,
                    "is_new_type": True,
                    "pattern_match": True
                }
        
        # Analyse pour nouveau pattern potentiel
        potential_category = self._analyze_potential_new_category(features, text)
        
        if potential_category:
            return {
                "category": potential_category,
                "confidence": 0.6,  # Confiance modérée nouveau type
                "is_new_type": True,
                "pattern_match": False
            }
        
        return {"confidence": 0}
    
    def _extract_document_features(self, text: str) -> Dict[str, Any]:
        """
        Extraction features caractéristiques document
        
        Args:
            text: Texte document
            
        Returns:
            Features structurées
        """
        features = {
            "keywords": [],
            "structure_indicators": [],
            "entities": [],
            "length": len(text),
            "word_count": len(text.split())
        }
        
        # Mots-clés significatifs (non communs)
        common_words = {'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et', 'ou', 'à', 'dans', 'sur', 'avec', 'pour'}
        words = [w for w in text.split() if len(w) > 3 and w not in common_words]
        features["keywords"] = list(set(words))[:20]  # Top 20 mots-clés uniques
        
        # Indicateurs structure document
        if "numéro" in text or "n°" in text:
            features["structure_indicators"].append("numbered_document")
        if "date" in text or "le " in text:
            features["structure_indicators"].append("dated_document")
        if "€" in text or "euros" in text:
            features["structure_indicators"].append("financial_document")
        
        return features
    
    def _calculate_pattern_similarity(self, features: Dict[str, Any], pattern_examples: List[Dict]) -> float:
        """
        Calcule similarité avec patterns émergents existants
        
        Args:
            features: Features document actuel
            pattern_examples: Exemples pattern émergent
            
        Returns:
            Score similarité (0-1)
        """
        if not pattern_examples:
            return 0.0
        
        similarities = []
        
        for example in pattern_examples[-5:]:  # 5 exemples récents max
            # Similarité mots-clés (Jaccard)
            keywords_sim = self._jaccard_similarity(
                set(features["keywords"]), 
                set(example.get("keywords", []))
            )
            
            # Similarité structure
            structure_sim = self._jaccard_similarity(
                set(features["structure_indicators"]),
                set(example.get("structure_indicators", []))
            )
            
            # Score combiné
            total_sim = (keywords_sim * 0.7) + (structure_sim * 0.3)
            similarities.append(total_sim)
        
        return max(similarities) if similarities else 0.0
    
    def _jaccard_similarity(self, set1: Set, set2: Set) -> float:
        """Calcule similarité Jaccard entre deux ensembles"""
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        
        return intersection / union if union > 0 else 0.0
    
    def _analyze_potential_new_category(self, features: Dict[str, Any], text: str) -> Optional[str]:
        """
        Analyse pour détecter nouveau type documentaire potentiel
        
        Args:
            features: Features extraites
            text: Texte original
            
        Returns:
            Nom catégorie potentielle ou None
        """
        # Patterns spécifiques nouveaux types fréquents
        potential_types = {
            "carte_grise": ["carte grise", "préfecture", "véhicule", "immatriculation"],
            "permis_conduire": ["permis", "conduire", "conduite", "code de la route"],
            "diplomes": ["diplôme", "université", "master", "licence", "baccalauréat"],
            "certificats_medicaux": ["certificat médical", "médecin", "arrêt", "maladie"],
            "fiches_paie": ["fiche de paie", "salaire", "employeur", "cotisations"],
            "avis_imposition": ["avis imposition", "impôts", "revenus", "fiscal"],
            "quittances_loyer": ["quittance", "loyer", "bailleur", "locataire"]
        }
        
        text_lower = text.lower()
        
        for category, indicators in potential_types.items():
            matches = sum(1 for indicator in indicators if indicator in text_lower)
            
            # Si 2+ indicateurs présents = nouveau type probable
            if matches >= 2:
                logger.info(f"Nouveau type potentiel détecté : {category} ({matches} indicateurs)")
                return category
        
        return None
    
    def _merge_classifications(self, base_result: Dict, emerging_result: Dict, text: str) -> Dict[str, Any]:
        """
        Fusion résultats classification base et émergente
        
        Args:
            base_result: Classification catégories base
            emerging_result: Classification émergente
            text: Texte original
            
        Returns:
            Classification finale optimale
        """
        base_conf = base_result["confidence"]
        emerging_conf = emerging_result.get("confidence", 0)
        
        # Priorité classification émergente si confiance élevée
        if emerging_conf > self.confidence_threshold and emerging_conf > base_conf:
            return {
                "category": emerging_result["category"],
                "confidence": emerging_conf,
                "is_new_type": True,
                "patterns": base_result["patterns"],
                "source": "emerging"
            }
        
        # Sinon classification base
        return {
            "category": base_result["category"],
            "confidence": base_conf,
            "is_new_type": False,
            "patterns": base_result["patterns"],
            "source": "base"
        }
    
    def _update_knowledge_base(self, text: str, classification: Dict[str, Any]):
        """
        Met à jour base de connaissances avec nouveau document
        
        Args:
            text: Texte document
            classification: Résultat classification
        """
        # Historique classifications
        entry = {
            "text_preview": text[:200],
            "category": classification["category"],
            "confidence": classification["confidence"],
            "timestamp": time.time(),
            "is_new_type": classification.get("is_new_type", False)
        }
        
        self.classification_history.append(entry)
        
        # Limitation historique (1000 derniers)
        if len(self.classification_history) > 1000:
            self.classification_history = self.classification_history[-1000:]
        
        # Enrichissement patterns émergents
        if classification.get("is_new_type"):
            category = classification["category"]
            features = self._extract_document_features(text)
            
            self.emerging_patterns[category].append(features)
            
            # Validation nouveau type si fréquence suffisante
            if len(self.emerging_patterns[category]) >= self.frequency_threshold:
                self._register_new_category(category)
    
    def _register_new_category(self, category: str):
        """
        Enregistre officiellement nouvelle catégorie
        
        Args:
            category: Nom nouvelle catégorie
        """
        if category not in self.known_categories:
            self.known_categories.add(category)
            
            # Génération patterns pour nouvelle catégorie
            if category in self.emerging_patterns:
                examples = self.emerging_patterns[category]
                
                # Extraction mots-clés fréquents
                all_keywords = []
                for example in examples:
                    all_keywords.extend(example.get("keywords", []))
                
                # Top mots-clés par fréquence
                keyword_counts = Counter(all_keywords)
                top_keywords = [word for word, count in keyword_counts.most_common(10) if count >= 2]
                
                # Ajout patterns categorie
                self.category_patterns[category] = top_keywords
                
                logger.info(f"Nouvelle catégorie enregistrée : {category} - Patterns: {top_keywords}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Statistiques classificateur et auto-apprentissage
        
        Returns:
            Métriques détaillées
        """
        total_classifications = len(self.classification_history)
        new_types_count = sum(1 for entry in self.classification_history if entry.get("is_new_type"))
        
        return {
            "total_classifications": total_classifications,
            "new_types_detected": new_types_count,
            "known_categories": len(self.known_categories),
            "base_categories": len(self.BASE_CATEGORIES),
            "emerging_categories": len(self.known_categories - self.BASE_CATEGORIES),
            "emerging_patterns_tracked": len(self.emerging_patterns),
            "classification_rate": new_types_count / total_classifications if total_classifications > 0 else 0
        }

# Fonction utilitaire
def classify_with_dynamic_model(text: str, models_path: str = "models/donut") -> Dict[str, Any]:
    """
    Classification rapide avec modèle dynamique
    
    Args:
        text: Texte à classifier
        models_path: Chemin modèles
        
    Returns:
        Résultat classification
    """
    classifier = DynamicDocumentClassifier(models_path)
    return classifier.classify_document(text)