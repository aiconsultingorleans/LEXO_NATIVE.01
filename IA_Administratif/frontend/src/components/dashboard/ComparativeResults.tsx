'use client';

import { useState, useEffect } from 'react';
import { usePipelineStore } from '@/stores/pipelineStore';
import { useToast } from '@/contexts/ToastContext';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { 
  FileText,
  Bot,
  Lightbulb,
  Clock,
  Target,
  Tag,
  User,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertCircle,
  CheckCircle,
  XCircle,
  RefreshCw,
  Eye,
  EyeOff,
  ArrowRight
} from 'lucide-react';

interface PipelineResult {
  pipeline: 'mistral' | 'donut';
  category: string;
  confidence: number;
  emitter?: string;
  processingTime: number;
  entities?: Array<{ type: string; value: string; confidence: number }>;
  summary?: string;
  errors?: string[];
  organizationPath?: string;
}

interface DocumentComparison {
  documentId: string;
  filename: string;
  uploadedAt: string;
  mistralResult?: PipelineResult;
  donutResult?: PipelineResult;
  goldStandard?: {
    category: string;
    emitter?: string;
    notes?: string;
  };
}

interface ComparativeResultsProps {
  className?: string;
  documentId?: string; // Si spécifié, affiche seulement ce document
  maxResults?: number;
  showGoldStandard?: boolean;
}

