"""
Pré-classificateur basé sur le nom de fichier - Étape 3
Classification rapide avant analyse du contenu pour optimiser les performances
"""

import re
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import json
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class FilenameClassification:
    """Résultat de pré-classification par nom de fichier"""
    predicted_category: str
    confidence: float
    matched_patterns: List[str]
    reasoning: str
    processing_time: float = 0.0


class FilenameClassifier:
    """
    Pré-classificateur intelligent basé sur le nom de fichier
    Objectif: >70% précision sur nom de fichier seul pour optimiser le pipeline
    """
    
    def __init__(self):
        self.logger = logging.getLogger("filename_classifier")
        
        # Patterns spécialisés par catégorie avec poids
        self.filename_patterns = {
            'factures': {
                'keywords': [
                    'facture', 'fact', 'invoice', 'bill', 'devis', 'quote',
                    'commande', 'order', 'note_frais', 'frais', 'ticket',
                    'recu', 'receipt', 'paiement', 'payment'
                ],
                'prefixes': ['fact_', 'inv_', 'bill_', 'fac_', 'f_'],
                'suffixes': ['_facture', '_fact', '_invoice', '_bill'],
                'patterns': [
                    r'\bfact(?:ure)?[-_]?\d+',
                    r'\binv(?:oice)?[-_]?\d+',
                    r'\bbill[-_]?\d+',
                    r'\bdevis[-_]?\d+',
                    r'\brecu[-_]?\d+'
                ],
                'fournisseurs': [
                    'edf', 'engie', 'total', 'orange', 'sfr', 'bouygues', 'free',
                    'veolia', 'suez', 'amazon', 'cdiscount', 'darty', 'fnac'
                ],
                'weight': 1.0
            },
            
            'rib': {
                'keywords': [
                    'rib', 'releve', 'identite', 'bancaire', 'bank', 'iban',
                    'compte', 'account', 'coordonnees', 'banking'
                ],
                'prefixes': ['rib_', 'releve_', 'bank_', 'iban_'],
                'suffixes': ['_rib', '_bank', '_bancaire', '_iban'],
                'patterns': [
                    r'\brib[-_]?\w*',
                    r'\breleve[-_]?bancaire',
                    r'\biban[-_]?\w*',
                    r'\bbank[-_]?account'
                ],
                'banques': [
                    'credit_agricole', 'bnp', 'societe_generale', 'lcl',
                    'caisse_epargne', 'banque_postale', 'cic', 'credit_mutuel',
                    'boursorama', 'ing', 'fortuneo'
                ],
                'weight': 1.2  # Poids élevé car patterns très distinctifs
            },
            
            'contrats': {
                'keywords': [
                    'contrat', 'contract', 'accord', 'convention', 'engagement',
                    'police', 'assurance', 'insurance', 'mutuelle', 'garantie'
                ],
                'prefixes': ['contrat_', 'contract_', 'police_', 'assur_'],
                'suffixes': ['_contrat', '_contract', '_assurance', '_police'],
                'patterns': [
                    r'\bcontrat[-_]?\w*',
                    r'\bpolice[-_]?\d+',
                    r'\bassur(?:ance)?[-_]?\w*',
                    r'\bcontract[-_]?\w*'
                ],
                'assureurs': [
                    'maif', 'macif', 'axa', 'allianz', 'generali', 'groupama',
                    'matmut', 'mma', 'april', 'harmonie'
                ],
                'weight': 1.0
            },
            
            'attestations': {
                'keywords': [
                    'attestation', 'certificate', 'carte', 'card', 'permis',
                    'certifie', 'justificatif', 'proof', 'document_officiel'
                ],
                'prefixes': ['att_', 'cert_', 'carte_', 'justif_'],
                'suffixes': ['_attestation', '_certificate', '_carte', '_card'],
                'patterns': [
                    r'\battestation[-_]?\w*',
                    r'\bcarte[-_]?\w*',
                    r'\bcertificate[-_]?\w*',
                    r'\bpermis[-_]?\w*'
                ],
                'organismes': [
                    'urssaf', 'cpam', 'caf', 'pole_emploi', 'prefecture',
                    'mairie', 'remi', 'transport', 'senior'
                ],
                'weight': 1.1
            },
            
            'impots': {
                'keywords': [
                    'impot', 'impots', 'fiscal', 'tax', 'urssaf', 'dgfip',
                    'declaration', 'cotisation', 'charges_sociales', 'tva'
                ],
                'prefixes': ['impot_', 'tax_', 'urssaf_', 'decl_', 'cotis_'],
                'suffixes': ['_impot', '_tax', '_fiscal', '_urssaf', '_tva'],
                'patterns': [
                    r'\bimpot[-_]?\w*',
                    r'\burssaf[-_]?\w*',
                    r'\btva[-_]?\w*',
                    r'\bdeclaration[-_]?\w*',
                    r'\bcotisation[-_]?\w*'
                ],
                'organismes': [
                    'urssaf', 'dgfip', 'tresor_public', 'impots', 'fiscal'
                ],
                'weight': 1.3  # Poids très élevé car mots-clés très spécifiques
            },
            
            'sante': {
                'keywords': [
                    'sante', 'medical', 'cpam', 'secu', 'mutuelle', 'remboursement',
                    'consultation', 'pharmacie', 'ordonnance', 'analyse'
                ],
                'prefixes': ['med_', 'sante_', 'cpam_', 'secu_', 'mut_'],
                'suffixes': ['_medical', '_sante', '_cpam', '_mutuelle'],
                'patterns': [
                    r'\bcpam[-_]?\w*',
                    r'\bsecu[-_]?\w*',
                    r'\bmedical[-_]?\w*',
                    r'\bmutuelle[-_]?\w*',
                    r'\bremboursement[-_]?\w*'
                ],
                'organismes': [
                    'cpam', 'secu', 'ameli', 'mutuelle', 'harmonie', 'mgen'
                ],
                'weight': 1.2
            },
            
            'emploi': {
                'keywords': [
                    'paie', 'salaire', 'emploi', 'travail', 'bulletin', 'fiche',
                    'payroll', 'salary', 'employment', 'pole_emploi'
                ],
                'prefixes': ['paie_', 'sal_', 'bull_', 'emp_', 'work_'],
                'suffixes': ['_paie', '_salaire', '_emploi', '_bulletin'],
                'patterns': [
                    r'\bpaie[-_]?\w*',
                    r'\bbulletin[-_]?\w*',
                    r'\bsalaire[-_]?\w*',
                    r'\bpole[-_]?emploi'
                ],
                'organismes': [
                    'pole_emploi', 'assedic', 'unedic', 'entreprise'
                ],
                'weight': 1.1
            },
            
            'courriers': {
                'keywords': [
                    'courrier', 'letter', 'correspondance', 'mail', 'lettre',
                    'rapport', 'report', 'document', 'note', 'memo'
                ],
                'prefixes': ['courrier_', 'letter_', 'mail_', 'rapport_'],
                'suffixes': ['_courrier', '_letter', '_rapport', '_note'],
                'patterns': [
                    r'\bcourrier[-_]?\w*',
                    r'\brapport[-_]?\w*',
                    r'\bletter[-_]?\w*',
                    r'\bmemo[-_]?\w*'
                ],
                'weight': 0.8  # Poids plus faible car plus générique
            }
        }
        
        # Patterns d'exclusion pour éviter les faux positifs
        self.exclusion_patterns = {
            'system_files': [r'\.tmp$', r'\.temp$', r'\.log$', r'\.bak$'],
            'generic_numbers': [r'^tmp\w+$', r'^\d+$'],
            'empty_or_short': [r'^.{1,3}$']
        }
        
        # Cache des classifications pour performance
        self._classification_cache = {}
        
        # Statistiques pour monitoring
        self.stats = {
            'total_classifications': 0,
            'cache_hits': 0,
            'category_counts': {cat: 0 for cat in self.filename_patterns.keys()},
            'confidence_distribution': {'high': 0, 'medium': 0, 'low': 0}
        }
    
    def classify_filename(self, filename: str) -> FilenameClassification:
        """
        Classifie un document basé uniquement sur son nom de fichier
        
        Args:
            filename: Nom du fichier (avec ou sans extension)
            
        Returns:
            FilenameClassification avec prédiction et confiance
        """
        start_time = datetime.now()
        
        # Vérifier le cache
        if filename in self._classification_cache:
            self.stats['cache_hits'] += 1
            result = self._classification_cache[filename]
            result.processing_time = (datetime.now() - start_time).total_seconds()
            return result
        
        self.stats['total_classifications'] += 1
        
        # Normaliser le nom de fichier
        normalized_filename = self._normalize_filename(filename)
        
        # Vérifier les exclusions
        if self._is_excluded(normalized_filename):
            result = FilenameClassification(
                predicted_category='non_classes',
                confidence=0.9,
                matched_patterns=['exclusion_pattern'],
                reasoning="Fichier système ou pattern générique détecté",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
            return result
        
        # Scorer chaque catégorie
        category_scores = {}
        category_matches = {}
        
        for category, config in self.filename_patterns.items():
            score, matches = self._score_category(normalized_filename, category, config)
            if score > 0:
                category_scores[category] = score
                category_matches[category] = matches
        
        # Déterminer la meilleure catégorie
        if not category_scores:
            result = FilenameClassification(
                predicted_category='non_classes',
                confidence=0.3,
                matched_patterns=[],
                reasoning="Aucun pattern reconnu dans le nom de fichier",
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        else:
            # Trier par score
            sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
            best_category, best_score = sorted_categories[0]
            
            # Calculer la confiance (0.3 à 0.9)
            confidence = min(0.9, 0.3 + (best_score / 10))
            
            # Bonus si écart significatif avec 2ème catégorie
            if len(sorted_categories) > 1:
                second_score = sorted_categories[1][1]
                if best_score > second_score * 1.5:
                    confidence = min(0.9, confidence * 1.2)
            
            # Générer le raisonnement
            matches = category_matches.get(best_category, [])
            reasoning = self._generate_reasoning(best_category, matches, best_score)
            
            result = FilenameClassification(
                predicted_category=best_category,
                confidence=confidence,
                matched_patterns=matches,
                reasoning=reasoning,
                processing_time=(datetime.now() - start_time).total_seconds()
            )
        
        # Mettre à jour les statistiques
        self._update_stats(result)
        
        # Sauvegarder en cache
        self._classification_cache[filename] = result
        
        self.logger.debug(f"Classification filename '{filename}': {result.predicted_category} (conf: {result.confidence:.2f})")
        
        return result
    
    def _normalize_filename(self, filename: str) -> str:
        """Normalise le nom de fichier pour l'analyse"""
        # Retirer l'extension
        name = Path(filename).stem
        
        # Convertir en minuscules
        name = name.lower()
        
        # Remplacer les caractères spéciaux par des underscores
        name = re.sub(r'[^\w\-]', '_', name)
        
        # Nettoyer les underscores multiples
        name = re.sub(r'_+', '_', name)
        
        # Retirer les underscores en début/fin
        name = name.strip('_')
        
        return name
    
    def _is_excluded(self, filename: str) -> bool:
        """Vérifie si le fichier doit être exclu de la classification"""
        for pattern_list in self.exclusion_patterns.values():
            for pattern in pattern_list:
                if re.search(pattern, filename, re.IGNORECASE):
                    return True
        return False
    
    def _score_category(self, filename: str, category: str, config: Dict) -> Tuple[float, List[str]]:
        """Calcule le score d'une catégorie pour un nom de fichier"""
        total_score = 0.0
        matched_patterns = []
        weight = config.get('weight', 1.0)
        
        # Score des mots-clés génériques
        for keyword in config.get('keywords', []):
            if keyword in filename:
                score = 2.0 * weight
                total_score += score
                matched_patterns.append(f"keyword:{keyword}")
        
        # Score des préfixes
        for prefix in config.get('prefixes', []):
            if filename.startswith(prefix):
                score = 3.0 * weight  # Bonus pour préfixes
                total_score += score
                matched_patterns.append(f"prefix:{prefix}")
        
        # Score des suffixes
        for suffix in config.get('suffixes', []):
            if filename.endswith(suffix):
                score = 3.0 * weight  # Bonus pour suffixes
                total_score += score
                matched_patterns.append(f"suffix:{suffix}")
        
        # Score des patterns regex
        for pattern in config.get('patterns', []):
            try:
                if re.search(pattern, filename, re.IGNORECASE):
                    score = 4.0 * weight  # Score le plus élevé pour patterns spécialisés
                    total_score += score
                    matched_patterns.append(f"pattern:{pattern}")
            except re.error:
                self.logger.warning(f"Pattern regex invalide: {pattern}")
        
        # Score des entités spécialisées (fournisseurs, banques, etc.)
        for entity_type in ['fournisseurs', 'banques', 'assureurs', 'organismes']:
            for entity in config.get(entity_type, []):
                if entity in filename:
                    score = 5.0 * weight  # Score maximum pour entités spécialisées
                    total_score += score
                    matched_patterns.append(f"{entity_type}:{entity}")
        
        return total_score, matched_patterns
    
    def _generate_reasoning(self, category: str, matches: List[str], score: float) -> str:
        """Génère une explication du raisonnement"""
        if not matches:
            return f"Classé comme {category} par défaut"
        
        match_types = {}
        for match in matches:
            match_type = match.split(':')[0]
            if match_type not in match_types:
                match_types[match_type] = 0
            match_types[match_type] += 1
        
        reasoning_parts = []
        for match_type, count in match_types.items():
            if match_type == 'keyword':
                reasoning_parts.append(f"{count} mot(s)-clé(s)")
            elif match_type == 'pattern':
                reasoning_parts.append(f"{count} pattern(s) spécialisé(s)")
            elif match_type in ['prefix', 'suffix']:
                reasoning_parts.append(f"{count} {match_type}(s)")
            else:
                reasoning_parts.append(f"{count} {match_type}")
        
        reasoning = f"Détecté: {', '.join(reasoning_parts)} (score: {score:.1f})"
        return reasoning
    
    def _update_stats(self, result: FilenameClassification):
        """Met à jour les statistiques"""
        # Compter par catégorie
        if result.predicted_category in self.stats['category_counts']:
            self.stats['category_counts'][result.predicted_category] += 1
        
        # Distribution de confiance
        if result.confidence >= 0.7:
            self.stats['confidence_distribution']['high'] += 1
        elif result.confidence >= 0.5:
            self.stats['confidence_distribution']['medium'] += 1
        else:
            self.stats['confidence_distribution']['low'] += 1
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne les statistiques du classificateur"""
        total = self.stats['total_classifications']
        if total == 0:
            return self.stats
        
        stats_with_rates = self.stats.copy()
        stats_with_rates['cache_hit_rate'] = self.stats['cache_hits'] / total * 100
        
        # Ajouter les pourcentages pour la distribution de confiance
        for level in self.stats['confidence_distribution']:
            count = self.stats['confidence_distribution'][level]
            stats_with_rates['confidence_distribution'][f'{level}_pct'] = count / total * 100
        
        return stats_with_rates
    
    def clear_cache(self):
        """Vide le cache de classification"""
        self._classification_cache.clear()
        self.logger.info("Cache de classification vidé")
    
    def add_custom_pattern(self, category: str, pattern_type: str, pattern: str, weight: float = 1.0):
        """
        Ajoute un pattern personnalisé à une catégorie
        
        Args:
            category: Catégorie cible
            pattern_type: Type de pattern ('keywords', 'patterns', etc.)
            pattern: Le pattern à ajouter
            weight: Poids du pattern (défaut: 1.0)
        """
        if category not in self.filename_patterns:
            self.logger.warning(f"Catégorie inconnue: {category}")
            return
        
        if pattern_type not in self.filename_patterns[category]:
            self.filename_patterns[category][pattern_type] = []
        
        if pattern not in self.filename_patterns[category][pattern_type]:
            self.filename_patterns[category][pattern_type].append(pattern)
            self.logger.info(f"Pattern ajouté: {category}.{pattern_type} = {pattern}")
        
        # Mettre à jour le poids si spécifié
        if weight != 1.0:
            self.filename_patterns[category]['weight'] = weight
    
    def test_filename_batch(self, filenames: List[str]) -> List[FilenameClassification]:
        """Teste une liste de noms de fichiers"""
        results = []
        for filename in filenames:
            result = self.classify_filename(filename)
            results.append(result)
        return results
    
    def export_patterns(self, file_path: str):
        """Exporte la configuration des patterns vers un fichier JSON"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.filename_patterns, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Patterns exportés vers {file_path}")
        except Exception as e:
            self.logger.error(f"Erreur export patterns: {e}")
    
    def import_patterns(self, file_path: str):
        """Importe une configuration de patterns depuis un fichier JSON"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_patterns = json.load(f)
            
            # Fusionner avec les patterns existants
            for category, config in imported_patterns.items():
                if category not in self.filename_patterns:
                    self.filename_patterns[category] = config
                else:
                    # Fusionner les listes
                    for key, value in config.items():
                        if isinstance(value, list):
                            if key not in self.filename_patterns[category]:
                                self.filename_patterns[category][key] = []
                            self.filename_patterns[category][key].extend(value)
                        else:
                            self.filename_patterns[category][key] = value
            
            self.logger.info(f"Patterns importés depuis {file_path}")
            
        except Exception as e:
            self.logger.error(f"Erreur import patterns: {e}")


# Instance globale pour éviter la re-initialisation
_filename_classifier_instance = None

def get_filename_classifier() -> FilenameClassifier:
    """Retourne l'instance singleton du classificateur de noms de fichiers"""
    global _filename_classifier_instance
    if _filename_classifier_instance is None:
        _filename_classifier_instance = FilenameClassifier()
    return _filename_classifier_instance