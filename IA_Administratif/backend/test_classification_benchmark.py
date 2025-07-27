#!/usr/bin/env python3
"""
Script de benchmark pour la classification automatique de documents - Étape 1
Mesure la précision du système actuel et valide les corrections Mistral MLX
"""

import os
import sys
import json
import time
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, Counter
import statistics
import traceback

# Ajouter le répertoire racine au path Python
sys.path.append(str(Path(__file__).parent))

# Imports spécifiques au projet
from services.document_classifier import get_document_classifier, DocumentCategory
from ocr.hybrid_ocr import HybridOCREngine
import requests

# Configuration logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("classification_benchmark")

# Configuration
MISTRAL_SERVICE_URL = "http://localhost:8004"
BACKEND_SERVICE_URL = "http://localhost:8000"
OCR_DOCS_PATH = "/Users/stephaneansel/Documents/LEXO_v1/OCR"
RESULTS_DIR = Path(__file__).parent / "benchmark_results"

@dataclass
class BenchmarkResult:
    """Résultat de test d'un document"""
    filename: str
    expected_category: Optional[str] = None
    predicted_category: str = ""
    confidence: float = 0.0
    processing_time: float = 0.0
    ocr_success: bool = False
    mistral_success: bool = False
    rules_applied: List[str] = field(default_factory=list)
    error_message: str = ""
    raw_text: str = ""
    # Nouvelles métriques de fusion
    rules_category: str = ""
    rules_confidence: float = 0.0
    mistral_category: str = ""
    mistral_confidence: float = 0.0
    fusion_decision: str = ""  # "rules_only", "mistral_override", "agreement_boost"

@dataclass
class BenchmarkStats:
    """Statistiques globales du benchmark"""
    total_documents: int = 0
    successful_classifications: int = 0
    ocr_success_rate: float = 0.0
    mistral_success_rate: float = 0.0
    accuracy: float = 0.0
    average_confidence: float = 0.0
    average_processing_time: float = 0.0
    category_stats: Dict[str, Dict[str, int]] = field(default_factory=dict)
    error_types: Dict[str, int] = field(default_factory=dict)
    # Nouvelles statistiques de fusion
    fusion_stats: Dict[str, int] = field(default_factory=dict)
    rules_vs_mistral_agreement: float = 0.0
    mistral_override_rate: float = 0.0