export function ComparativeResults({ 
  className, 
  documentId,
  maxResults = 10,
  showGoldStandard = false 
}: ComparativeResultsProps) {
  const [comparisons, setComparisons] = useState<DocumentComparison[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedDoc, setSelectedDoc] = useState<DocumentComparison | null>(null);
  const [showDetails, setShowDetails] = useState<Record<string, boolean>>({});
  const { activePipeline } = usePipelineStore();
  const toast = useToast();

  const fetchComparisons = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Token d\'authentification manquant');
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const endpoint = documentId 
        ? `${apiUrl}/api/v1/documents/${documentId}/comparison`
        : `${apiUrl}/api/v1/documents/comparisons?limit=${maxResults}`;
        
      // Utiliser directement les données mockées pour éviter les erreurs d'API
      // TODO: Réactiver l'appel API quand les endpoints seront implémentés
      
      if (true) { // Forcer l'utilisation des données mockées
          // Endpoint pas encore implémenté - données mockées
          const mockComparisons: DocumentComparison[] = [
            {
              documentId: 'doc-1',
              filename: 'facture_edf_janvier_2025.pdf',
              uploadedAt: new Date().toISOString(),
              mistralResult: {
                pipeline: 'mistral',
                category: 'factures',
                confidence: 0.87,
                emitter: 'EDF',
                processingTime: 8.2,
                entities: [
                  { type: 'AMOUNT', value: '145.67€', confidence: 0.92 },
                  { type: 'DATE', value: '15/01/2025', confidence: 0.89 },
                ],
                summary: 'Facture EDF pour la période de janvier 2025',
                organizationPath: '/OCR/factures/EDF/'
              },
              donutResult: {
                pipeline: 'donut',
                category: 'factures',
                confidence: 0.94,
                emitter: 'EDF',
                processingTime: 6.8,
                entities: [
                  { type: 'AMOUNT', value: '145.67€', confidence: 0.96 },
                  { type: 'DATE', value: '15/01/2025', confidence: 0.94 },
                  { type: 'ACCOUNT', value: '12345678901', confidence: 0.91 },
                ],
                summary: 'Facture électricité EDF période janvier 2025 - Montant 145.67€',
                organizationPath: '/OCR/factures/EDF/'
              },
              goldStandard: {
                category: 'factures',
                emitter: 'EDF',
                notes: 'Classification correcte pour les deux pipelines'
              }
            },
            {
              documentId: 'doc-2',
              filename: 'attestation_cpam_2025.pdf',
              uploadedAt: new Date(Date.now() - 3600000).toISOString(),
              mistralResult: {
                pipeline: 'mistral',
                category: 'attestations',
                confidence: 0.82,
                emitter: 'CPAM',
                processingTime: 9.1,
                entities: [
                  { type: 'PERSON', value: 'Jean Dupont', confidence: 0.88 },
                ],
                summary: 'Attestation CPAM',
                organizationPath: '/OCR/attestations/CPAM/'
              },
              donutResult: {
                pipeline: 'donut',
                category: 'attestations',
                confidence: 0.91,
                emitter: 'CPAM',
                processingTime: 7.3,
                entities: [
                  { type: 'PERSON', value: 'Jean Dupont', confidence: 0.93 },
                  { type: 'NUMBER', value: '1234567890123', confidence: 0.89 },
                ],
                summary: 'Attestation de droits CPAM pour Jean Dupont',
                organizationPath: '/OCR/attestations/CPAM/'
              },
              goldStandard: {
                category: 'attestations',
                emitter: 'CPAM',
                notes: 'DONUT détecte plus d\'entités'
              }
            },
          ];
          // Filtrer par documentId si spécifié
          const filteredComparisons = documentId 
            ? mockComparisons.filter(comp => comp.documentId === documentId)
            : mockComparisons.slice(0, maxResults);
          
          setComparisons(filteredComparisons);
          return;
        }
        
        // Ce code ne sera jamais atteint mais laissé pour référence future
        const errorData = await response.json().catch(() => ({ detail: 'Erreur de récupération' }));
        throw new Error(errorData.detail || 'Impossible de récupérer les comparaisons');

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur inconnue';
      setError(errorMessage);
      console.error('Erreur lors de la récupération des comparaisons:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComparisons();
  }, [documentId, maxResults]);

  const toggleDetails = (docId: string) => {
    setShowDetails(prev => ({
      ...prev,
      [docId]: !prev[docId]
    }));
  };

  const getComparisonIcon = (mistral?: PipelineResult, donut?: PipelineResult) => {
    if (!mistral || !donut) return <Minus className="h-4 w-4 text-gray-400" />;
    
    if (donut.confidence > mistral.confidence) {
      return <TrendingUp className="h-4 w-4 text-green-500" />;
    } else if (donut.confidence < mistral.confidence) {
      return <TrendingDown className="h-4 w-4 text-red-500" />;
    }
    return <Minus className="h-4 w-4 text-gray-400" />;
  };

  const getAccuracyStatus = (result: PipelineResult, goldStandard?: DocumentComparison['goldStandard']) => {
    if (!goldStandard) return null;
    
    const categoryMatch = result.category === goldStandard.category;
    const emitterMatch = result.emitter === goldStandard.emitter;
    
    if (categoryMatch && emitterMatch) {
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    } else if (categoryMatch) {
      return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
    return <XCircle className="h-4 w-4 text-red-500" />;
  };

  const renderPipelineResult = (result: PipelineResult | undefined, comparison: DocumentComparison) => {
    if (!result) {
      return (
        <div className="text-center py-8 text-gray-400">
          <Bot className="h-6 w-6 mx-auto mb-2" />
          <p className="text-sm">Pas de résultat</p>
        </div>
      );
    }

    const isActive = result.pipeline === activePipeline;

    return (
      <div className={cn(
        'bg-card-background border rounded-lg p-4 transition-all duration-200',
        {
          'border-blue-600/50 bg-blue-900/20': result.pipeline === 'mistral' && isActive,
          'border-purple-600/50 bg-purple-900/20': result.pipeline === 'donut' && isActive,
          'border-card-border': !isActive,
        }
      )}>
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            {result.pipeline === 'donut' ? (
              <Lightbulb className="h-5 w-5 text-purple-400" />
            ) : (
              <Bot className="h-5 w-5 text-blue-400" />
            )}
            <span className="font-medium text-sm text-foreground">
              {result.pipeline === 'donut' ? 'DONUT' : 'Mistral MLX'}
            </span>
            {isActive && (
              <span className="bg-primary text-white text-xs px-2 py-0.5 rounded-full">
                Actif
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            {showGoldStandard && getAccuracyStatus(result, comparison.goldStandard)}
            <span className={cn(
              'text-xs font-medium px-2 py-1 rounded border',
              {
                'bg-green-900/20 text-green-300 border-green-800/30': result.confidence >= 0.9,
                'bg-yellow-900/20 text-yellow-300 border-yellow-800/30': result.confidence >= 0.7,
                'bg-red-900/20 text-red-300 border-red-800/30': result.confidence < 0.7,
              }
            )}>
              {(result.confidence * 100).toFixed(1)}%
            </span>
          </div>
        </div>

        {/* Main Results */}
        <div className="space-y-2 mb-3">
          <div className="flex items-center space-x-2">
            <Tag className="h-4 w-4 text-foreground-muted" />
            <span className="text-sm text-foreground">
              <span className="font-medium">Catégorie:</span> {result.category}
            </span>
          </div>
          
          {result.emitter && (
            <div className="flex items-center space-x-2">
              <User className="h-4 w-4 text-foreground-muted" />
              <span className="text-sm text-foreground">
                <span className="font-medium">Émetteur:</span> {result.emitter}
              </span>
            </div>
          )}
          
          <div className="flex items-center space-x-2">
            <Clock className="h-4 w-4 text-foreground-muted" />
            <span className="text-sm text-foreground">
              <span className="font-medium">Temps:</span> {result.processingTime}s
            </span>
          </div>

          {result.organizationPath && (
            <div className="flex items-center space-x-2">
              <ArrowRight className="h-4 w-4 text-foreground-muted" />
              <span className="text-xs text-foreground-secondary font-mono">
                {result.organizationPath}
              </span>
            </div>
          )}
        </div>

        {/* Summary */}
        {result.summary && (
          <div className="bg-background-secondary p-3 rounded text-sm text-foreground-secondary mb-3 border border-card-border">
            {result.summary}
          </div>
        )}

        {/* Details Toggle */}
        <div className="border-t border-card-border pt-3">
          <button
            onClick={() => toggleDetails(`${comparison.documentId}-${result.pipeline}`)}
            className="flex items-center space-x-2 text-sm text-foreground-secondary hover:text-foreground transition-colors"
          >
            {showDetails[`${comparison.documentId}-${result.pipeline}`] ? (
              <EyeOff className="h-4 w-4" />
            ) : (
              <Eye className="h-4 w-4" />
            )}
            <span>
              {showDetails[`${comparison.documentId}-${result.pipeline}`] ? 'Masquer' : 'Voir'} détails
            </span>
          </button>

          {/* Extended Details */}
          {showDetails[`${comparison.documentId}-${result.pipeline}`] && (
            <div className="mt-3 space-y-2">
              {/* Entities */}
              {result.entities && result.entities.length > 0 && (
                <div>
                  <h5 className="text-xs font-medium text-foreground mb-2">Entités détectées:</h5>
                  <div className="space-y-1">
                    {result.entities.map((entity, idx) => (
                      <div key={idx} className="flex items-center justify-between text-xs">
                        <span className="text-foreground-secondary">{entity.type}: {entity.value}</span>
                        <span className="text-foreground-muted">{(entity.confidence * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Errors */}
              {result.errors && result.errors.length > 0 && (
                <div>
                  <h5 className="text-xs font-medium text-red-400 mb-2">Erreurs:</h5>
                  <div className="space-y-1">
                    {result.errors.map((error, idx) => (
                      <div key={idx} className="text-xs text-red-300">
                        • {error}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    );
  };

  if (error) {
    return (
      <div className={cn('bg-card-background p-6 rounded-xl border border-card-border', className)}>
        <div className="text-center py-8">
          <AlertCircle className="h-8 w-8 text-red-500 mx-auto mb-4" />
          <p className="text-sm text-red-600 mb-4">{error}</p>
          <Button variant="outline" onClick={fetchComparisons}>
            Réessayer
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-card-background rounded-xl border border-card-border', className)}>
      {/* Header */}
      <div className="p-6 border-b border-card-border">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <Target className="w-5 h-5 text-primary" />
            Résultats comparatifs
            {documentId && <span className="text-sm text-foreground-muted">- Document spécifique</span>}
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={fetchComparisons}
            disabled={loading}
          >
            <RefreshCw className={cn('h-4 w-4', { 'animate-spin': loading })} />
          </Button>
        </div>
      </div>

      {/* Results */}
      <div className="p-6">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-6 w-6 animate-spin text-foreground-muted mr-2" />
            <span className="text-foreground-secondary">Chargement des comparaisons...</span>
          </div>
        ) : comparisons.length > 0 ? (
          <div className="space-y-6">
            {comparisons.map((comparison) => (
              <div key={comparison.documentId} className="border border-card-border rounded-lg p-4">
                {/* Document Header */}
                <div className="flex items-center justify-between mb-4 pb-2 border-b border-card-border">
                  <div className="flex items-center space-x-3">
                    <FileText className="h-5 w-5 text-foreground-muted" />
                    <div>
                      <h4 className="font-medium text-sm text-foreground">{comparison.filename}</h4>
                      <p className="text-xs text-foreground-muted">
                        {new Date(comparison.uploadedAt).toLocaleString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    {getComparisonIcon(comparison.mistralResult, comparison.donutResult)}
                    {showGoldStandard && comparison.goldStandard && (
                      <span className="bg-yellow-900/20 text-yellow-300 text-xs px-2 py-1 rounded border border-yellow-800/30">
                        Gold Standard
                      </span>
                    )}
                  </div>
                </div>

                {/* Side by Side Results */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {renderPipelineResult(comparison.mistralResult, comparison)}
                  {renderPipelineResult(comparison.donutResult, comparison)}
                </div>

                {/* Gold Standard */}
                {showGoldStandard && comparison.goldStandard && (
                  <div className="mt-4 bg-yellow-900/20 border border-yellow-800/30 rounded-lg p-3">
                    <h5 className="text-sm font-medium text-yellow-300 mb-2">Standard de référence:</h5>
                    <div className="text-sm text-yellow-400">
                      <p>Catégorie: {comparison.goldStandard.category}</p>
                      {comparison.goldStandard.emitter && (
                        <p>Émetteur: {comparison.goldStandard.emitter}</p>
                      )}
                      {comparison.goldStandard.notes && (
                        <p className="mt-1 italic">{comparison.goldStandard.notes}</p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-12 text-foreground-secondary">
            <Target className="h-8 w-8 text-foreground-muted mx-auto mb-2" />
            <p className="text-sm">Aucune comparaison disponible</p>
            <p className="text-xs text-foreground-muted mt-1">
              {documentId 
                ? 'Ce document n\'a pas encore été traité par les deux pipelines'
                : 'Uploadez des documents pour voir les comparaisons'
              }
            </p>
          </div>
        )}
      </div>
    </div>
  );
}