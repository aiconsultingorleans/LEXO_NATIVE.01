"""
Module d'extraction d'entités françaises - Étape 3
Extraction spécialisée pour documents administratifs français
"""

import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class FrenchEntity:
    """Entité française extraite avec contexte"""
    type: str  # 'siret', 'tva', 'iban', 'montant', 'date', 'telephone', 'email'
    value: str
    confidence: float
    context: str = ""  # Texte environnant l'entité
    position: int = 0  # Position dans le texte
    validated: bool = False  # Validation algorithmique réussie


@dataclass
class EntityExtractionResult:
    """Résultat d'extraction d'entités"""
    sirets: List[FrenchEntity] = field(default_factory=list)
    tva_numbers: List[FrenchEntity] = field(default_factory=list)
    ibans: List[FrenchEntity] = field(default_factory=list)
    montants: List[FrenchEntity] = field(default_factory=list)
    dates: List[FrenchEntity] = field(default_factory=list)
    telephones: List[FrenchEntity] = field(default_factory=list)
    emails: List[FrenchEntity] = field(default_factory=list)
    organismes: List[FrenchEntity] = field(default_factory=list)
    entreprises: List[FrenchEntity] = field(default_factory=list)
    references: List[FrenchEntity] = field(default_factory=list)
    extraction_time: float = 0.0
    total_entities: int = 0


