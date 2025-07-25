"""
Système de prompts optimisé pour Mistral et l'analyse documentaire française.
"""
import logging
from typing import Dict, List, Any, Optional
from enum import Enum
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)

class PromptType(Enum):
    """Types de prompts disponibles."""
    DOCUMENT_ANALYSIS = "document_analysis"
    QUESTION_ANSWERING = "question_answering"
    DOCUMENT_SUMMARY = "document_summary"
    ENTITY_EXTRACTION = "entity_extraction"
    CLASSIFICATION = "classification"
    COMPARISON = "comparison"
    SEARCH_CONTEXT = "search_context"

@dataclass
class PromptTemplate:
    """Template de prompt avec métadonnées."""
    name: str
    type: PromptType
    system_prompt: str
    user_template: str
    expected_format: str
    max_tokens: int = 512
    temperature: float = 0.7
    examples: List[str] = None

class PromptSystem:
    """Système de gestion des prompts pour RAG."""
    
    def __init__(self):
        self.templates = {}
        self._initialize_templates()
    
    def _initialize_templates(self):
        """Initialise tous les templates de prompts."""
        try:
            # Prompt pour analyse générale de documents
            self.templates[PromptType.DOCUMENT_ANALYSIS] = PromptTemplate(
                name="Analyse de document",
                type=PromptType.DOCUMENT_ANALYSIS,
                system_prompt="""Tu es un expert en analyse de documents administratifs français.
Analyse le document fourni de manière structurée et factuelle.
Extrais les informations clés et réponds aux questions avec précision.
Si une information n'est pas présente, indique-le clairement.
Utilise uniquement les informations du document fourni.""",
                user_template="""Document à analyser:
{document_text}

Question: {question}

Réponds de manière structurée en citant les passages pertinents.""",
                expected_format="Réponse structurée avec citations",
                max_tokens=400,
                temperature=0.3
            )
            
            # Prompt pour réponse à des questions
            self.templates[PromptType.QUESTION_ANSWERING] = PromptTemplate(
                name="Réponse aux questions",
                type=PromptType.QUESTION_ANSWERING,
                system_prompt="""Tu es un assistant spécialisé dans l'analyse de documents français.
Réponds aux questions en te basant uniquement sur le contexte fourni.
Sois précis, factuel et concis. Si l'information n'est pas dans le contexte, dis-le clairement.
Cite les sources quand c'est pertinent.""",
                user_template="""Contexte:
{context}

Question: {question}

Réponse:""",
                expected_format="Réponse directe et factuelle",
                max_tokens=300,
                temperature=0.2
            )
            
            # Prompt pour résumé de documents
            self.templates[PromptType.DOCUMENT_SUMMARY] = PromptTemplate(
                name="Résumé de document",
                type=PromptType.DOCUMENT_SUMMARY,
                system_prompt="""Tu es un expert en synthèse de documents administratifs.
Crée un résumé clair et structuré du document fourni.
Mets en avant les points essentiels et les informations importantes.
Organise le résumé de manière logique.""",
                user_template="""Document à résumer:
{document_text}

Crée un résumé structuré de ce document en français.""",
                expected_format="Résumé structuré avec points clés",
                max_tokens=600,
                temperature=0.4
            )
            
            # Prompt pour extraction d'entités
            self.templates[PromptType.ENTITY_EXTRACTION] = PromptTemplate(
                name="Extraction d'entités",
                type=PromptType.ENTITY_EXTRACTION,
                system_prompt="""Tu es un extracteur d'entités spécialisé dans les documents français.
Extrais les entités importantes du document: noms, dates, montants, adresses, références.
Présente les résultats de manière structurée et précise.
N'extrais que les entités explicitement mentionnées.""",
                user_template="""Document:
{document_text}

Extrais les entités importantes de ce document français.
Format: JSON avec catégories (noms, dates, montants, adresses, références).""",
                expected_format="JSON structuré des entités",
                max_tokens=400,
                temperature=0.1
            )
            
            # Prompt pour classification
            self.templates[PromptType.CLASSIFICATION] = PromptTemplate(
                name="Classification de document",
                type=PromptType.CLASSIFICATION,
                system_prompt="""Tu es un classificateur de documents administratifs français.
Analyse le document et détermine son type parmi les catégories disponibles.
Base-toi sur le contenu, la structure et les éléments caractéristiques.
Justifie ton choix avec des éléments concrets du document.""",
                user_template="""Document à classifier:
{document_text}

Catégories possibles: {categories}

Détermine le type de ce document et justifie ton choix.""",
                expected_format="Type + justification",
                max_tokens=200,
                temperature=0.2
            )
            
            # Prompt pour comparaison de documents
            self.templates[PromptType.COMPARISON] = PromptTemplate(
                name="Comparaison de documents",
                type=PromptType.COMPARISON,
                system_prompt="""Tu es un expert en comparaison de documents administratifs.
Compare les documents fournis et identifie les similitudes et différences.
Mets en avant les points importants et les divergences significatives.
Organise la comparaison de manière claire et structurée.""",
                user_template="""Document 1:
{document1}

Document 2:
{document2}

Compare ces documents en identifiant similitudes et différences importantes.""",
                expected_format="Comparaison structurée",
                max_tokens=500,
                temperature=0.3
            )
            
            # Prompt pour contexte de recherche
            self.templates[PromptType.SEARCH_CONTEXT] = PromptTemplate(
                name="Recherche contextuelle",
                type=PromptType.SEARCH_CONTEXT,
                system_prompt="""Tu es un assistant de recherche documentaire intelligent.
Analyse la question et le contexte de documents trouvés.
Fournis une réponse complète en synthétisant les informations pertinentes.
Cite les sources et indique le niveau de confiance de ta réponse.""",
                user_template="""Question: {question}

Documents trouvés:
{search_results}

Synthétise ces informations pour répondre à la question.""",
                expected_format="Synthèse avec sources",
                max_tokens=600,
                temperature=0.4
            )
            
            logger.info(f"Système de prompts initialisé: {len(self.templates)} templates")
            
        except Exception as e:
            logger.error(f"Erreur initialisation templates: {e}")
    
    def get_prompt(
        self,
        prompt_type: PromptType,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Génère un prompt complet à partir d'un template.
        
        Args:
            prompt_type: Type de prompt désiré
            **kwargs: Variables pour le template
            
        Returns:
            Dict avec system_prompt, user_prompt et config
        """
        try:
            if prompt_type not in self.templates:
                logger.error(f"Template {prompt_type} non trouvé")
                return self._get_fallback_prompt(kwargs.get("question", ""))
            
            template = self.templates[prompt_type]
            
            # Formatage du prompt utilisateur
            try:
                user_prompt = template.user_template.format(**kwargs)
            except KeyError as e:
                logger.error(f"Variable manquante pour template {prompt_type}: {e}")
                return self._get_fallback_prompt(kwargs.get("question", ""))
            
            return {
                "system_prompt": template.system_prompt,
                "user_prompt": user_prompt,
                "config": {
                    "max_tokens": template.max_tokens,
                    "temperature": template.temperature,
                    "expected_format": template.expected_format
                },
                "template_name": template.name
            }
            
        except Exception as e:
            logger.error(f"Erreur génération prompt: {e}")
            return self._get_fallback_prompt(kwargs.get("question", ""))
    
    def get_document_analysis_prompt(
        self,
        document_text: str,
        question: str,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Prompt spécialisé pour l'analyse de documents."""
        try:
            # Adaptation selon le type de document
            if document_type:
                specialized_system = self._get_specialized_system_prompt(document_type)
                if specialized_system:
                    # Template personnalisé
                    return {
                        "system_prompt": specialized_system,
                        "user_prompt": f"Document:\n{document_text}\n\nQuestion: {question}",
                        "config": {"max_tokens": 400, "temperature": 0.3}
                    }
            
            # Template standard
            return self.get_prompt(
                PromptType.DOCUMENT_ANALYSIS,
                document_text=document_text,
                question=question
            )
            
        except Exception as e:
            logger.error(f"Erreur prompt analyse document: {e}")
            return self._get_fallback_prompt(question)
    
    def get_rag_search_prompt(
        self,
        question: str,
        search_results: List[Dict[str, Any]],
        max_context_length: int = 2000
    ) -> Dict[str, Any]:
        """Prompt optimisé pour RAG avec résultats de recherche."""
        try:
            # Formatage des résultats de recherche
            formatted_results = []
            current_length = 0
            
            for i, result in enumerate(search_results):
                if current_length >= max_context_length:
                    break
                
                text = result.get("text", "")
                metadata = result.get("metadata", {})
                score = result.get("score", 0.0)
                
                # Formatage avec métadonnées
                formatted_result = f"""[Document {i+1}] (Pertinence: {score:.2f})
Source: {metadata.get('filename', 'Unknown')}
Type: {metadata.get('document_type', 'Unknown')}
Contenu: {text[:500]}..."""
                
                if current_length + len(formatted_result) <= max_context_length:
                    formatted_results.append(formatted_result)
                    current_length += len(formatted_result)
            
            search_context = "\n\n".join(formatted_results)
            
            return self.get_prompt(
                PromptType.SEARCH_CONTEXT,
                question=question,
                search_results=search_context
            )
            
        except Exception as e:
            logger.error(f"Erreur prompt RAG: {e}")
            return self._get_fallback_prompt(question)
    
    def _get_specialized_system_prompt(self, document_type: str) -> Optional[str]:
        """Prompts système spécialisés par type de document."""
        try:
            specializations = {
                "facture": """Tu es un expert en analyse de factures françaises.
Identifie les montants, dates, TVA, références, fournisseurs et clients.
Calcule les totaux et vérifie la cohérence des montants.
Signale toute anomalie ou information manquante.""",
                
                "contrat": """Tu es un expert en analyse de contrats français.
Identifie les parties, objets, durées, conditions et obligations.
Mets en avant les clauses importantes et les échéances.
Signale les points d'attention juridiques.""",
                
                "transport": """Tu es un expert en titres de transport français.
Identifie les zones, validités, tarifs et conditions d'usage.
Extrais les informations de voyage et les restrictions.
Vérifie les dates de validité.""",
                
                "bancaire": """Tu es un expert en documents bancaires français.
Identifie les IBAN, BIC, montants, dates de virement.
Vérifie la cohérence des informations bancaires.
Extrais les références de transactions."""
            }
            
            return specializations.get(document_type.lower())
            
        except Exception as e:
            logger.warning(f"Erreur prompt spécialisé: {e}")
            return None
    
    def _get_fallback_prompt(self, question: str) -> Dict[str, Any]:
        """Prompt de fallback en cas d'erreur."""
        return {
            "system_prompt": """Tu es un assistant IA spécialisé dans l'analyse de documents.
Réponds de manière factuelle et précise.""",
            "user_prompt": question,
            "config": {"max_tokens": 300, "temperature": 0.5},
            "template_name": "fallback"
        }
    
    def add_custom_template(self, template: PromptTemplate) -> bool:
        """Ajoute un template personnalisé."""
        try:
            self.templates[template.type] = template
            logger.info(f"Template personnalisé ajouté: {template.name}")
            return True
        except Exception as e:
            logger.error(f"Erreur ajout template: {e}")
            return False
    
    def get_prompt_suggestions(self, document_text: str) -> List[str]:
        """Suggère des questions pertinentes pour un document."""
        try:
            # Suggestions basées sur le contenu
            suggestions = []
            text_lower = document_text.lower()
            
            # Suggestions génériques
            suggestions.extend([
                "Quel est le résumé de ce document ?",
                "Quelles sont les informations principales ?"
            ])
            
            # Suggestions spécialisées
            if any(word in text_lower for word in ["€", "montant", "total", "prix"]):
                suggestions.extend([
                    "Quel est le montant total ?",
                    "Quels sont les différents montants mentionnés ?"
                ])
            
            if any(word in text_lower for word in ["date", "échéance", "validité"]):
                suggestions.extend([
                    "Quelles sont les dates importantes ?",
                    "Quelle est la date d'échéance ?"
                ])
            
            if any(word in text_lower for word in ["nom", "société", "client"]):
                suggestions.extend([
                    "Qui sont les parties mentionnées ?",
                    "Quels sont les noms et coordonnées ?"
                ])
            
            return suggestions[:8]  # Max 8 suggestions
            
        except Exception as e:
            logger.error(f"Erreur suggestions: {e}")
            return ["Quel est le contenu de ce document ?"]
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Statistiques sur les templates."""
        try:
            stats = {
                "total_templates": len(self.templates),
                "templates_by_type": {},
                "average_max_tokens": 0,
                "temperature_range": {"min": 1.0, "max": 0.0}
            }
            
            total_tokens = 0
            for template in self.templates.values():
                # Comptage par type
                type_name = template.type.value
                stats["templates_by_type"][type_name] = stats["templates_by_type"].get(type_name, 0) + 1
                
                # Moyennes
                total_tokens += template.max_tokens
                
                # Ranges
                stats["temperature_range"]["min"] = min(stats["temperature_range"]["min"], template.temperature)
                stats["temperature_range"]["max"] = max(stats["temperature_range"]["max"], template.temperature)
            
            if self.templates:
                stats["average_max_tokens"] = total_tokens // len(self.templates)
            
            return stats
            
        except Exception as e:
            logger.error(f"Erreur stats templates: {e}")
            return {}

# Instance globale du système de prompts
prompt_system = PromptSystem()