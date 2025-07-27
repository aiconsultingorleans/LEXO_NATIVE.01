"""
Module de classification avancée de documents - Étape 3 (Enhanced)
Implemente une taxonomie complète avec extraction d'entités françaises
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import time

# Imports pour intégration Étape 3
from .french_entity_extractor import get_french_entity_extractor, EntityExtractionResult
from .filename_classifier import get_filename_classifier, FilenameClassification

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
    """Résultat de classification avec détails enrichis Étape 3"""
    category: str
    confidence: float
    score: float
    matched_rules: List[str] = field(default_factory=list)
    reasoning: str = ""
    # Nouveaux champs Étape 3
    filename_prediction: Optional[FilenameClassification] = None
    extracted_entities: Optional[EntityExtractionResult] = None
    entity_boost: float = 0.0
    processing_times: Dict[str, float] = field(default_factory=dict)


class DocumentClassifier:
    """Classificateur avancé de documents avec extraction d'entités Étape 3"""
    
    def __init__(self):
        self.classification_rules = self._build_classification_rules()
        
        # Intégration services Étape 3
        self.entity_extractor = get_french_entity_extractor()
        self.filename_classifier = get_filename_classifier()
        
        # Configuration scoring entités
        self.entity_scoring_weights = {
            'siret': 3.0,      # Très important pour classification administrative
            'tva': 2.5,        # Important pour factures/déclarations
            'iban': 2.8,       # Très important pour RIB
            'montant': 1.5,    # Modéré (présent dans beaucoup de catégories)
            'date': 1.0,       # Faible (très commun)
            'organisme': 2.0,  # Important pour attestations/impôts
            'entreprise': 1.8  # Modéré pour factures/contrats
        }
        
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
                    keywords=[
                        "urssaf", "union de recouvrement", "acoss", 
                        "déclaration sociale nominative", "dsn",
                        "cotisation", "charges sociales", "prélèvement social"
                    ],
                    patterns=[
                        r"urssaf\s+[a-zé\s\-]+",  # URSSAF région
                        r"\d+[èe]r?\s+trimestre\s+\d{4}",
                        r"déclaration\s+trimestrielle",
                        r"appel\s+de\s+cotisation",
                        r"échéance\s+urssaf",
                        r"auto[\-\s]?entrepreneur",
                        r"travailleur\s+indépendant"
                    ],
                    score_weight=3.0,  # Poids très élevé pour URSSAF
                    exclusions=["facture", "devis", "commande"]
                ),
                ClassificationRule(
                    keywords=[
                        "dgfip", "direction générale des finances publiques",
                        "impôt", "fiscal", "déclaration revenus", "avis imposition",
                        "taxe habitation", "taxe foncière", "impôt société"
                    ],
                    patterns=[
                        r"avis\s+d[\'']impôt\s+sur",
                        r"déclaration\s+de\s+revenus?\s+\d{4}",
                        r"impôt\s+sur\s+le\s+revenu",
                        r"revenus?\s+\d{4}",
                        r"acompte\s+provisionnel",
                        r"solde\s+d[\'']impôt"
                    ],
                    score_weight=2.5
                ),
                ClassificationRule(
                    keywords=[
                        "tva", "taxe sur la valeur ajoutée", "ca3", "ca12",
                        "impôt société", "is", "bénéfice", "résultat fiscal",
                        "liasse fiscale", "cerfa"
                    ],
                    patterns=[
                        r"déclaration\s+tva\s+ca\d+",
                        r"période\s+du\s+\d{1,2}[/\-]\d{1,2}[/\-]\d{4}",
                        r"tva\s+collectée",
                        r"tva\s+déductible",
                        r"crédit\s+de\s+tva",
                        r"cerfa\s+n[°\s]*\d+"
                    ],
                    score_weight=2.2
                ),
                ClassificationRule(
                    keywords=[
                        "mise en demeure", "recouvrement", "majorations",
                        "pénalités", "créance", "redressement",
                        "contrôle fiscal", "vérification"
                    ],
                    patterns=[
                        r"mise\s+en\s+demeure\s+de\s+payer",
                        r"majorations?\s+de\s+retard",
                        r"pénalités?\s+pour\s+retard",
                        r"contrôle\s+fiscal\s+n[°\s]*\d+",
                        r"redressement\s+fiscal"
                    ],
                    score_weight=2.8,  # Score très élevé pour documents officiels
                    exclusions=["facture", "devis"]
                )
            ],
            
            DocumentCategory.FACTURES: [
                ClassificationRule(
                    keywords=["facture", "invoice", "bill", "devis", "commande", "note de frais"],
                    patterns=[
                        r"facture\s+n[°\s]*:?\s*\d+",
                        r"invoice\s+n[°\s]*:?\s*\d+", 
                        r"devis\s+n[°\s]*:?\s*\d+",
                        r"bon\s+de\s+commande\s+n[°\s]*:?\s*\d+",
                        r"référence\s+facture"
                    ],
                    score_weight=2.5,
                    exclusions=["déclaration", "attestation", "urssaf", "cotisation", "impôt", "contrat", "assurance", "police"]
                ),
                ClassificationRule(
                    keywords=[
                        "edf", "enedis", "engie", "total", "antargaz",  # Énergie
                        "orange", "sfr", "bouygues telecom", "free", "red by sfr",  # Télécom
                        "veolia", "suez", "saur",  # Eau
                        "darty", "fnac", "amazon", "cdiscount"  # Commerce
                    ],
                    patterns=[
                        r"montant\s+à\s+payer\s*:?\s*\d+[,\.]\d+\s*€",
                        r"échéance\s*:?\s*\d{1,2}[/\-]\d{1,2}[/\-]\d{4}",
                        r"date\s+limite\s+de\s+paiement",
                        r"abonnement\s+[a-zé\s]+",
                        r"consommation\s+du\s+\d+"
                    ],
                    score_weight=2.2
                ),
                ClassificationRule(
                    keywords=["montant", "ttc", "ht", "tva", "total", "sous-total", "remise"],
                    patterns=[
                        r"\d{1,3}(?:\s?\d{3})*[,\.]\d{2}\s*€",  # Format français
                        r"total\s+ttc\s*:?\s*\d+[,\.]\d+",
                        r"montant\s+ht\s*:?\s*\d+[,\.]\d+",
                        r"tva\s+\d+[,\.]\d+%",
                        r"net\s+à\s+payer\s*:?\s*\d+"
                    ],
                    score_weight=1.2,  # Score modéré car assez commun
                    exclusions=["déclaration", "urssaf", "cotisation", "bulletin", "salaire", "contrat", "assurance", "police"]
                ),
                ClassificationRule(
                    keywords=[
                        "siret", "siren", "rcs", "tva intracommunautaire", 
                        "code ape", "capital social", "raison sociale"
                    ],
                    patterns=[
                        r"siret\s*:?\s*\d{3}\s?\d{3}\s?\d{3}\s?\d{5}",
                        r"siren\s*:?\s*\d{3}\s?\d{3}\s?\d{3}",
                        r"tva\s+fr\s*\d{11}",
                        r"rcs\s+[a-zé\s]+\s+\d+"
                    ],
                    score_weight=1.5,
                    exclusions=["déclaration", "urssaf", "attestation"]
                )
            ],
            
            DocumentCategory.RIB: [
                ClassificationRule(
                    keywords=["rib", "relevé identité bancaire", "bank account", "iban", "bic", "identité bancaire"],
                    patterns=[
                        r"iban\s*:?\s*FR\d{2}\s?[\dA-Z\s]{23,}",  # IBAN français complet
                        r"bic\s*:?\s*[A-Z]{4}FR[A-Z0-9]{2}[A-Z0-9]{3}?",  # BIC français
                        r"FR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{3}",  # IBAN formaté
                        r"domiciliation\s+bancaire"
                    ],
                    score_weight=3.0  # Poids élevé pour IBAN français
                ),
                ClassificationRule(
                    keywords=[
                        "crédit agricole", "bnp paribas", "société générale", "lcl", 
                        "caisse d'épargne", "banque postale", "cic", "crédit mutuel",
                        "banque populaire", "crédit lyonnais", "hsbc france", "boursorama"
                    ],
                    patterns=[
                        r"code\s+banque\s*:?\s*\d{5}",
                        r"code\s+guichet\s*:?\s*\d{5}",
                        r"compte\s+n[°\s]*:?\s*\d{11}",
                        r"clé\s+rib\s*:?\s*\d{2}",
                        r"titulaire\s*:?\s*[A-Z\s]+"
                    ],
                    score_weight=2.0
                ),
                ClassificationRule(
                    keywords=["banque", "établissement", "agence", "swift", "sort code"],
                    patterns=[
                        r"\d{5}\s+\d{5}\s+\d{11}\s+\d{2}",  # Format RIB classique
                        r"agence\s+n[°\s]*:?\s*\d+",
                        r"swift\s*:?\s*[A-Z]{8,11}"
                    ],
                    score_weight=1.8
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
                    keywords=[
                        "carte vitale", "cpam", "cram", "caisse primaire",
                        "sécurité sociale", "assurance maladie", "améli",
                        "numéro sécurité sociale", "nir"
                    ],
                    patterns=[
                        r"carte\s+vitale\s+n[°\s]*\d+",
                        r"remboursement\s+n[°\s]*\d+",
                        r"feuille\s+de\s+soins?",
                        r"cpam\s+[a-zé\s]+",
                        r"assurance\s+maladie\s+obligatoire",
                        r"\d\s?\d{2}\s?\d{2}\s?\d{2}\s?\d{3}\s?\d{3}\s?\d{2}"  # Numéro sécu
                    ],
                    score_weight=2.8
                ),
                ClassificationRule(
                    keywords=[
                        "mutuelle", "complémentaire santé", "harmonie", "mgen", 
                        "maaf", "macif", "april", "alan", "swisslife"
                    ],
                    patterns=[
                        r"mutuelle\s+n[°\s]*\d+",
                        r"garanties?\s+soins",
                        r"plafond\s+annuel",
                        r"taux\s+de\s+remboursement"
                    ],
                    score_weight=2.3
                ),
                ClassificationRule(
                    keywords=[
                        "pharmacie", "médicament", "ordonnance", "prescription",
                        "analyse", "laboratoire", "radiologie", "scanner",
                        "médecin", "docteur", "consultation", "spécialiste"
                    ],
                    patterns=[
                        r"prescription\s+médicale",
                        r"analyse\s+médicale\s+n[°\s]*\d+",
                        r"consultation\s+du\s+\d{1,2}[/\-]\d{1,2}",
                        r"honoraires?\s+médecin",
                        r"acte\s+médical"
                    ],
                    score_weight=2.0
                )
            ],
            
            DocumentCategory.EMPLOI: [
                ClassificationRule(
                    keywords=[
                        "fiche de paie", "bulletin de salaire", "bulletin de paie",
                        "salaire", "rémunération", "paie", "employeur"
                    ],
                    patterns=[
                        r"salaire\s+brut\s*:?\s*\d+[,\.]\d+",
                        r"net\s+à\s+payer\s*:?\s*\d+[,\.]\d+",
                        r"cotisations?\s+salariales?",
                        r"cotisations?\s+patronales?",
                        r"période\s+de\s+paie\s*:?\s*\d+[/\-]\d+",
                        r"heures?\s+travaillées?"
                    ],
                    score_weight=2.5,
                    exclusions=["contrat", "assurance", "police", "convention", "accord"]
                ),
                ClassificationRule(
                    keywords=[
                        "pôle emploi", "france travail", "assedic", "unédic",
                        "allocation chômage", "are", "ass", "rsa"
                    ],
                    patterns=[
                        r"allocation\s+d[\'']aide\s+au\s+retour\s+à\s+l[\'']emploi",
                        r"attestation\s+pôle\s+emploi",
                        r"demandeur\s+d[\'']emploi\s+n[°\s]*\d+",
                        r"indemnisation\s+chômage"
                    ],
                    score_weight=2.3
                ),
                ClassificationRule(
                    keywords=[
                        "contrat de travail", "cdi", "cdd", "stage", "apprentissage",
                        "démission", "licenciement", "rupture conventionnelle",
                        "préavis", "indemnités"
                    ],
                    patterns=[
                        r"contrat\s+à\s+durée\s+indéterminée",
                        r"contrat\s+à\s+durée\s+déterminée",
                        r"période\s+d[\'']essai",
                        r"convention\s+collective",
                        r"coefficient\s+hiérarchique"
                    ],
                    score_weight=2.0
                ),
                ClassificationRule(
                    keywords=[
                        "formation professionnelle", "cpf", "dif", "cif",
                        "organisme de formation", "certification", "diplôme"
                    ],
                    patterns=[
                        r"compte\s+personnel\s+de\s+formation",
                        r"heures?\s+de\s+formation",
                        r"attestation\s+de\s+formation"
                    ],
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
        Classification enrichie avec extraction d'entités et pré-classification Étape 3
        
        Args:
            filename: Nom du fichier
            ocr_text: Texte extrait par OCR
            entities: Entités extraites (optionnel, legacy)
            
        Returns:
            ClassificationResult avec catégorie et détails enrichis
        """
        start_time = time.time()
        processing_times = {}
        
        if not entities:
            entities = []
            
        filename_lower = filename.lower()
        text_lower = ocr_text.lower() if ocr_text else ""
        
        # ÉTAPE 1: Pré-classification par nom de fichier
        filename_start = time.time()
        filename_prediction = self.filename_classifier.classify_filename(filename)
        processing_times['filename_classification'] = time.time() - filename_start
        
        # ÉTAPE 2: Extraction d'entités françaises
        entity_start = time.time()
        extracted_entities = self.entity_extractor.extract_entities(text_lower, filename)
        processing_times['entity_extraction'] = time.time() - entity_start
        
        # ÉTAPE 3: Classification par règles enrichies avec entités
        rules_start = time.time()
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
            
            # BONUS: Scoring basé sur les entités extraites
            entity_bonus = self._calculate_entity_bonus(category, extracted_entities)
            total_score += entity_bonus
            
            if entity_bonus > 0:
                matched_rules.append(f"entity_bonus:{entity_bonus:.1f}")
            
            if total_score > 0:
                category_scores[category] = total_score
                category_matches[category] = matched_rules
        
        processing_times['rules_classification'] = time.time() - rules_start
        
        # ÉTAPE 4: Fusion intelligente filename + règles + entités
        fusion_start = time.time()
        
        # Si aucune règle ne correspond, utiliser la prédiction filename
        if not category_scores:
            if filename_prediction.confidence > 0.5:
                return ClassificationResult(
                    category=filename_prediction.predicted_category,
                    confidence=filename_prediction.confidence * 0.8,  # Réduction car pas de contenu
                    score=filename_prediction.confidence * 5,
                    reasoning=f"Classification par nom de fichier: {filename_prediction.reasoning}",
                    filename_prediction=filename_prediction,
                    extracted_entities=extracted_entities,
                    processing_times=processing_times
                )
            else:
                return ClassificationResult(
                    category=DocumentCategory.NON_CLASSES.value,
                    confidence=0.1,
                    score=0,
                    reasoning="Aucune règle et nom de fichier non reconnu",
                    filename_prediction=filename_prediction,
                    extracted_entities=extracted_entities,
                    processing_times=processing_times
                )
        
        # Trier par score décroissant
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        best_category, best_score = sorted_categories[0]
        
        # Calculer la confiance de base
        total_score = sum(category_scores.values())
        confidence = best_score / total_score if total_score > 0 else 0
        
        # BONUS: Accord avec prédiction filename
        if filename_prediction.predicted_category == best_category.value and filename_prediction.confidence > 0.6:
            confidence = min(0.95, confidence * 1.3)
            logger.info(f"Bonus accord filename/règles: {best_category.value}")
        
        # Bonus de confiance si écart significatif avec le 2ème
        if len(sorted_categories) > 1:
            second_score = sorted_categories[1][1]
            if best_score > second_score * 1.5:  # 50% d'écart minimum
                confidence = min(0.95, confidence * 1.2)
        
        # Calculer le boost total des entités
        entity_bonus = sum(self._calculate_entity_bonus(cat, extracted_entities) for cat, _ in sorted_categories)
        
        processing_times['fusion_decision'] = time.time() - fusion_start
        processing_times['total'] = time.time() - start_time
        
        # Générer le raisonnement enrichi
        reasoning = self._generate_enhanced_reasoning(
            best_category, 
            category_matches.get(best_category, []),
            filename_prediction,
            extracted_entities,
            entity_bonus
        )
        
        return ClassificationResult(
            category=best_category.value,
            confidence=confidence,
            score=best_score,
            matched_rules=category_matches.get(best_category, []),
            reasoning=reasoning,
            filename_prediction=filename_prediction,
            extracted_entities=extracted_entities,
            entity_boost=entity_bonus,
            processing_times=processing_times
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
    
    def _calculate_entity_bonus(self, category: DocumentCategory, entities: EntityExtractionResult) -> float:
        """Calcule le bonus de score basé sur les entités extraites pour une catégorie"""
        if not entities:
            return 0.0
        
        bonus = 0.0
        category_name = category.value
        
        # Mapping entités vers catégories avec poids spécialisés
        entity_category_mapping = {
            'rib': {
                'iban': 5.0,      # IBAN = très fort indicateur RIB
                'bic': 3.0,       # BIC = fort indicateur bancaire
                'entreprise': 1.0 # Banques détectées
            },
            'factures': {
                'montant': 2.0,   # Montants = indicateur facture
                'tva': 2.5,       # TVA = fort indicateur facture business
                'siret': 1.5,     # SIRET = indicateur entreprise/facture
                'entreprise': 2.0 # Fournisseurs détectés
            },
            'impots': {
                'siret': 3.0,     # SIRET = très important pour déclarations
                'tva': 3.5,       # TVA = très important pour fiscalité  
                'organisme': 4.0  # URSSAF/DGFIP = indicateur maximal
            },
            'attestations': {
                'organisme': 3.0, # CPAM/CAF/etc = fort indicateur
                'date': 1.5,      # Dates validité = modéré
                'siret': 1.0      # Parfois présent sur attestations
            },
            'sante': {
                'organisme': 3.5, # CPAM/mutuelle = très fort
                'montant': 1.5,   # Remboursements = modéré
                'date': 1.0       # Dates consultation = faible
            },
            'emploi': {
                'montant': 2.5,   # Salaires = fort indicateur
                'siret': 2.0,     # SIRET employeur = fort
                'organisme': 1.5  # Pôle Emploi = modéré
            },
            'contrats': {
                'siret': 2.0,     # Entreprises contractantes = fort
                'montant': 1.5,   # Montants contrats = modéré
                'date': 1.0       # Dates contrat = faible
            }
        }
        
        # Récupérer les poids pour cette catégorie
        category_weights = entity_category_mapping.get(category_name, {})
        
        # Calculer le bonus pour chaque type d'entité
        for entity_type, weight in category_weights.items():
            entity_count = 0
            avg_confidence = 0.0
            
            if entity_type == 'iban':
                entity_count = len(entities.ibans)
                avg_confidence = sum(e.confidence for e in entities.ibans) / max(1, entity_count)
            elif entity_type == 'siret':
                entity_count = len(entities.sirets)
                avg_confidence = sum(e.confidence for e in entities.sirets) / max(1, entity_count)
            elif entity_type == 'tva':
                entity_count = len(entities.tva_numbers)
                avg_confidence = sum(e.confidence for e in entities.tva_numbers) / max(1, entity_count)
            elif entity_type == 'montant':
                entity_count = len(entities.montants)
                avg_confidence = sum(e.confidence for e in entities.montants) / max(1, entity_count)
            elif entity_type == 'date':
                entity_count = len(entities.dates)
                avg_confidence = sum(e.confidence for e in entities.dates) / max(1, entity_count)
            elif entity_type == 'organisme':
                entity_count = len(entities.organismes)
                avg_confidence = sum(e.confidence for e in entities.organismes) / max(1, entity_count)
            elif entity_type == 'entreprise':
                entity_count = len(entities.entreprises)
                avg_confidence = sum(e.confidence for e in entities.entreprises) / max(1, entity_count)
            
            # Calculer le bonus : nombre * confiance * poids * facteur de saturation
            if entity_count > 0:
                saturation_factor = min(1.0, entity_count / 3)  # Plafond à 3 entités
                entity_bonus = entity_count * avg_confidence * weight * saturation_factor
                bonus += entity_bonus
        
        return min(bonus, 15.0)  # Plafonner le bonus total à 15 points
    
    def _generate_enhanced_reasoning(self, 
                                   category: DocumentCategory, 
                                   matches: List[str],
                                   filename_prediction: FilenameClassification,
                                   entities: EntityExtractionResult,
                                   entity_bonus: float) -> str:
        """Génère un raisonnement enrichi avec entités et filename"""
        reasoning_parts = []
        
        # Raisonnement de base
        if not matches:
            reasoning_parts.append(f"Classé comme {category.value} par défaut")
        else:
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
            reasoning_parts.append(f"{base_reason} ({len(matches)} règles)")
        
        # Accord filename
        if filename_prediction.predicted_category == category.value:
            reasoning_parts.append(f"Confirmé par nom fichier (conf: {filename_prediction.confidence:.2f})")
        elif filename_prediction.confidence > 0.6:
            reasoning_parts.append(f"Nom fichier suggérait: {filename_prediction.predicted_category}")
        
        # Entités trouvées
        entity_summary = []
        if entities.sirets:
            entity_summary.append(f"{len(entities.sirets)} SIRET")
        if entities.tva_numbers:
            entity_summary.append(f"{len(entities.tva_numbers)} TVA")
        if entities.ibans:
            entity_summary.append(f"{len(entities.ibans)} IBAN")
        if entities.montants:
            entity_summary.append(f"{len(entities.montants)} montants")
        if entities.organismes:
            entity_summary.append(f"{len(entities.organismes)} organismes")
        
        if entity_summary:
            reasoning_parts.append(f"Entités: {', '.join(entity_summary)}")
        
        if entity_bonus > 1.0:
            reasoning_parts.append(f"Bonus entités: +{entity_bonus:.1f}")
        
        return " | ".join(reasoning_parts)
    
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
    
    def get_classification_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques enrichies sur le système de classification"""
        stats = {}
        
        # Statistiques règles de base
        for category, rules in self.classification_rules.items():
            stats[category.value] = {
                "rules_count": len(rules),
                "total_keywords": sum(len(rule.keywords) for rule in rules),
                "total_patterns": sum(len(rule.patterns) for rule in rules)
            }
        
        # Statistiques services Étape 3
        stats['entity_extractor'] = self.entity_extractor.get_statistics()
        stats['filename_classifier'] = self.filename_classifier.get_statistics()
        
        # Configuration scoring entités
        stats['entity_scoring_weights'] = self.entity_scoring_weights
        
        return stats


# Instance globale pour éviter la re-initialisation
_classifier_instance = None

def get_document_classifier() -> DocumentClassifier:
    """Retourne l'instance singleton du classificateur"""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = DocumentClassifier()
    return _classifier_instance