class FrenchEntityExtractor:
    """Extracteur d'entités françaises optimisé"""
    
    def __init__(self):
        self.logger = logging.getLogger("french_entity_extractor")
        
        # Cache pour performance
        self._compiled_patterns = {}
        self._cache_dir = Path(__file__).parent.parent / "data" / "entity_cache"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Patterns optimisés français
        self.patterns = {
            # SIRET : 14 chiffres (+ validation Luhn)
            'siret': [
                r'\bSIRET\s*:?\s*(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b',
                r'\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b',  # SIRET isolé
                r'siret\s*n[°u\s]*:?\s*(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b'
            ],
            
            # SIREN : 9 chiffres (sous-ensemble SIRET)
            'siren': [
                r'\bSIREN\s*:?\s*(\d{3}\s?\d{3}\s?\d{3})\b',
                r'siren\s*n[°u\s]*:?\s*(\d{3}\s?\d{3}\s?\d{3})\b'
            ],
            
            # TVA française : FR + 11 chiffres
            'tva': [
                r'\bTVA\s*:?\s*(FR\s?\d{2}\s?\d{9})\b',
                r'\b(FR\s?\d{2}\s?\d{9})\b',
                r'tva\s+intracommunautaire\s*:?\s*(FR\s?\d{2}\s?\d{9})\b',
                r'n[°u]\s*tva\s*:?\s*(FR\s?\d{2}\s?\d{9})\b'
            ],
            
            # IBAN français : FR76 + 23 caractères
            'iban': [
                r'\bIBAN\s*:?\s*(FR\d{2}\s?[\dA-Z\s]{20,27})\b',
                r'\b(FR\d{2}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\s?\d{3})\b'
            ],
            
            # BIC français
            'bic': [
                r'\bBIC\s*:?\s*([A-Z]{4}FR[A-Z0-9]{2}[A-Z0-9]{3}?)\b',
                r'\bSWIFT\s*:?\s*([A-Z]{4}FR[A-Z0-9]{2}[A-Z0-9]{3}?)\b'
            ],
            
            # Montants français avec contexte
            'montants': [
                # Format standard français
                r'(\d{1,3}(?:[\s\.]\d{3})*,\d{2})\s*€',
                r'(\d{1,3}(?:[\s\.]\d{3})*,\d{2})\s*euros?',
                r'(\d+,\d{2})\s*€',
                r'(\d+,\d{2})\s*euros?',
                
                # Avec contexte business
                r'(?:total|montant|prix|coût|facture|net à payer|ttc|ht)\s*:?\s*(\d{1,3}(?:[\s\.]\d{3})*,\d{2})\s*€?',
                r'(\d{1,3}(?:[\s\.]\d{3})*,\d{2})\s*€?\s*(?:ttc|ht|euros?|net)',
            ],
            
            # Dates françaises
            'dates': [
                # DD/MM/YYYY et variantes
                r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})\b',
                r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2})\b',
                
                # DD mois YYYY
                r'\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b',
                
                # Contexte dates importantes
                r'(?:échéance|validité|émission|du|au|date)\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b',
                r'(?:valable|expire|valide)\s+(?:jusqu|au)\s*["\']?(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})\b'
            ],
            
            # Téléphones français
            'telephones': [
                r'\b(0[1-9](?:\s?\d{2}){4})\b',  # 01 23 45 67 89
                r'\b(\+33\s?[1-9](?:\s?\d{2}){4})\b',  # +33 1 23 45 67 89
                r'(?:tél|téléphone|portable|mobile)\s*:?\s*(\+?33?[-\s]?[0-9][-\s0-9]{8,})\b'
            ],
            
            # Emails
            'emails': [
                r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b'
            ],
            
            # Organismes français spécifiques
            'organismes': [
                r'\b(URSSAF\s+[A-ZÀ-Ÿ\s\-]+)\b',
                r'\b(CPAM\s+[A-ZÀ-Ÿ\s\-]+)\b',
                r'\b(CAF\s+[A-ZÀ-Ÿ\s\-]+)\b',
                r'\b(Pôle\s+Emploi\s+[A-ZÀ-Ÿ\s\-]*)\b',
                r'\b(DGFIP)\b',
                r'\b(Direction\s+Générale\s+des\s+Finances\s+Publiques)\b'
            ],
            
            # Entreprises/fournisseurs français
            'entreprises': [
                r'\b(EDF|Enedis|Engie|Total|Antargaz)\b',
                r'\b(Orange|SFR|Bouygues\s+Telecom|Free|Red\s+by\s+SFR)\b',
                r'\b(Veolia|Suez|Saur)\b',
                r'\b(Crédit\s+Agricole|BNP\s+Paribas|Société\s+Générale|LCL)\b',
                r'\b(Caisse\s+d[\'"]Épargne|Banque\s+Postale|CIC|Crédit\s+Mutuel)\b'
            ],
            
            # Références/numéros de documents
            'references': [
                r'\b(?:facture|invoice|fact)\s*n[°u\s]*:?\s*(\w*\d+\w*)\b',
                r'\b(?:contrat|police|dossier)\s*n[°u\s]*:?\s*(\w*\d+\w*)\b',
                r'\b(?:référence|ref)\s*:?\s*(\w+\d+\w*)\b',
                r'\bn[°u]\s*(\d{6,})\b'  # Numéros génériques 6+ chiffres
            ]
        }
        
        # Mois français pour conversion dates
        self.mois_francais = {
            'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
            'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
            'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
        }
        
        # Compiler les patterns pour performance
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile les patterns regex pour améliorer les performances"""
        for entity_type, pattern_list in self.patterns.items():
            compiled_patterns = []
            for pattern in pattern_list:
                try:
                    compiled_patterns.append(re.compile(pattern, re.IGNORECASE))
                except re.error as e:
                    self.logger.warning(f"Pattern regex invalide pour {entity_type}: {pattern} - {e}")
            self._compiled_patterns[entity_type] = compiled_patterns
    
    def _validate_siret(self, siret: str) -> bool:
        """Valide un numéro SIRET avec l'algorithme de Luhn"""
        # Nettoyer le SIRET (supprimer espaces)
        clean_siret = re.sub(r'\s+', '', siret)
        
        if len(clean_siret) != 14 or not clean_siret.isdigit():
            return False
        
        # Algorithme de Luhn pour validation SIRET
        def luhn_checksum(card_num):
            def digits_of(n):
                return [int(d) for d in str(n)]
            
            digits = digits_of(card_num)
            odd_digits = digits[-1::-2]
            even_digits = digits[-2::-2]
            checksum = sum(odd_digits)
            for d in even_digits:
                checksum += sum(digits_of(d*2))
            return checksum % 10
        
        return luhn_checksum(int(clean_siret)) == 0
    
    def _validate_tva_fr(self, tva: str) -> bool:
        """Valide un numéro de TVA français"""
        # Nettoyer la TVA
        clean_tva = re.sub(r'\s+', '', tva.upper())
        
        if not clean_tva.startswith('FR') or len(clean_tva) != 13:
            return False
        
        # Vérifier que les caractères après FR sont des chiffres
        return clean_tva[2:].isdigit()
    
    def _validate_iban_fr(self, iban: str) -> bool:
        """Valide un IBAN français (validation simplifiée)"""
        # Nettoyer l'IBAN
        clean_iban = re.sub(r'\s+', '', iban.upper())
        
        if not clean_iban.startswith('FR') or len(clean_iban) != 27:
            return False
        
        # Vérifier format (FR + 2 chiffres + 23 caractères alphanumériques)
        return re.match(r'^FR\d{2}[A-Z0-9]{23}$', clean_iban) is not None
    
    def _normalize_date(self, day: str, month: str, year: str) -> Optional[str]:
        """Normalise une date au format DD/MM/YYYY"""
        try:
            # Convertir mois texte en numéro
            if month.lower() in self.mois_francais:
                month = self.mois_francais[month.lower()]
            
            # Normaliser l'année (2 chiffres -> 4 chiffres)
            if len(year) == 2:
                current_year = datetime.now().year
                year_int = int(year)
                if year_int <= (current_year % 100):
                    year = f"20{year}"
                else:
                    year = f"19{year}"
            
            # Valider la date
            datetime.strptime(f"{day}/{month}/{year}", "%d/%m/%Y")
            return f"{day.zfill(2)}/{month.zfill(2)}/{year}"
            
        except (ValueError, KeyError):
            return None
    
    def _extract_with_context(self, text: str, entity_type: str, pattern_compiled: re.Pattern) -> List[FrenchEntity]:
        """Extrait les entités avec leur contexte"""
        entities = []
        
        for match in pattern_compiled.finditer(text):
            # Récupérer la valeur (premier groupe de capture ou match complet)
            if match.groups():
                value = match.group(1)
            else:
                value = match.group(0)
            
            # Nettoyer la valeur
            value = value.strip()
            if not value:
                continue
            
            # Extraire le contexte (30 caractères avant et après)
            start_pos = max(0, match.start() - 30)
            end_pos = min(len(text), match.end() + 30)
            context = text[start_pos:end_pos].replace('\n', ' ').strip()
            
            # Calculer la confiance de base
            confidence = 0.7  # Confiance de base
            
            # Validation et ajustement confiance
            validated = False
            if entity_type == 'siret':
                validated = self._validate_siret(value)
                confidence = 0.9 if validated else 0.6
            elif entity_type == 'tva':
                validated = self._validate_tva_fr(value)
                confidence = 0.9 if validated else 0.6
            elif entity_type == 'iban':
                validated = self._validate_iban_fr(value)
                confidence = 0.9 if validated else 0.6
            elif 'montant' in entity_type:
                # Confiance plus élevée si format correct
                if re.match(r'^\d{1,3}(?:[\s\.]\d{3})*,\d{2}$', value):
                    confidence = 0.8
            
            entity = FrenchEntity(
                type=entity_type,
                value=value,
                confidence=confidence,
                context=context,
                position=match.start(),
                validated=validated
            )
            
            entities.append(entity)
        
        return entities
    
    def extract_entities(self, text: str, filename: str = "") -> EntityExtractionResult:
        """
        Extraction complète d'entités françaises
        
        Args:
            text: Texte à analyser
            filename: Nom du fichier (optionnel, pour cache)
            
        Returns:
            EntityExtractionResult avec toutes les entités extraites
        """
        start_time = datetime.now()
        
        # Vérifier le cache si filename fourni
        if filename:
            cached_result = self._get_cached_result(text, filename)
            if cached_result:
                self.logger.debug(f"Entités récupérées du cache pour {filename}")
                return cached_result
        
        result = EntityExtractionResult()
        
        if not text or not text.strip():
            return result
        
        # Nettoyer le texte (garder les caractères importants)
        clean_text = text.strip()
        
        try:
            # Extraction SIRET
            for pattern in self._compiled_patterns.get('siret', []):
                entities = self._extract_with_context(clean_text, 'siret', pattern)
                result.sirets.extend(entities)
            
            # Extraction TVA
            for pattern in self._compiled_patterns.get('tva', []):
                entities = self._extract_with_context(clean_text, 'tva', pattern)
                result.tva_numbers.extend(entities)
            
            # Extraction IBAN
            for pattern in self._compiled_patterns.get('iban', []):
                entities = self._extract_with_context(clean_text, 'iban', pattern)
                result.ibans.extend(entities)
            
            # Extraction montants avec logique spéciale
            result.montants = self._extract_montants_francais(clean_text)
            
            # Extraction dates avec normalisation
            result.dates = self._extract_dates_francaises(clean_text)
            
            # Extraction téléphones
            for pattern in self._compiled_patterns.get('telephones', []):
                entities = self._extract_with_context(clean_text, 'telephone', pattern)
                result.telephones.extend(entities)
            
            # Extraction emails
            for pattern in self._compiled_patterns.get('emails', []):
                entities = self._extract_with_context(clean_text, 'email', pattern)
                result.emails.extend(entities)
            
            # Extraction organismes
            for pattern in self._compiled_patterns.get('organismes', []):
                entities = self._extract_with_context(clean_text, 'organisme', pattern)
                result.organismes.extend(entities)
            
            # Extraction entreprises
            for pattern in self._compiled_patterns.get('entreprises', []):
                entities = self._extract_with_context(clean_text, 'entreprise', pattern)
                result.entreprises.extend(entities)
            
            # Extraction références
            for pattern in self._compiled_patterns.get('references', []):
                entities = self._extract_with_context(clean_text, 'reference', pattern)
                result.references.extend(entities)
            
        except Exception as e:
            self.logger.error(f"Erreur lors de l'extraction d'entités: {e}")
        
        # Déduplication et tri par confiance
        result = self._deduplicate_and_sort(result)
        
        # Calculer statistiques finales
        result.total_entities = (
            len(result.sirets) + len(result.tva_numbers) + len(result.ibans) +
            len(result.montants) + len(result.dates) + len(result.telephones) +
            len(result.emails) + len(result.organismes) + len(result.entreprises) +
            len(result.references)
        )
        
        result.extraction_time = (datetime.now() - start_time).total_seconds()
        
        # Sauvegarder en cache si filename fourni
        if filename and result.total_entities > 0:
            self._cache_result(text, filename, result)
        
        self.logger.info(f"Extraction terminée: {result.total_entities} entités en {result.extraction_time:.2f}s")
        
        return result
    
    def _extract_montants_francais(self, text: str) -> List[FrenchEntity]:
        """Extraction spécialisée pour les montants français"""
        montants = []
        
        for pattern in self._compiled_patterns.get('montants', []):
            for match in pattern.finditer(text):
                value = match.group(1) if match.groups() else match.group(0)
                value = value.strip()
                
                if not value:
                    continue
                
                # Context étendu pour montants
                start_pos = max(0, match.start() - 50)
                end_pos = min(len(text), match.end() + 50)
                context = text[start_pos:end_pos].replace('\n', ' ').strip()
                
                # Analyser le contexte pour améliorer la confiance
                confidence = 0.7
                context_lower = context.lower()
                
                # Boost confiance avec mots-clés business
                business_keywords = ['total', 'montant', 'facture', 'net à payer', 'ttc', 'ht', 'prix', 'coût']
                if any(keyword in context_lower for keyword in business_keywords):
                    confidence = 0.9
                
                # Boost si format parfait français
                if re.match(r'^\d{1,3}(?:[\s\.]\d{3})*,\d{2}$', value):
                    confidence = min(0.95, confidence + 0.1)
                
                entity = FrenchEntity(
                    type='montant',
                    value=value,
                    confidence=confidence,
                    context=context,
                    position=match.start(),
                    validated=True  # Montants sont toujours considérés valides si format OK
                )
                
                montants.append(entity)
        
        return montants
    
    def _extract_dates_francaises(self, text: str) -> List[FrenchEntity]:
        """Extraction spécialisée pour les dates françaises"""
        dates = []
        
        # Pattern standard DD/MM/YYYY
        date_pattern = re.compile(r'\b(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})\b')
        for match in date_pattern.finditer(text):
            day, month, year = match.groups()
            normalized_date = self._normalize_date(day, month, year)
            
            if normalized_date:
                context = text[max(0, match.start()-30):match.end()+30].replace('\n', ' ').strip()
                
                # Analyser contexte pour type de date
                context_lower = context.lower()
                confidence = 0.8
                
                date_keywords = ['échéance', 'validité', 'émission', 'expire', 'valable']
                if any(keyword in context_lower for keyword in date_keywords):
                    confidence = 0.9
                
                entity = FrenchEntity(
                    type='date',
                    value=normalized_date,
                    confidence=confidence,
                    context=context,
                    position=match.start(),
                    validated=True
                )
                
                dates.append(entity)
        
        # Pattern DD mois YYYY en français
        month_pattern = re.compile(
            r'\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b',
            re.IGNORECASE
        )
        
        for match in month_pattern.finditer(text):
            day, month_name, year = match.groups()
            normalized_date = self._normalize_date(day, month_name, year)
            
            if normalized_date:
                context = text[max(0, match.start()-30):match.end()+30].replace('\n', ' ').strip()
                
                entity = FrenchEntity(
                    type='date',
                    value=normalized_date,
                    confidence=0.9,  # Format français complet = confiance élevée
                    context=context,
                    position=match.start(),
                    validated=True
                )
                
                dates.append(entity)
        
        return dates
    
    def _deduplicate_and_sort(self, result: EntityExtractionResult) -> EntityExtractionResult:
        """Déduplique et trie les entités par confiance"""
        
        def dedupe_entities(entities: List[FrenchEntity]) -> List[FrenchEntity]:
            """Déduplique une liste d'entités"""
            seen_values = set()
            deduped = []
            
            # Trier par confiance décroissante
            entities.sort(key=lambda e: e.confidence, reverse=True)
            
            for entity in entities:
                # Normaliser la valeur pour comparaison
                normalized_value = re.sub(r'\s+', '', entity.value.upper())
                
                if normalized_value not in seen_values:
                    seen_values.add(normalized_value)
                    deduped.append(entity)
            
            return deduped[:5]  # Limiter à 5 entités par type pour performance
        
        # Appliquer la déduplication à tous les types
        result.sirets = dedupe_entities(result.sirets)
        result.tva_numbers = dedupe_entities(result.tva_numbers)
        result.ibans = dedupe_entities(result.ibans)
        result.montants = dedupe_entities(result.montants)
        result.dates = dedupe_entities(result.dates)
        result.telephones = dedupe_entities(result.telephones)
        result.emails = dedupe_entities(result.emails)
        result.organismes = dedupe_entities(result.organismes)
        result.entreprises = dedupe_entities(result.entreprises)
        result.references = dedupe_entities(result.references)
        
        return result
    
    def _get_cache_key(self, text: str, filename: str) -> str:
        """Génère une clé de cache basée sur le contenu et filename"""
        content_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{filename}_{content_hash[:16]}"
    
    def _get_cached_result(self, text: str, filename: str) -> Optional[EntityExtractionResult]:
        """Récupère un résultat du cache si disponible"""
        try:
            cache_key = self._get_cache_key(text, filename)
            cache_file = self._cache_dir / f"{cache_key}.json"
            
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Reconstruire le résultat depuis le JSON
                result = EntityExtractionResult()
                for entity_type in ['sirets', 'tva_numbers', 'ibans', 'montants', 'dates', 
                                  'telephones', 'emails', 'organismes', 'entreprises', 'references']:
                    entities = []
                    for entity_data in data.get(entity_type, []):
                        entity = FrenchEntity(**entity_data)
                        entities.append(entity)
                    setattr(result, entity_type, entities)
                
                result.total_entities = data.get('total_entities', 0)
                result.extraction_time = data.get('extraction_time', 0.0)
                
                return result
                
        except Exception as e:
            self.logger.warning(f"Erreur lecture cache: {e}")
        
        return None
    
    def _cache_result(self, text: str, filename: str, result: EntityExtractionResult):
        """Sauvegarde le résultat en cache"""
        try:
            cache_key = self._get_cache_key(text, filename)
            cache_file = self._cache_dir / f"{cache_key}.json"
            
            # Convertir en dict pour JSON
            data = {
                'timestamp': datetime.now().isoformat(),
                'filename': filename,
                'total_entities': result.total_entities,
                'extraction_time': result.extraction_time
            }
            
            # Convertir chaque liste d'entités
            for entity_type in ['sirets', 'tva_numbers', 'ibans', 'montants', 'dates',
                              'telephones', 'emails', 'organismes', 'entreprises', 'references']:
                entities = getattr(result, entity_type)
                data[entity_type] = [
                    {
                        'type': e.type,
                        'value': e.value,
                        'confidence': e.confidence,
                        'context': e.context,
                        'position': e.position,
                        'validated': e.validated
                    }
                    for e in entities
                ]
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            self.logger.warning(f"Erreur écriture cache: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourne des statistiques sur l'extracteur"""
        return {
            'patterns_compiled': len(self._compiled_patterns),
            'cache_directory': str(self._cache_dir),
            'supported_entities': list(self.patterns.keys()),
            'validation_algorithms': ['siret_luhn', 'tva_french', 'iban_french']
        }


# Instance globale pour éviter la re-initialisation
_extractor_instance = None

def get_french_entity_extractor() -> FrenchEntityExtractor:
    """Retourne l'instance singleton de l'extracteur"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = FrenchEntityExtractor()
    return _extractor_instance