"""
Stratégies de chunking de texte pour optimiser les embeddings.
"""
import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class ChunkingStrategy(Enum):
    """Stratégies de chunking disponibles."""
    SENTENCE = "sentence"          # Par phrases
    PARAGRAPH = "paragraph"        # Par paragraphes  
    SEMANTIC = "semantic"          # Sémantique (groupes logiques)
    FIXED_SIZE = "fixed_size"      # Taille fixe avec overlap
    STRUCTURE_AWARE = "structure"   # Conscient de la structure du document

@dataclass
class ChunkConfig:
    """Configuration pour le chunking."""
    strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH
    max_chunk_size: int = 512      # Taille max en caractères
    overlap_size: int = 50         # Chevauchement entre chunks
    min_chunk_size: int = 50       # Taille min pour être valide
    preserve_sentences: bool = True # Préserver les phrases complètes
    
class TextChunker:
    """Service de chunking de texte intelligent."""
    
    def __init__(self):
        self.sentence_patterns = [
            r'[.!?]+\s+',               # Points, exclamations, questions + espace
            r'[.!?]+$',                 # Fin de texte
            r'\n\s*\n',                 # Double saut de ligne
        ]
        
        self.paragraph_patterns = [
            r'\n\s*\n+',                # Paragraphes séparés par lignes vides
            r'\n(?=[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏ])', # Nouvelle ligne + majuscule
        ]
    
    def chunk_text(
        self, 
        text: str, 
        metadata: Optional[Dict[str, Any]] = None,
        config: Optional[ChunkConfig] = None
    ) -> List[Dict[str, Any]]:
        """
        Découpe un texte en chunks selon la stratégie choisie.
        
        Args:
            text: Texte à découper
            metadata: Métadonnées du document
            config: Configuration de chunking
            
        Returns:
            Liste de chunks avec métadonnées
        """
        try:
            if not text or len(text.strip()) < 10:
                return []
            
            config = config or ChunkConfig()
            
            # Nettoyage du texte
            cleaned_text = self._clean_text(text)
            
            # Choix de la stratégie selon le type de document
            if metadata:
                config = self._adapt_strategy_to_document(metadata, config)
            
            # Application de la stratégie
            chunks = self._apply_chunking_strategy(cleaned_text, config)
            
            # Post-traitement et enrichissement
            enriched_chunks = self._enrich_chunks(chunks, metadata, config)
            
            logger.info(f"Texte découpé en {len(enriched_chunks)} chunks avec stratégie {config.strategy.value}")
            
            return enriched_chunks
            
        except Exception as e:
            logger.error(f"Erreur lors du chunking: {e}")
            return [{"text": text, "metadata": metadata or {}}]  # Fallback
    
    def _clean_text(self, text: str) -> str:
        """Nettoie le texte avant chunking."""
        try:
            # Suppression des espaces multiples
            text = re.sub(r'\s+', ' ', text)
            
            # Suppression des caractères de contrôle
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)
            
            # Normalisation des sauts de ligne
            text = re.sub(r'\r\n|\r', '\n', text)
            
            # Suppression des lignes vides multiples
            text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"Erreur nettoyage texte: {e}")
            return text
    
    def _adapt_strategy_to_document(
        self, 
        metadata: Dict[str, Any], 
        config: ChunkConfig
    ) -> ChunkConfig:
        """Adapte la stratégie selon le type de document."""
        try:
            doc_type = metadata.get("document_type", "").lower()
            
            # Factures : chunks plus petits, préservation structure
            if doc_type == "facture":
                config.strategy = ChunkingStrategy.STRUCTURE_AWARE
                config.max_chunk_size = 256
                config.overlap_size = 30
            
            # Contrats : par paragraphes logiques
            elif doc_type == "contrat":
                config.strategy = ChunkingStrategy.PARAGRAPH
                config.max_chunk_size = 768
                config.overlap_size = 100
            
            # Documents avec tableaux : préservation structure
            elif metadata.get("has_tables"):
                config.strategy = ChunkingStrategy.STRUCTURE_AWARE
                config.max_chunk_size = 400
            
            # Documents courts : un seul chunk
            elif len(metadata.get("text", "")) < 200:
                config.strategy = ChunkingStrategy.FIXED_SIZE
                config.max_chunk_size = 1000
                config.overlap_size = 0
            
            return config
            
        except Exception as e:
            logger.warning(f"Erreur adaptation stratégie: {e}")
            return config
    
    def _apply_chunking_strategy(self, text: str, config: ChunkConfig) -> List[str]:
        """Applique la stratégie de chunking."""
        try:
            if config.strategy == ChunkingStrategy.SENTENCE:
                return self._chunk_by_sentences(text, config)
            
            elif config.strategy == ChunkingStrategy.PARAGRAPH:
                return self._chunk_by_paragraphs(text, config)
            
            elif config.strategy == ChunkingStrategy.SEMANTIC:
                return self._chunk_semantically(text, config)
            
            elif config.strategy == ChunkingStrategy.STRUCTURE_AWARE:
                return self._chunk_structure_aware(text, config)
            
            else:  # FIXED_SIZE
                return self._chunk_fixed_size(text, config)
                
        except Exception as e:
            logger.error(f"Erreur application stratégie: {e}")
            return [text]  # Fallback
    
    def _chunk_by_sentences(self, text: str, config: ChunkConfig) -> List[str]:
        """Chunking par phrases."""
        try:
            # Division en phrases
            sentences = []
            current_pos = 0
            
            for pattern in self.sentence_patterns:
                matches = list(re.finditer(pattern, text))
                for match in matches:
                    if match.start() > current_pos:
                        sentence = text[current_pos:match.end()].strip()
                        if len(sentence) >= config.min_chunk_size:
                            sentences.append(sentence)
                        current_pos = match.end()
            
            # Reste du texte
            if current_pos < len(text):
                remaining = text[current_pos:].strip()
                if len(remaining) >= config.min_chunk_size:
                    sentences.append(remaining)
            
            # Regroupement selon la taille max
            return self._group_by_size(sentences, config)
            
        except Exception as e:
            logger.error(f"Erreur chunking par phrases: {e}")
            return [text]
    
    def _chunk_by_paragraphs(self, text: str, config: ChunkConfig) -> List[str]:
        """Chunking par paragraphes."""
        try:
            # Division par paragraphes
            paragraphs = re.split(r'\n\s*\n+', text)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            # Filtrage par taille minimum
            valid_paragraphs = [
                p for p in paragraphs 
                if len(p) >= config.min_chunk_size
            ]
            
            # Regroupement selon la taille max
            return self._group_by_size(valid_paragraphs, config)
            
        except Exception as e:
            logger.error(f"Erreur chunking par paragraphes: {e}")
            return [text]
    
    def _chunk_semantically(self, text: str, config: ChunkConfig) -> List[str]:
        """Chunking sémantique (groupes logiques)."""
        try:
            # Marqueurs sémantiques
            semantic_markers = [
                r'\n(?=\d+[\.\)]\s)',       # Listes numérotées
                r'\n(?=[A-Z][^.]*:)',       # Titres avec deux-points
                r'\n(?=Article\s+\d+)',     # Articles numérotés
                r'\n(?=ARTICLE\s+\d+)',     # Articles en majuscules
                r'\n(?=[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏ]{2,})', # Titres en majuscules
            ]
            
            chunks = []
            current_pos = 0
            
            # Recherche des marqueurs
            for pattern in semantic_markers:
                matches = list(re.finditer(pattern, text))
                for match in matches:
                    if match.start() > current_pos:
                        chunk = text[current_pos:match.start()].strip()
                        if len(chunk) >= config.min_chunk_size:
                            chunks.append(chunk)
                    current_pos = match.start()
            
            # Reste du texte
            if current_pos < len(text):
                remaining = text[current_pos:].strip()
                if len(remaining) >= config.min_chunk_size:
                    chunks.append(remaining)
            
            # Si pas de structure sémantique trouvée, fallback sur paragraphes
            if not chunks:
                return self._chunk_by_paragraphs(text, config)
            
            return self._group_by_size(chunks, config)
            
        except Exception as e:
            logger.error(f"Erreur chunking sémantique: {e}")
            return self._chunk_by_paragraphs(text, config)
    
    def _chunk_structure_aware(self, text: str, config: ChunkConfig) -> List[str]:
        """Chunking conscient de la structure (tableaux, listes, etc.)."""
        try:
            chunks = []
            current_chunk = ""
            
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Détection de structures spéciales
                is_table_row = self._is_table_row(line)
                is_list_item = self._is_list_item(line)
                is_header = self._is_header(line)
                
                # Si nouvelle structure et chunk actuel non vide
                if (is_header or is_table_row) and current_chunk:
                    if len(current_chunk) >= config.min_chunk_size:
                        chunks.append(current_chunk.strip())
                    current_chunk = ""
                
                current_chunk += line + "\n"
                
                # Si chunk trop grand, le finaliser
                if len(current_chunk) >= config.max_chunk_size:
                    if len(current_chunk) >= config.min_chunk_size:
                        chunks.append(current_chunk.strip())
                    current_chunk = ""
            
            # Dernier chunk
            if current_chunk and len(current_chunk) >= config.min_chunk_size:
                chunks.append(current_chunk.strip())
            
            return chunks if chunks else [text]
            
        except Exception as e:
            logger.error(f"Erreur chunking structure-aware: {e}")
            return [text]
    
    def _chunk_fixed_size(self, text: str, config: ChunkConfig) -> List[str]:
        """Chunking à taille fixe avec chevauchement."""
        try:
            chunks = []
            start = 0
            
            while start < len(text):
                end = start + config.max_chunk_size
                
                # Si pas à la fin, chercher un point d'arrêt propre
                if end < len(text) and config.preserve_sentences:
                    # Chercher le dernier point ou saut de ligne
                    for i in range(end, max(start + config.min_chunk_size, end - 100), -1):
                        if text[i] in '.!?\n':
                            end = i + 1
                            break
                
                chunk = text[start:end].strip()
                if len(chunk) >= config.min_chunk_size:
                    chunks.append(chunk)
                
                # Calcul du prochain début avec overlap
                start = max(start + 1, end - config.overlap_size)
                
                # Éviter les boucles infinies
                if start >= len(text):
                    break
            
            return chunks if chunks else [text]
            
        except Exception as e:
            logger.error(f"Erreur chunking taille fixe: {e}")
            return [text]
    
    def _group_by_size(self, items: List[str], config: ChunkConfig) -> List[str]:
        """Regroupe les éléments selon la taille maximale."""
        try:
            chunks = []
            current_chunk = ""
            
            for item in items:
                # Si l'ajout dépasse la taille max, finaliser le chunk actuel
                if current_chunk and len(current_chunk + " " + item) > config.max_chunk_size:
                    if len(current_chunk) >= config.min_chunk_size:
                        chunks.append(current_chunk.strip())
                    current_chunk = item
                else:
                    current_chunk = (current_chunk + " " + item).strip()
            
            # Dernier chunk
            if current_chunk and len(current_chunk) >= config.min_chunk_size:
                chunks.append(current_chunk.strip())
            
            return chunks if chunks else items
            
        except Exception as e:
            logger.error(f"Erreur regroupement: {e}")
            return items
    
    def _enrich_chunks(
        self, 
        chunks: List[str], 
        metadata: Optional[Dict[str, Any]], 
        config: ChunkConfig
    ) -> List[Dict[str, Any]]:
        """Enrichit les chunks avec des métadonnées."""
        try:
            enriched_chunks = []
            
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "chunk_index": i,
                    "chunk_count": len(chunks),
                    "chunk_size": len(chunk),
                    "chunking_strategy": config.strategy.value,
                    "overlap_size": config.overlap_size
                }
                
                # Ajout des métadonnées du document parent
                if metadata:
                    chunk_metadata.update(metadata)
                
                # Analyse basique du chunk
                chunk_metadata.update(self._analyze_chunk(chunk))
                
                enriched_chunks.append({
                    "text": chunk,
                    "metadata": chunk_metadata
                })
            
            return enriched_chunks
            
        except Exception as e:
            logger.error(f"Erreur enrichissement chunks: {e}")
            return [{"text": chunk, "metadata": metadata or {}} for chunk in chunks]
    
    def _analyze_chunk(self, chunk: str) -> Dict[str, Any]:
        """Analyse basique d'un chunk."""
        try:
            return {
                "word_count": len(chunk.split()),
                "sentence_count": len(re.findall(r'[.!?]+', chunk)),
                "has_numbers": bool(re.search(r'\d+', chunk)),
                "has_dates": bool(re.search(r'\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}', chunk)),
                "has_amounts": bool(re.search(r'\d+[,\.]?\d*\s*€', chunk)),
                "language_hint": "fr" if re.search(r'\b(le|la|les|un|une|des|du|de|à|et)\b', chunk.lower()) else "unknown"
            }
        except Exception as e:
            logger.warning(f"Erreur analyse chunk: {e}")
            return {}
    
    def _is_table_row(self, line: str) -> bool:
        """Détecte si une ligne fait partie d'un tableau."""
        return (
            '|' in line or 
            '\t' in line or
            len(re.findall(r'\s{3,}', line)) >= 2
        )
    
    def _is_list_item(self, line: str) -> bool:
        """Détecte si une ligne est un élément de liste."""
        return bool(re.match(r'^\s*[-*•]\s+', line) or re.match(r'^\s*\d+[\.\)]\s+', line))
    
    def _is_header(self, line: str) -> bool:
        """Détecte si une ligne est un titre."""
        return (
            line.isupper() and len(line) > 5 or
            bool(re.match(r'^[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏ][^.]*:$', line)) or
            bool(re.match(r'^(ARTICLE|Article|Chapitre|CHAPITRE)\s+\d+', line))
        )

# Instance globale du chunker
text_chunker = TextChunker()