class ClassificationBenchmark:
    """Classe principale pour le benchmark de classification"""
    
    def __init__(self):
        self.classifier = get_document_classifier()
        self.ocr_processor = None
        self.results: List[BenchmarkResult] = []
        
        # Créer le répertoire de résultats
        RESULTS_DIR.mkdir(exist_ok=True)
        
        # Mapping manuel des catégories basé sur le nom de dossier
        self.folder_to_category = {
            'factures': 'factures',
            'rib': 'rib', 
            'contrats': 'contrats',
            'attestations': 'attestations',
            'courriers': 'courriers',
            'rapports': 'rapports',
            'cartes_transport': 'attestations',  # Les cartes de transport sont des attestations
            'documents_personnels': 'non_classes',
            'non_classes': 'non_classes',
            'en_attente': 'non_classes'
        }
        
        # Mapping Mistral vers nos catégories (identique à production)
        self.mistral_to_our_categories = {
            'factures': 'factures',
            'facture': 'factures',
            'rib': 'rib', 
            'contrats': 'contrats',
            'contrat': 'contrats',
            'attestations': 'attestations',
            'attestation': 'attestations',
            'courriers': 'courriers',
            'courrier': 'courriers',
            'impots': 'impots',
            'impôts': 'impots',
            'sante': 'sante',
            'santé': 'sante',
            'emploi': 'emploi',
            'rapport': 'courriers',  # Les rapports sont classés comme courriers
            'autre': 'non_classes',
            'non_classes': 'non_classes'
        }
    
    def map_mistral_to_categories(self, mistral_type: str) -> str:
        """Mapper types Mistral vers nos 9 catégories (identique production)"""
        if not mistral_type:
            return 'non_classes'
        return self.mistral_to_our_categories.get(mistral_type.lower(), 'non_classes')
    
    async def initialize_services(self):
        """Initialise les services nécessaires"""
        logger.info("Initialisation des services...")
        
        # Vérifier que Mistral MLX est actif
        try:
            response = requests.get(f"{MISTRAL_SERVICE_URL}/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Service Mistral MLX actif")
            else:
                logger.error(f"❌ Service Mistral MLX erreur: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Service Mistral MLX inaccessible: {e}")
            return False
        
        # Vérifier le backend
        try:
            response = requests.get(f"{BACKEND_SERVICE_URL}/api/v1/health", timeout=5)
            if response.status_code == 200:
                logger.info("✅ Backend FastAPI actif")
            else:
                logger.error(f"❌ Backend FastAPI erreur: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Backend FastAPI inaccessible: {e}")
            return False
        
        # Initialiser l'OCR
        try:
            self.ocr_processor = HybridOCREngine()
            logger.info("✅ OCR Engine initialisé")
        except Exception as e:
            logger.error(f"❌ Erreur initialisation OCR: {e}")
            return False
        
        return True
    
    def discover_test_documents(self) -> List[Tuple[str, str, str]]:
        """Découvre les documents de test dans le dossier OCR"""
        documents = []
        ocr_path = Path(OCR_DOCS_PATH)
        
        if not ocr_path.exists():
            logger.error(f"Dossier OCR introuvable: {OCR_DOCS_PATH}")
            return documents
        
        # Parcourir tous les sous-dossiers
        for folder in ocr_path.iterdir():
            if folder.is_dir() and folder.name in self.folder_to_category:
                expected_category = self.folder_to_category[folder.name]
                
                # Chercher les fichiers PDF et images
                for file_path in folder.rglob("*"):
                    if file_path.is_file() and file_path.suffix.lower() in ['.pdf', '.png', '.jpg', '.jpeg', '.tiff']:
                        documents.append((
                            str(file_path),
                            file_path.name,
                            expected_category
                        ))
        
        logger.info(f"📄 {len(documents)} documents découverts pour le test")
        
        # Afficher la répartition par catégorie
        category_counts = Counter(doc[2] for doc in documents)
        for category, count in category_counts.items():
            logger.info(f"  - {category}: {count} documents")
        
        return documents[:50]  # Limiter à 50 pour les tests initiaux
    
    async def test_document_classification(self, file_path: str, filename: str, expected_category: str) -> BenchmarkResult:
        """Teste la classification d'un document avec fusion règles/Mistral (identique production)"""
        start_time = time.time()
        result = BenchmarkResult(filename=filename, expected_category=expected_category)
        
        try:
            logger.info(f"🔍 Test: {filename}")
            
            # Étape 1: OCR
            ocr_start = time.time()
            try:
                ocr_result = self.ocr_processor.extract_text(file_path)
                result.ocr_success = True
                result.raw_text = ocr_result.text[:500] if hasattr(ocr_result, 'text') else str(ocr_result)[:500]
                logger.debug(f"OCR réussi: {len(result.raw_text)} caractères")
            except Exception as e:
                logger.error(f"❌ OCR échoué pour {filename}: {e}")
                result.error_message = f"OCR: {str(e)}"
                return result
            
            # Étape 2: Classification par règles
            rules_category = None
            rules_confidence = 0.0
            try:
                classification = self.classifier.classify_document(
                    filename=filename,
                    ocr_text=result.raw_text,
                    entities=[]
                )
                
                rules_category = classification.category
                rules_confidence = classification.confidence
                result.rules_applied = classification.matched_rules
                
                logger.info(f"  Règles: {rules_category} (conf: {rules_confidence:.2f})")
                
            except Exception as e:
                logger.error(f"❌ Classification règles échouée pour {filename}: {e}")
                result.error_message = f"Règles: {str(e)}"
                return result
            
            # Étape 3: Analyse Mistral MLX
            mistral_category = None
            mistral_confidence = 0.0
            try:
                mistral_response = requests.post(
                    f"{MISTRAL_SERVICE_URL}/analyze",
                    json={
                        "text": result.raw_text,
                        "analysis_types": ["classification", "key_extraction"]
                    },
                    timeout=30
                )
                
                if mistral_response.status_code == 200:
                    mistral_data = mistral_response.json()
                    if mistral_data.get('success'):
                        result.mistral_success = True
                        mistral_result = mistral_data['result']
                        mistral_raw_type = mistral_result.get('document_type', '')
                        mistral_category = self.map_mistral_to_categories(mistral_raw_type)
                        mistral_confidence = mistral_result.get('confidence', 0)
                        logger.info(f"  Mistral: {mistral_raw_type} -> {mistral_category} (conf: {mistral_confidence:.2f})")
                    else:
                        logger.warning(f"⚠️ Mistral échec: {mistral_data.get('error', 'Unknown')}")
                else:
                    logger.warning(f"⚠️ Mistral HTTP {mistral_response.status_code}")
                    
            except Exception as e:
                logger.warning(f"⚠️ Mistral inaccessible pour {filename}: {e}")
            
            # Étape 4: FUSION INTELLIGENTE (identique production)
            final_category = rules_category
            final_confidence = rules_confidence
            fusion_decision = "rules_only"
            
            # Capturer les métriques de fusion
            result.rules_category = rules_category
            result.rules_confidence = rules_confidence
            result.mistral_category = mistral_category or ""
            result.mistral_confidence = mistral_confidence
            
            if mistral_category and mistral_confidence > 0:
                # Logique de fusion identique à production (documents.py lignes 299-306)
                if mistral_confidence > 0.8 and mistral_category != final_category:
                    logger.info(f"🔄 Fusion: {final_category} → {mistral_category} (Mistral prioritaire: {mistral_confidence:.2f})")
                    final_category = mistral_category
                    final_confidence = min(0.95, (final_confidence + mistral_confidence) / 2)
                    fusion_decision = "mistral_override"
                elif mistral_category == final_category:
                    # Boost confiance si accord
                    final_confidence = min(0.98, final_confidence * 1.2)
                    logger.info(f"✅ Fusion: Accord règles/Mistral sur {final_category} (boost conf: {final_confidence:.2f})")
                    fusion_decision = "agreement_boost"
                else:
                    logger.info(f"🤝 Fusion: Règles prioritaires {final_category} vs Mistral {mistral_category} (conf faible: {mistral_confidence:.2f})")
                    fusion_decision = "rules_priority"
            else:
                logger.info(f"📋 Fusion: Règles seules {final_category} (Mistral indisponible)")
                fusion_decision = "rules_only"
            
            # Résultat final
            result.predicted_category = final_category
            result.confidence = final_confidence
            result.fusion_decision = fusion_decision
            
            # Calculer l'exactitude
            result.processing_time = time.time() - start_time
            
            if result.predicted_category == expected_category:
                logger.info(f"  ✅ CORRECT: {expected_category}")
            else:
                logger.warning(f"  ❌ FAUX: attendu {expected_category}, obtenu {result.predicted_category}")
            
        except Exception as e:
            logger.error(f"❌ Erreur générale pour {filename}: {e}")
            result.error_message = f"Général: {str(e)}"
            result.processing_time = time.time() - start_time
        
        return result
    
    def calculate_statistics(self) -> BenchmarkStats:
        """Calcule les statistiques du benchmark"""
        stats = BenchmarkStats()
        
        if not self.results:
            return stats
        
        stats.total_documents = len(self.results)
        
        # Compter les succès
        successful_results = [r for r in self.results if r.predicted_category and not r.error_message]
        stats.successful_classifications = len(successful_results)
        
        # Taux de succès OCR et Mistral
        stats.ocr_success_rate = sum(1 for r in self.results if r.ocr_success) / stats.total_documents * 100
        stats.mistral_success_rate = sum(1 for r in self.results if r.mistral_success) / stats.total_documents * 100
        
        if successful_results:
            # Précision globale
            correct_predictions = sum(1 for r in successful_results if r.predicted_category == r.expected_category)
            stats.accuracy = correct_predictions / len(successful_results) * 100
            
            # Confiance et temps moyens
            stats.average_confidence = statistics.mean(r.confidence for r in successful_results)
            stats.average_processing_time = statistics.mean(r.processing_time for r in successful_results)
            
            # Statistiques par catégorie
            for category in set(r.expected_category for r in self.results if r.expected_category):
                category_results = [r for r in successful_results if r.expected_category == category]
                if category_results:
                    correct = sum(1 for r in category_results if r.predicted_category == r.expected_category)
                    stats.category_stats[category] = {
                        'total': len(category_results),
                        'correct': correct,
                        'accuracy': correct / len(category_results) * 100,
                        'avg_confidence': statistics.mean(r.confidence for r in category_results)
                    }
        
        # Types d'erreurs
        error_counter = Counter()
        for result in self.results:
            if result.error_message:
                error_type = result.error_message.split(':')[0]  # Prendre le préfixe avant ':'
                error_counter[error_type] += 1
        stats.error_types = dict(error_counter)
        
        # Statistiques de fusion
        fusion_counter = Counter()
        agreement_count = 0
        mistral_override_count = 0
        total_with_mistral = 0
        
        for result in successful_results:
            if hasattr(result, 'fusion_decision') and result.fusion_decision:
                fusion_counter[result.fusion_decision] += 1
                
                if result.mistral_category:  # Mistral était disponible
                    total_with_mistral += 1
                    if result.rules_category == result.mistral_category:
                        agreement_count += 1
                    if result.fusion_decision == "mistral_override":
                        mistral_override_count += 1
        
        stats.fusion_stats = dict(fusion_counter)
        if total_with_mistral > 0:
            stats.rules_vs_mistral_agreement = agreement_count / total_with_mistral * 100
            stats.mistral_override_rate = mistral_override_count / total_with_mistral * 100
        
        return stats
    
    def generate_report(self, stats: BenchmarkStats) -> str:
        """Génère un rapport détaillé"""
        report = []
        
        report.append("=" * 80)
        report.append("🎯 RAPPORT BENCHMARK CLASSIFICATION - FUSION RÈGLES/IA")
        report.append("=" * 80)
        report.append(f"📅 Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"📊 Documents testés: {stats.total_documents}")
        report.append("")
        
        # Résultats globaux
        report.append("📈 RÉSULTATS GLOBAUX")
        report.append("-" * 40)
        report.append(f"✅ Classifications réussies: {stats.successful_classifications}/{stats.total_documents} ({stats.successful_classifications/stats.total_documents*100:.1f}%)")
        report.append(f"🎯 Précision globale: {stats.accuracy:.1f}%")
        report.append(f"📊 Confiance moyenne: {stats.average_confidence:.2f}")
        report.append(f"⏱️ Temps moyen: {stats.average_processing_time:.2f}s")
        report.append("")
        
        # Taux de succès des composants
        report.append("🔧 TAUX DE SUCCÈS COMPOSANTS")
        report.append("-" * 40)
        report.append(f"🔍 OCR Success Rate: {stats.ocr_success_rate:.1f}%")
        report.append(f"🤖 Mistral MLX Success Rate: {stats.mistral_success_rate:.1f}%")
        report.append("")
        
        # Statistiques de fusion
        if stats.fusion_stats:
            report.append("🔗 STATISTIQUES DE FUSION RÈGLES/IA")
            report.append("-" * 40)
            for decision_type, count in stats.fusion_stats.items():
                report.append(f"{decision_type.replace('_', ' ').title()}: {count} documents")
            if stats.rules_vs_mistral_agreement > 0:
                report.append(f"Accord Règles/Mistral: {stats.rules_vs_mistral_agreement:.1f}%")
            if stats.mistral_override_rate > 0:
                report.append(f"Taux Override Mistral: {stats.mistral_override_rate:.1f}%")
            report.append("")
        
        # Précision par catégorie
        if stats.category_stats:
            report.append("📋 PRÉCISION PAR CATÉGORIE")
            report.append("-" * 40)
            for category, cat_stats in sorted(stats.category_stats.items()):
                report.append(f"{category.upper()}: {cat_stats['accuracy']:.1f}% ({cat_stats['correct']}/{cat_stats['total']}) - Conf: {cat_stats['avg_confidence']:.2f}")
            report.append("")
        
        # Erreurs
        if stats.error_types:
            report.append("❌ TYPES D'ERREURS")
            report.append("-" * 40)
            for error_type, count in sorted(stats.error_types.items(), key=lambda x: x[1], reverse=True):
                report.append(f"{error_type}: {count} occurrences")
            report.append("")
        
        # Objectifs Étape 1
        report.append("🎯 VALIDATION OBJECTIFS ÉTAPE 1")
        report.append("-" * 40)
        
        target_accuracy = 85.0
        target_time = 8.0
        target_crashes = 0
        
        if stats.accuracy >= target_accuracy:
            report.append(f"✅ Précision: {stats.accuracy:.1f}% >= {target_accuracy}% (OBJECTIF ATTEINT)")
        else:
            report.append(f"❌ Précision: {stats.accuracy:.1f}% < {target_accuracy}% (OBJECTIF NON ATTEINT)")
        
        if stats.average_processing_time <= target_time:
            report.append(f"✅ Performance: {stats.average_processing_time:.1f}s <= {target_time}s (OBJECTIF ATTEINT)")
        else:
            report.append(f"❌ Performance: {stats.average_processing_time:.1f}s > {target_time}s (OBJECTIF NON ATTEINT)")
        
        crashes = len([r for r in self.results if "crash" in r.error_message.lower() or "exception" in r.error_message.lower()])
        if crashes == target_crashes:
            report.append(f"✅ Robustesse: {crashes} crashes = {target_crashes} (OBJECTIF ATTEINT)")
        else:
            report.append(f"❌ Robustesse: {crashes} crashes > {target_crashes} (OBJECTIF NON ATTEINT)")
        
        # Recommandations
        report.append("")
        report.append("🔧 RECOMMANDATIONS POUR ÉTAPE 2")
        report.append("-" * 40)
        
        if stats.accuracy < 88:
            report.append("• Améliorer les prompts Mistral avec few-shot learning")
            report.append("• Enrichir les règles de classification françaises")
        
        if stats.mistral_success_rate < 95:
            report.append("• Stabiliser les réponses JSON de Mistral MLX")
            report.append("• Améliorer la gestion des timeouts")
        
        if stats.average_processing_time > 6:
            report.append("• Optimiser la performance des requêtes Mistral")
            report.append("• Implémenter du caching intelligent")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    async def run_benchmark(self, max_documents: int = 50) -> BenchmarkStats:
        """Execute le benchmark complet"""
        logger.info("🚀 Démarrage du benchmark de classification")
        
        # Initialiser les services
        if not await self.initialize_services():
            logger.error("❌ Échec initialisation des services")
            return BenchmarkStats()
        
        # Découvrir les documents
        documents = self.discover_test_documents()
        if not documents:
            logger.error("❌ Aucun document trouvé pour les tests")
            return BenchmarkStats()
        
        # Limiter le nombre de documents pour les tests
        documents = documents[:max_documents]
        logger.info(f"📋 Test de {len(documents)} documents")
        
        # Tester chaque document
        for i, (file_path, filename, expected_category) in enumerate(documents, 1):
            logger.info(f"\n[{i}/{len(documents)}] Processing: {filename}")
            
            try:
                result = await self.test_document_classification(file_path, filename, expected_category)
                self.results.append(result)
            except Exception as e:
                logger.error(f"❌ Erreur critique pour {filename}: {e}")
                error_result = BenchmarkResult(
                    filename=filename,
                    expected_category=expected_category,
                    error_message=f"Critique: {str(e)}"
                )
                self.results.append(error_result)
        
        # Calculer les statistiques
        stats = self.calculate_statistics()
        
        # Générer le rapport
        report = self.generate_report(stats)
        
        # Sauvegarder les résultats
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Rapport texte
        report_file = RESULTS_DIR / f"benchmark_report_{timestamp}.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Données JSON pour analyse
        results_file = RESULTS_DIR / f"benchmark_results_{timestamp}.json"
        results_data = {
            'timestamp': timestamp,
            'stats': {
                'total_documents': stats.total_documents,
                'successful_classifications': stats.successful_classifications,
                'accuracy': stats.accuracy,
                'average_confidence': stats.average_confidence,
                'average_processing_time': stats.average_processing_time,
                'ocr_success_rate': stats.ocr_success_rate,
                'mistral_success_rate': stats.mistral_success_rate,
                'category_stats': stats.category_stats,
                'error_types': stats.error_types,
                'fusion_stats': stats.fusion_stats,
                'rules_vs_mistral_agreement': stats.rules_vs_mistral_agreement,
                'mistral_override_rate': stats.mistral_override_rate
            },
            'detailed_results': [
                {
                    'filename': r.filename,
                    'expected_category': r.expected_category,
                    'predicted_category': r.predicted_category,
                    'confidence': r.confidence,
                    'processing_time': r.processing_time,
                    'ocr_success': r.ocr_success,
                    'mistral_success': r.mistral_success,
                    'error_message': r.error_message,
                    'rules_category': getattr(r, 'rules_category', ''),
                    'rules_confidence': getattr(r, 'rules_confidence', 0.0),
                    'mistral_category': getattr(r, 'mistral_category', ''),
                    'mistral_confidence': getattr(r, 'mistral_confidence', 0.0),
                    'fusion_decision': getattr(r, 'fusion_decision', '')
                }
                for r in self.results
            ]
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        # Afficher le rapport
        print("\n" + report)
        
        logger.info(f"📁 Rapport sauvegardé: {report_file}")
        logger.info(f"📁 Données JSON: {results_file}")
        
        return stats


async def main():
    """Point d'entrée principal"""
    benchmark = ClassificationBenchmark()
    
    try:
        stats = await benchmark.run_benchmark(max_documents=30)  # Test sur 30 documents
        
        # Résumé final
        print(f"\n🎯 RÉSUMÉ FINAL:")
        print(f"   Précision: {stats.accuracy:.1f}%")
        print(f"   Documents: {stats.successful_classifications}/{stats.total_documents}")
        print(f"   Temps moyen: {stats.average_processing_time:.1f}s")
        
        # Vérifier les objectifs Étape 1
        objectives_met = (
            stats.accuracy >= 85.0 and
            stats.average_processing_time <= 8.0 and
            len([r for r in benchmark.results if "crash" in r.error_message.lower()]) == 0
        )
        
        if objectives_met:
            print("✅ OBJECTIFS ÉTAPE 1 ATTEINTS - Prêt pour Étape 2")
            return 0
        else:
            print("❌ OBJECTIFS ÉTAPE 1 NON ATTEINTS - Corrections nécessaires")
            return 1
            
    except Exception as e:
        logger.error(f"❌ Erreur critique du benchmark: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("❌ Benchmark interrompu par l'utilisateur")
        sys.exit(1)