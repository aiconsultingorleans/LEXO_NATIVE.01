"""
Module d'extraction d'entités spécifiques et d'éléments structurés
Extraction avancée de dates, montants, adresses, numéros, etc.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import json

logger = logging.getLogger(__name__)

# Import conditionnel de spaCy
try:
    import spacy
    from spacy import displacy
    SPACY_AVAILABLE = True
    logger.info("spaCy disponible - extraction d'entités avancée activée")
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy n'est pas disponible - utilisation des regex seulement")


@dataclass
class ExtractedEntity:
    """Entité extraite avec métadonnées"""
    entity_type: str
    value: str
    confidence: float
    start_position: int
    end_position: int
    normalized_value: Optional[Any] = None
    context: Optional[str] = None
    pattern_used: Optional[str] = None


@dataclass 
class EntityExtractionResult:
    """Résultat d'extraction d'entités"""
    text: str
    entities: List[ExtractedEntity]
    entity_counts: Dict[str, int]
    processing_time: float
    extraction_method: str


class EntityExtractor:
    """
    Extracteur d'entités spécialisé pour documents d'affaires
    """
    
    def __init__(self, language: str = "fr_core_news_sm"):
        """
        Initialise l'extracteur d'entités
        
        Args:
            language: Modèle spaCy à utiliser (fr_core_news_sm pour le français)
        """
        self.language = language
        self.nlp = None
        
        # Patterns regex pour différents types d'entités
        self.patterns = {
            'dates': [
                # Formats français
                r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b',  # 23/07/2025, 23-07-2025
                r'\b\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b',
                r'\b(?:lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+\d{1,2}\s+(?:janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+\d{4}\b',
                # Formats anglais
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}\b',  # 07/23/2025
                # ISO format
                r'\b\d{4}-\d{2}-\d{2}\b',  # 2025-07-23
            ],
            'amounts': [
                # Formats français avec €
                r'\b\d{1,3}(?:\s?\d{3})*[,.]?\d{0,2}\s*€\b',  # 1 234,56 €
                r'\b\d{1,3}(?:[.,]\d{3})*[,.]?\d{0,2}\s*euros?\b',  # 1.234,56 euros
                # Formats avec devise en préfixe
                r'\b€\s*\d{1,3}(?:\s?\d{3})*[,.]?\d{0,2}\b',  # € 1 234,56
                # Formats USD/GBP
                r'\b\$\s*\d{1,3}(?:,\d{3})*\.?\d{0,2}\b',  # $1,234.56
                r'\b£\s*\d{1,3}(?:,\d{3})*\.?\d{0,2}\b',   # £1,234.56
                # Montants avec mots
                r'\b(?:total|montant|prix|coût|facture|facture)\s*:?\s*\d{1,3}(?:[.,\s]\d{3})*[,.]?\d{0,2}\s*[€$£]?\b',
            ],
            'phones': [
                # Formats français
                r'\b0[1-9](?:[.\s-]?\d{2}){4}\b',  # 01 23 45 67 89
                r'\b\+33\s?[1-9](?:[.\s-]?\d{2}){4}\b',  # +33 1 23 45 67 89
                # Formats internationaux
                r'\b\+\d{1,3}[\s.-]?\d{1,4}[\s.-]?\d{1,4}[\s.-]?\d{1,9}\b',
            ],
            'emails': [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            ],
            'addresses': [
                # Adresses françaises
                r'\b\d{1,4}\s+(?:rue|avenue|boulevard|place|allée|impasse|chemin|route)\s+[A-Za-z\s\'-]+\b',
                r'\b\d{5}\s+[A-Za-z\s\'-]+(?:France)?\b',  # Code postal + ville
            ],
            'companies': [
                # Formes juridiques françaises
                r'\b[A-Z][A-Za-z\s&\'-]+(?:SARL|SAS|SA|EURL|SCI|SASU|SNC|SCS)\b',
                r'\b[A-Z][A-Za-z\s&\'-]+(?:Ltd|Inc|Corp|LLC|GmbH)\b',
            ],
            'siret': [
                r'\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b',  # SIRET: 123 456 789 12345
            ],
            'iban': [
                r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{0,4}\b',  # IBAN
            ],
            'invoice_numbers': [
                r'\b(?:facture|invoice|bill)\s*n?°?\s*:?\s*([A-Z0-9-]{3,20})\b',
                r'\b[A-Z]{1,3}[-/]?\d{3,10}(?:[-/]\d{2,4})?\b',  # F-2025-001
            ],
            'percentages': [
                r'\b\d{1,3}[.,]?\d{0,2}\s*%\b',  # 20.5%
            ],
            'urls': [
                r'https?://[^\s<>"{}|\\^`\[\]]+',
                r'www\.[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?:/[^\s<>"{}|\\^`\[\]]*)?',
            ]
        }
        
        # Mois en français pour la normalisation des dates
        self.french_months = {
            'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
            'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
            'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
        }
        
        # Initialiser spaCy si disponible
        self._initialize_nlp()
    
    def _initialize_nlp(self):
        """Initialise le modèle spaCy si disponible"""
        try:
            import spacy
            import os
            
            # Configuration du répertoire spaCy depuis les variables d'environnement
            spacy_data_dir = os.getenv('SPACY_DATA')
            if spacy_data_dir:
                # Ajouter le répertoire au path de spaCy
                import spacy.util
                spacy.util.set_data_path(spacy_data_dir)
                logger.info(f"Répertoire spaCy configuré: {spacy_data_dir}")
            
            self.nlp = spacy.load(self.language)
            logger.info(f"Modèle spaCy chargé: {self.language}")
        except (ImportError, OSError) as e:
            logger.warning(f"spaCy non disponible ou modèle non trouvé: {e}")
            logger.info("Utilisation des regex uniquement")
            self.nlp = None
    
    def extract_entities(self, text: str, entity_types: Optional[List[str]] = None) -> EntityExtractionResult:
        """
        Extrait les entités du texte
        
        Args:
            text: Texte à analyser
            entity_types: Types d'entités à extraire (None = tous)
            
        Returns:
            Résultat de l'extraction avec toutes les entités trouvées
        """
        import time
        start_time = time.time()
        
        if entity_types is None:
            entity_types = list(self.patterns.keys())
        
        logger.info(f"Extraction d'entités sur {len(text)} caractères")
        
        all_entities = []
        
        # Extraction par patterns regex
        for entity_type in entity_types:
            if entity_type in self.patterns:
                entities = self._extract_with_regex(text, entity_type)
                all_entities.extend(entities)
        
        # Extraction avec spaCy si disponible
        if self.nlp:
            spacy_entities = self._extract_with_spacy(text, entity_types)
            all_entities.extend(spacy_entities)
        
        # Tri par position dans le texte
        all_entities.sort(key=lambda x: x.start_position)
        
        # Suppression des doublons
        unique_entities = self._remove_overlapping_entities(all_entities)
        
        # Comptage par type
        entity_counts = {}
        for entity in unique_entities:
            entity_counts[entity.entity_type] = entity_counts.get(entity.entity_type, 0) + 1
        
        processing_time = time.time() - start_time
        
        logger.info(f"Extraction terminée: {len(unique_entities)} entités en {processing_time:.2f}s")
        
        return EntityExtractionResult(
            text=text,
            entities=unique_entities,
            entity_counts=entity_counts,
            processing_time=processing_time,
            extraction_method="hybrid" if self.nlp else "regex"
        )
    
    def _extract_with_regex(self, text: str, entity_type: str) -> List[ExtractedEntity]:
        """Extrait les entités avec les patterns regex"""
        entities = []
        patterns = self.patterns.get(entity_type, [])
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                value = match.group().strip()
                start, end = match.span()
                
                # Normaliser la valeur selon le type
                normalized_value = self._normalize_value(value, entity_type)
                
                # Calculer un score de confiance
                confidence = self._calculate_confidence(value, entity_type, pattern)
                
                # Extraire le contexte
                context = self._extract_context(text, start, end)
                
                entity = ExtractedEntity(
                    entity_type=entity_type,
                    value=value,
                    confidence=confidence,
                    start_position=start,
                    end_position=end,
                    normalized_value=normalized_value,
                    context=context,
                    pattern_used=pattern
                )
                
                entities.append(entity)
        
        return entities
    
    def _extract_with_spacy(self, text: str, entity_types: List[str]) -> List[ExtractedEntity]:
        """Extrait les entités avec spaCy"""
        if not self.nlp:
            return []
        
        entities = []
        doc = self.nlp(text)
        
        # Mapping des labels spaCy vers nos types
        spacy_mapping = {
            'PERSON': 'persons',
            'ORG': 'companies',
            'GPE': 'locations',
            'LOC': 'locations', 
            'DATE': 'dates',
            'TIME': 'dates',
            'MONEY': 'amounts',
            'PERCENT': 'percentages'
        }
        
        for ent in doc.ents:
            entity_type = spacy_mapping.get(ent.label_, 'other')
            
            if entity_type in entity_types or 'other' in entity_types:
                # Normaliser la valeur
                normalized_value = self._normalize_value(ent.text, entity_type)
                
                entity = ExtractedEntity(
                    entity_type=entity_type,
                    value=ent.text,
                    confidence=0.8,  # spaCy est généralement fiable
                    start_position=ent.start_char,
                    end_position=ent.end_char,
                    normalized_value=normalized_value,
                    context=self._extract_context(text, ent.start_char, ent.end_char),
                    pattern_used="spacy_" + ent.label_
                )
                
                entities.append(entity)
        
        return entities
    
    def _normalize_value(self, value: str, entity_type: str) -> Any:
        """Normalise une valeur selon son type"""
        try:
            if entity_type == 'dates':
                return self._normalize_date(value)
            elif entity_type == 'amounts':
                return self._normalize_amount(value)
            elif entity_type == 'phones':
                return self._normalize_phone(value)
            elif entity_type == 'emails':
                return value.lower().strip()
            elif entity_type == 'percentages':
                return self._normalize_percentage(value)
            elif entity_type in ['siret', 'iban']:
                return re.sub(r'\s', '', value.upper())
            else:
                return value.strip()
        except Exception as e:
            logger.debug(f"Erreur normalisation {entity_type}: {e}")
            return value
    
    def _normalize_date(self, date_str: str) -> Optional[date]:
        """Normalise une date vers un objet date Python"""
        date_str = date_str.strip()
        
        # Formats à essayer
        formats = [
            '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y',
            '%d/%m/%y', '%d-%m-%y', '%d.%m.%y',
            '%Y-%m-%d',
            '%m/%d/%Y', '%m-%d-%Y',
            '%d %B %Y', '%d %b %Y'
        ]
        
        # Remplacer les mois français
        for french_month, month_num in self.french_months.items():
            date_str = re.sub(
                r'\b' + french_month + r'\b', 
                str(month_num), 
                date_str, 
                flags=re.IGNORECASE
            )
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None
    
    def _normalize_amount(self, amount_str: str) -> Optional[Decimal]:
        """Normalise un montant vers un Decimal"""
        # Nettoyer la chaîne
        amount_str = re.sub(r'[€$£\s]', '', amount_str)
        amount_str = re.sub(r'euros?', '', amount_str, flags=re.IGNORECASE)
        
        # Gérer les formats français (virgule décimale)
        if ',' in amount_str and '.' in amount_str:
            # Format 1.234,56
            amount_str = amount_str.replace('.', '').replace(',', '.')
        elif ',' in amount_str and amount_str.count(',') == 1:
            # Format 1234,56
            parts = amount_str.split(',')
            if len(parts[1]) <= 2:  # Partie décimale
                amount_str = amount_str.replace(',', '.')
        
        # Supprimer les espaces restants
        amount_str = amount_str.replace(' ', '')
        
        try:
            return Decimal(amount_str)
        except (InvalidOperation, ValueError):
            return None
    
    def _normalize_phone(self, phone_str: str) -> str:
        """Normalise un numéro de téléphone"""
        # Supprimer tous les séparateurs
        phone = re.sub(r'[\s.\-]', '', phone_str)
        
        # Format français: convertir vers format international
        if phone.startswith('0') and len(phone) == 10:
            phone = '+33' + phone[1:]
        
        return phone
    
    def _normalize_percentage(self, percent_str: str) -> Optional[float]:
        """Normalise un pourcentage"""
        # Extraire le nombre
        number_str = re.sub(r'[%\s]', '', percent_str).replace(',', '.')
        
        try:
            return float(number_str)
        except ValueError:
            return None
    
    def _calculate_confidence(self, value: str, entity_type: str, pattern: str) -> float:
        """Calcule un score de confiance pour une entité"""
        base_confidence = 0.7
        
        # Ajustements selon le type et la qualité de la correspondance
        if entity_type == 'emails':
            # Vérifier la structure basique d'un email
            if '@' in value and '.' in value.split('@')[1]:
                base_confidence = 0.9
        
        elif entity_type == 'amounts':
            # Les montants avec devise sont plus fiables
            if any(symbol in value for symbol in ['€', '$', '£']):
                base_confidence = 0.85
        
        elif entity_type == 'dates':
            # Les dates avec séparateurs clairs sont plus fiables
            if any(sep in value for sep in ['/', '-', '.']):
                base_confidence = 0.8
        
        elif entity_type == 'phones':
            # Les numéros avec indicatif sont plus fiables
            if value.startswith('+') or value.startswith('0'):
                base_confidence = 0.85
        
        # Pénalité pour les valeurs très courtes ou très longues
        if len(value) < 3:
            base_confidence *= 0.7
        elif len(value) > 50:
            base_confidence *= 0.8
        
        return min(1.0, base_confidence)
    
    def _extract_context(self, text: str, start: int, end: int, context_size: int = 50) -> str:
        """Extrait le contexte autour d'une entité"""
        context_start = max(0, start - context_size)
        context_end = min(len(text), end + context_size)
        
        context = text[context_start:context_end]
        
        # Marquer la position de l'entité
        entity_start = start - context_start
        entity_end = end - context_start
        
        return (context[:entity_start] + 
                "[" + context[entity_start:entity_end] + "]" + 
                context[entity_end:])
    
    def _remove_overlapping_entities(self, entities: List[ExtractedEntity]) -> List[ExtractedEntity]:
        """Supprime les entités qui se chevauchent, garde la plus fiable"""
        if not entities:
            return []
        
        # Trier par position puis par confiance (décroissante)
        entities.sort(key=lambda x: (x.start_position, -x.confidence))
        
        unique_entities = [entities[0]]
        
        for entity in entities[1:]:
            # Vérifier le chevauchement avec la dernière entité ajoutée
            last_entity = unique_entities[-1]
            
            # Si pas de chevauchement, ajouter
            if entity.start_position >= last_entity.end_position:
                unique_entities.append(entity)
            # Si chevauchement et meilleure confiance, remplacer
            elif entity.confidence > last_entity.confidence:
                unique_entities[-1] = entity
        
        return unique_entities
    
    def get_entities_by_type(self, result: EntityExtractionResult, entity_type: str) -> List[ExtractedEntity]:
        """Filtre les entités par type"""
        return [entity for entity in result.entities if entity.entity_type == entity_type]
    
    def get_structured_summary(self, result: EntityExtractionResult) -> Dict[str, Any]:
        """Crée un résumé structuré des entités extraites"""
        summary = {
            'extraction_info': {
                'total_entities': len(result.entities),
                'processing_time': result.processing_time,
                'method': result.extraction_method,
                'text_length': len(result.text)
            },
            'entity_counts': result.entity_counts,
            'entities_by_type': {}
        }
        
        # Grouper par type
        for entity in result.entities:
            entity_type = entity.entity_type
            if entity_type not in summary['entities_by_type']:
                summary['entities_by_type'][entity_type] = []
            
            summary['entities_by_type'][entity_type].append({
                'value': entity.value,
                'normalized_value': entity.normalized_value,
                'confidence': entity.confidence,
                'position': (entity.start_position, entity.end_position),
                'context': entity.context
            })
        
        return summary
    
    def create_highlighted_text(self, result: EntityExtractionResult) -> str:
        """Crée une version du texte avec les entités mises en évidence"""
        if not result.entities:
            return result.text
        
        # Couleurs pour différents types d'entités
        colors = {
            'dates': '#ffcccc',
            'amounts': '#ccffcc', 
            'emails': '#ccccff',
            'phones': '#ffffcc',
            'companies': '#ffccff',
            'addresses': '#ccffff',
            'other': '#e0e0e0'
        }
        
        highlighted_text = result.text
        offset = 0
        
        for entity in sorted(result.entities, key=lambda x: x.start_position):
            color = colors.get(entity.entity_type, colors['other'])
            
            start = entity.start_position + offset
            end = entity.end_position + offset
            
            # Créer le marquage HTML
            highlight_start = f'<mark style="background-color:{color}" title="{entity.entity_type} ({entity.confidence:.2f})">'
            highlight_end = '</mark>'
            
            highlighted_text = (
                highlighted_text[:start] + 
                highlight_start + 
                highlighted_text[start:end] + 
                highlight_end + 
                highlighted_text[end:]
            )
            
            offset += len(highlight_start) + len(highlight_end)
        
        return highlighted_text
    
    def export_entities_to_json(self, result: EntityExtractionResult, output_file: str):
        """Exporte les entités vers un fichier JSON"""
        data = {
            'extraction_info': {
                'timestamp': datetime.now().isoformat(),
                'total_entities': len(result.entities),
                'processing_time': result.processing_time,
                'method': result.extraction_method,
                'text_length': len(result.text),
                'entity_counts': result.entity_counts
            },
            'entities': []
        }
        
        for entity in result.entities:
            entity_data = {
                'type': entity.entity_type,
                'value': entity.value,
                'normalized_value': str(entity.normalized_value) if entity.normalized_value else None,
                'confidence': entity.confidence,
                'position': {
                    'start': entity.start_position,
                    'end': entity.end_position
                },
                'context': entity.context,
                'pattern_used': entity.pattern_used
            }
            data['entities'].append(entity_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Entités exportées vers: {output_file}")


def extract_entities_simple(text: str, entity_types: Optional[List[str]] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fonction simple pour extraire des entités
    
    Args:
        text: Texte à analyser
        entity_types: Types d'entités à rechercher
        
    Returns:
        Dictionnaire des entités par type
    """
    extractor = EntityExtractor()
    result = extractor.extract_entities(text, entity_types)
    
    entities_dict = {}
    for entity in result.entities:
        if entity.entity_type not in entities_dict:
            entities_dict[entity.entity_type] = []
        
        entities_dict[entity.entity_type].append({
            'value': entity.value,
            'normalized_value': entity.normalized_value,
            'confidence': entity.confidence,
            'position': (entity.start_position, entity.end_position)
        })
    
    return entities_dict


def extract_document_metadata(text: str) -> Dict[str, Any]:
    """
    Extrait les métadonnées principales d'un document
    
    Args:
        text: Texte du document
        
    Returns:
        Métadonnées structurées du document
    """
    extractor = EntityExtractor()
    result = extractor.extract_entities(text)
    
    metadata = {
        'dates': [],
        'amounts': [],
        'companies': [],
        'contacts': {
            'emails': [],
            'phones': []
        },
        'references': {
            'invoice_numbers': [],
            'siret': [],
            'iban': []
        },
        'summary': extractor.get_structured_summary(result)
    }
    
    for entity in result.entities:
        if entity.entity_type == 'dates':
            metadata['dates'].append({
                'value': entity.value,
                'normalized': entity.normalized_value.isoformat() if entity.normalized_value else None,
                'confidence': entity.confidence
            })
        elif entity.entity_type == 'amounts':
            metadata['amounts'].append({
                'value': entity.value,
                'normalized': str(entity.normalized_value) if entity.normalized_value else None,
                'confidence': entity.confidence
            })
        elif entity.entity_type == 'companies':
            metadata['companies'].append({
                'value': entity.value,
                'confidence': entity.confidence
            })
        elif entity.entity_type == 'emails':
            metadata['contacts']['emails'].append({
                'value': entity.value,
                'confidence': entity.confidence
            })
        elif entity.entity_type == 'phones':
            metadata['contacts']['phones'].append({
                'value': entity.value,
                'normalized': entity.normalized_value,
                'confidence': entity.confidence
            })
        elif entity.entity_type in ['invoice_numbers', 'siret', 'iban']:
            metadata['references'][entity.entity_type].append({
                'value': entity.value,
                'normalized': entity.normalized_value,
                'confidence': entity.confidence
            })
    
    return metadata