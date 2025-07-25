"""
Module de classification avancée de documents - Étape 4
Implemente une taxonomie complète et un système de scoring intelligent
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class DocumentCategory(Enum):
    """Catégories de documents supportées"""
    ATTESTATIONS = "attestations"
    FACTURES = "factures" 
    IMPOTS = "impots"
    RIB = "rib"
    CONTRATS = "contrats"
    COURRIERS = "courriers"
    SANTE = "sante"
    EMPLOI = "emploi"
    NON_CLASSES = "non_classes"


@dataclass
class ClassificationRule:
    """Règle de classification avec scoring"""
    keywords: List[str]
    patterns: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    score_weight: float = 1.0
    exclusions: List[str] = field(default_factory=list)  # Mots qui invalident la règle
    
    
@dataclass 
class ClassificationResult:
    """Résultat de classification avec détails"""
    category: str
    confidence: float
    score: float
    matched_rules: List[str] = field(default_factory=list)
    reasoning: str = ""


class DocumentClassifier:
    """Classificateur avancé de documents"""
    
    def __init__(self):
        self.classification_rules = self._build_classification_rules()
        
    def _build_classification_rules(self) -> Dict[DocumentCategory, List[ClassificationRule]]:
        """Construit les règles de classification détaillées"""
        return {
            DocumentCategory.ATTESTATIONS: [
                ClassificationRule(
                    keywords=["attestation", "certifie", "certificate", "carte", "permis"],
                    patterns=[r"atteste que", r"certifie que", r"carte\s+\w+", r"permis de"],
                    score_weight=2.0
                ),
                ClassificationRule(
                    keywords=["urssaf", "cpam", "caf", "pole emploi", "assurance"],
                    patterns=[r"attestation\s+\w+", r"certificate"],
                    score_weight=1.8
                ),
                ClassificationRule(
                    keywords=["validité", "valable", "expire", "valide jusqu"],
                    score_weight=1.2
                )
            ],
            
            DocumentCategory.IMPOTS: [
                ClassificationRule(
                    keywords=["urssaf", "déclaration", "trimestre", "cotisation", "charges sociales"],
                    patterns=[r"\d+\w*\s+trimestre", r"déclaration\s+\w+", r"urssaf"],
                    score_weight=2.5,
                    exclusions=["facture", "devis"]  # Pas une facture même si montants
                ),
                ClassificationRule(
                    keywords=["dgfip", "impôt", "fiscal", "déclaration revenus", "avis", "tax"],
                    patterns=[r"avis\s+d[\'']impôt", r"déclaration\s+revenus"],
                    score_weight=2.0
                ),
                ClassificationRule(
                    keywords=["tva", "impôt société", "bénéfice", "résultat fiscal"],
                    score_weight=1.5
                )
            ],
            
            DocumentCategory.FACTURES: [
                ClassificationRule(
                    keywords=["facture", "invoice", "bill", "devis", "commande"],
                    patterns=[r"facture\s+n[°\s]*\d+", r"invoice", r"devis\s+n[°\s]*\d+"],
                    score_weight=2.0,
                    exclusions=["déclaration", "attestation", "urssaf"]
                ),
                ClassificationRule(
                    keywords=["edf", "engie", "orange", "sfr", "bouygues", "free"],
                    patterns=[r"montant\s+à\s+payer", r"échéance"],
                    score_weight=1.8
                ),
                ClassificationRule(
                    keywords=["montant", "ttc", "ht", "tva", "total", "€", "euros"],
                    patterns=[r"\d+[,\.]\d+\s*€", r"total\s*:\s*\d+"],
                    score_weight=1.0,  # Score faible car très commun
                    exclusions=["déclaration", "urssaf", "cotisation"]
                )
            ],
            
            DocumentCategory.RIB: [
                ClassificationRule(
                    keywords=["rib", "relevé identité bancaire", "bank account", "iban", "bic"],
                    patterns=[r"iban\s*:\s*[A-Z]{2}\d{2}", r"bic\s*:\s*[A-Z]{4}"],
                    score_weight=2.5
                ),
                ClassificationRule(
                    keywords=["banque", "crédit agricole", "bnp", "société générale", "lcl"],
                    patterns=[r"code\s+banque", r"compte\s+n[°\s]*\d+"],
                    score_weight=1.5
                )
            ],
            
            DocumentCategory.CONTRATS: [
                ClassificationRule(
                    keywords=["contrat", "contract", "accord", "convention", "engagement"],
                    patterns=[r"contrat\s+\w+", r"signé\s+le", r"partie\s+contractante"],
                    score_weight=2.0
                ),
                ClassificationRule(
                    keywords=["assurance", "mutuelle", "garantie", "police"],
                    patterns=[r"police\s+n[°\s]*\d+", r"assuré\s*:", r"souscripteur"],
                    score_weight=1.8
                )
            ],
            
            DocumentCategory.SANTE: [
                ClassificationRule(
                    keywords=["carte vitale", "cpam", "sécurité sociale", "mutuelle", "médecin"],
                    patterns=[r"carte\s+vitale", r"remboursement", r"consultation", r"assurance\s+maladie"],
                    score_weight=2.5  # Score plus élevé pour les documents santé
                ),
                ClassificationRule(
                    keywords=["pharmacie", "médicament", "analyse", "radiologie", "ordonnance"],
                    patterns=[r"prescription", r"analyse\s+médicale"],
                    score_weight=1.8
                )
            ],
            
            DocumentCategory.EMPLOI: [
                ClassificationRule(
                    keywords=["pole emploi", "fiche de paie", "bulletin salaire", "employeur"],
                    patterns=[r"salaire\s+brut", r"net\s+à\s+payer", r"cotisations"],
                    score_weight=2.0
                ),
                ClassificationRule(
                    keywords=["contrat travail", "cdi", "cdd", "démission", "licenciement"],
                    score_weight=1.8
                )
            ],
            
            DocumentCategory.COURRIERS: [
                ClassificationRule(
                    keywords=["monsieur", "madame", "objet", "courrier", "letter"],
                    patterns=[r"objet\s*:", r"monsieur|madame", r"cordialement", r"salutations"],
                    score_weight=1.0
                )
            ]
        }
    
    def classify_document(self, 
                         filename: str, 
                         ocr_text: str, 
                         entities: List[Any] = None) -> ClassificationResult:
        """
        Classifie un document avec scoring avancé
        
        Args:
            filename: Nom du fichier
            ocr_text: Texte extrait par OCR
            entities: Entités extraites (optionnel)
            
        Returns:
            ClassificationResult avec catégorie et détails
        """
        if not entities:
            entities = []
            
        filename_lower = filename.lower()
        text_lower = ocr_text.lower() if ocr_text else ""
        
        # Calculer les scores pour chaque catégorie
        category_scores = {}
        category_matches = {}
        
        for category, rules in self.classification_rules.items():
            total_score = 0
            matched_rules = []
            
            for rule in rules:
                rule_score = self._evaluate_rule(rule, filename_lower, text_lower, entities)
                if rule_score > 0:
                    total_score += rule_score
                    matched_rules.append(f"{category.value}:{','.join(rule.keywords[:2])}")
            
            if total_score > 0:
                category_scores[category] = total_score
                category_matches[category] = matched_rules
        
        # Déterminer la meilleure catégorie
        if not category_scores:
            return ClassificationResult(
                category=DocumentCategory.NON_CLASSES.value,
                confidence=0.1,
                score=0,
                reasoning="Aucune règle ne correspond"
            )
        
        # Trier par score décroissant
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        best_category, best_score = sorted_categories[0]
        
        # Calculer la confiance
        total_score = sum(category_scores.values())
        confidence = best_score / total_score if total_score > 0 else 0
        
        # Bonus de confiance si écart significatif avec le 2ème
        if len(sorted_categories) > 1:
            second_score = sorted_categories[1][1]
            if best_score > second_score * 1.5:  # 50% d'écart minimum
                confidence = min(0.95, confidence * 1.2)
        
        # Générer le raisonnement
        reasoning = self._generate_reasoning(best_category, category_matches.get(best_category, []))
        
        return ClassificationResult(
            category=best_category.value,
            confidence=confidence,
            score=best_score,
            matched_rules=category_matches.get(best_category, []),
            reasoning=reasoning
        )
    
    def _evaluate_rule(self, 
                      rule: ClassificationRule, 
                      filename: str, 
                      text: str, 
                      entities: List[Any]) -> float:
        """Évalue une règle de classification"""
        score = 0
        
        # Vérifier les exclusions d'abord
        for exclusion in rule.exclusions:
            if exclusion in filename or exclusion in text:
                return 0  # Règle invalidée
        
        # Score des mots-clés
        keyword_matches = 0
        for keyword in rule.keywords:
            if keyword in filename:
                keyword_matches += 2  # Bonus filename
            elif keyword in text:
                keyword_matches += 1
        
        if keyword_matches > 0:
            score += keyword_matches * rule.score_weight
        
        # Score des patterns
        pattern_matches = 0
        for pattern in rule.patterns:
            if re.search(pattern, filename, re.IGNORECASE):
                pattern_matches += 2
            elif re.search(pattern, text, re.IGNORECASE):
                pattern_matches += 1
        
        if pattern_matches > 0:
            score += pattern_matches * rule.score_weight * 1.2  # Bonus patterns
        
        # Score des entités (si disponibles)
        for entity in entities:
            entity_type = entity.get('type', '') if isinstance(entity, dict) else str(entity)
            if entity_type.lower() in [e.lower() for e in rule.entities]:
                score += rule.score_weight * 0.5
        
        return score
    
    def _generate_reasoning(self, category: DocumentCategory, matches: List[str]) -> str:
        """Génère une explication du raisonnement de classification"""
        if not matches:
            return f"Classé comme {category.value} par défaut"
        
        reasoning_map = {
            DocumentCategory.ATTESTATIONS: "Document officiel ou carte d'identité",
            DocumentCategory.IMPOTS: "Document fiscal ou déclaration administrative",
            DocumentCategory.FACTURES: "Facture ou document de paiement",
            DocumentCategory.RIB: "Informations bancaires",
            DocumentCategory.CONTRATS: "Document contractuel",
            DocumentCategory.SANTE: "Document médical ou de santé",
            DocumentCategory.EMPLOI: "Document lié à l'emploi",
            DocumentCategory.COURRIERS: "Correspondance administrative"
        }
        
        base_reason = reasoning_map.get(category, f"Classé comme {category.value}")
        return f"{base_reason} (règles: {len(matches)})"
    
    def get_classification_statistics(self) -> Dict[str, int]:
        """Retourne des statistiques sur les règles de classification"""
        stats = {}
        for category, rules in self.classification_rules.items():
            stats[category.value] = {
                "rules_count": len(rules),
                "total_keywords": sum(len(rule.keywords) for rule in rules),
                "total_patterns": sum(len(rule.patterns) for rule in rules)
            }
        return stats


# Instance globale pour éviter la re-initialisation
_classifier_instance = None

def get_document_classifier() -> DocumentClassifier:
    """Retourne l'instance singleton du classificateur"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = DocumentClassifier()
    return _classifier_instance