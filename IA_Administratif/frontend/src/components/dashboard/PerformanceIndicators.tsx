'use client';

import { useState, useEffect } from 'react';
import { usePipelineStore } from '@/stores/pipelineStore';
import { useToast } from '@/contexts/ToastContext';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts';
import { 
  TrendingUp,
  Clock,
  Target,
  Zap,
  RefreshCw,
  BarChart3,
  Timer,
  CheckCircle,
  AlertTriangle,
  Info
} from 'lucide-react';

interface PerformanceMetrics {
  pipeline: 'mistral' | 'donut';
  accuracy: number;
  processingTime: number; // en secondes
  documentsProcessed: number;
  categoryAccuracy: Record<string, number>;
  emitterDetection: number;
  errorRate: number;
  averageConfidence: number;
  lastUpdate: string;
}

interface ComparisonData {
  mistral: PerformanceMetrics;
  donut: PerformanceMetrics;
  timeSeriesData: Array<{
    timestamp: string;
    mistralAccuracy: number;
    donutAccuracy: number;
    mistralSpeed: number;
    donutSpeed: number;
  }>;
}

interface PerformanceIndicatorsProps {
  className?: string;
  showTimeRange?: boolean;
  autoRefresh?: boolean;
}

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff7300', '#00ff00'];

export function PerformanceIndicators({ 
  className, 
  showTimeRange = true,
  autoRefresh = true 
}: PerformanceIndicatorsProps) {
  const [comparisonData, setComparisonData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d'>('24h');
  const { activePipeline } = usePipelineStore();
  const toast = useToast();

  const fetchPerformanceData = async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Token d\'authentification manquant');
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/analytics/performance-comparison?range=${timeRange}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          // Endpoint pas encore implémenté - données mockées
          const mockData: ComparisonData = {
            mistral: {
              pipeline: 'mistral',
              accuracy: 89.7,
              processingTime: 8.2,
              documentsProcessed: 245,
              categoryAccuracy: {
                factures: 92.1,
                attestations: 87.3,
                rib: 94.6,
                contrats: 88.9,
                courriers: 85.2
              },
              emitterDetection: 84.5,
              errorRate: 2.3,
              averageConfidence: 87.8,
              lastUpdate: new Date().toISOString(),
            },
            donut: {
              pipeline: 'donut',
              accuracy: 92.4,
              processingTime: 6.8,
              documentsProcessed: 189,
              categoryAccuracy: {
                factures: 94.3,
                attestations: 91.2,
                rib: 96.1,
                contrats: 90.7,
                courriers: 88.9,
                carte_grise: 95.2,
                carte_vitale: 93.8
              },
              emitterDetection: 91.3,
              errorRate: 1.8,
              averageConfidence: 90.8,
              lastUpdate: new Date().toISOString(),
            },
            timeSeriesData: [
              { timestamp: '00:00', mistralAccuracy: 88.5, donutAccuracy: 91.2, mistralSpeed: 8.5, donutSpeed: 7.1 },
              { timestamp: '04:00', mistralAccuracy: 89.1, donutAccuracy: 92.0, mistralSpeed: 8.3, donutSpeed: 6.9 },
              { timestamp: '08:00', mistralAccuracy: 89.8, donutAccuracy: 92.6, mistralSpeed: 8.1, donutSpeed: 6.7 },
              { timestamp: '12:00', mistralAccuracy: 90.2, donutAccuracy: 93.1, mistralSpeed: 8.0, donutSpeed: 6.8 },
              { timestamp: '16:00', mistralAccuracy: 89.9, donutAccuracy: 92.8, mistralSpeed: 8.2, donutSpeed: 6.9 },
              { timestamp: '20:00', mistralAccuracy: 89.7, donutAccuracy: 92.4, mistralSpeed: 8.2, donutSpeed: 6.8 },
            ],
          };
          setComparisonData(mockData);
          return;
        }
        
        const errorData = await response.json().catch(() => ({ detail: 'Erreur de récupération' }));
        throw new Error(errorData.detail || 'Impossible de récupérer les métriques');
      }

      const data = await response.json();
      setComparisonData(data);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur inconnue';
      setError(errorMessage);
      console.error('Erreur lors de la récupération des métriques:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPerformanceData();
    
    if (autoRefresh) {
      const interval = setInterval(fetchPerformanceData, 60000); // Refresh toutes les minutes
      return () => clearInterval(interval);
    }
  }, [timeRange, autoRefresh]);

  const handleRefresh = async () => {
    await fetchPerformanceData();
    toast.success('Métriques mises à jour', 'Données de performance actualisées');
  };

  const getComparisonBars = () => {
    if (!comparisonData) return [];
    
    return [
      {
        name: 'Précision',
        mistral: comparisonData.mistral.accuracy,
        donut: comparisonData.donut.accuracy,
        unit: '%'
      },
      {
        name: 'Vitesse',
        mistral: Math.round((1 / comparisonData.mistral.processingTime) * 100) / 100,
        donut: Math.round((1 / comparisonData.donut.processingTime) * 100) / 100,
        unit: 'doc/s'
      },
      {
        name: 'Détection émetteur',
        mistral: comparisonData.mistral.emitterDetection,
        donut: comparisonData.donut.emitterDetection,
        unit: '%'
      },
      {
        name: 'Confiance',
        mistral: comparisonData.mistral.averageConfidence,
        donut: comparisonData.donut.averageConfidence,
        unit: '%'
      }
    ];
  };

  const getCategoryData = () => {
    if (!comparisonData) return [];
    
    const allCategories = new Set([
      ...Object.keys(comparisonData.mistral.categoryAccuracy),
      ...Object.keys(comparisonData.donut.categoryAccuracy)
    ]);
    
    return Array.from(allCategories).map(category => ({
      name: category,
      mistral: comparisonData.mistral.categoryAccuracy[category] || 0,
      donut: comparisonData.donut.categoryAccuracy[category] || 0,
    }));
  };

  const getWinnerMetric = (metric: 'accuracy' | 'speed' | 'emitterDetection') => {
    if (!comparisonData) return null;
    
    const mistralValue = metric === 'speed' 
      ? 1 / comparisonData.mistral.processingTime 
      : comparisonData.mistral[metric];
    const donutValue = metric === 'speed' 
      ? 1 / comparisonData.donut.processingTime 
      : comparisonData.donut[metric];
    
    return donutValue > mistralValue ? 'donut' : 'mistral';
  };

  if (error) {
    return (
      <div className={cn('bg-card-background p-6 rounded-xl border border-card-border', className)}>
        <div className="text-center py-8">
          <AlertTriangle className="h-8 w-8 text-red-500 mx-auto mb-4" />
          <p className="text-sm text-red-600 mb-4">{error}</p>
          <Button variant="outline" onClick={handleRefresh}>
            Réessayer
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-card-background rounded-xl border border-card-border', className)}>
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            Performance Comparative
          </h3>
          <div className="flex items-center space-x-2">
            {showTimeRange && (
              <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
                {(['1h', '24h', '7d'] as const).map((range) => (
                  <button
                    key={range}
                    onClick={() => setTimeRange(range)}
                    className={cn(
                      'px-3 py-1 text-xs font-medium rounded transition-all duration-150',
                      {
                        'bg-white text-primary shadow-sm': timeRange === range,
                        'text-gray-600 hover:text-gray-800': timeRange !== range,
                      }
                    )}
                  >
                    {range}
                  </button>
                ))}
              </div>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleRefresh}
              disabled={loading}
            >
              <RefreshCw className={cn('h-4 w-4', { 'animate-spin': loading })} />
            </Button>
          </div>
        </div>

        {/* Pipeline Status */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center space-x-2">
            <div className={cn(
              'w-2 h-2 rounded-full',
              activePipeline === 'donut' ? 'bg-purple-500' : 'bg-blue-500'
            )}></div>
            <span className="text-gray-600">
              Pipeline actif: {activePipeline === 'donut' ? 'DONUT' : 'Mistral MLX'}
            </span>
          </div>
          {comparisonData && (
            <span className="text-gray-500">
              {new Date(comparisonData[activePipeline].lastUpdate).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>

      {loading && !comparisonData ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-gray-400 mr-2" />
          <span className="text-gray-500">Chargement des métriques...</span>
        </div>
      ) : comparisonData ? (
        <div className="p-6 space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-blue-50 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <Target className="h-5 w-5 text-blue-600" />
                {getWinnerMetric('accuracy') === 'donut' && (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                )}
              </div>
              <div className="text-lg font-semibold text-blue-900">
                {comparisonData[activePipeline].accuracy}%
              </div>
              <div className="text-xs text-blue-600">Précision globale</div>
            </div>

            <div className="bg-green-50 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <Timer className="h-5 w-5 text-green-600" />
                {getWinnerMetric('speed') === activePipeline && (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                )}
              </div>
              <div className="text-lg font-semibold text-green-900">
                {comparisonData[activePipeline].processingTime}s
              </div>
              <div className="text-xs text-green-600">Temps moyen</div>
            </div>

            <div className="bg-purple-50 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <CheckCircle className="h-5 w-5 text-purple-600" />
                {getWinnerMetric('emitterDetection') === activePipeline && (
                  <TrendingUp className="h-4 w-4 text-green-500" />
                )}
              </div>
              <div className="text-lg font-semibold text-purple-900">
                {comparisonData[activePipeline].emitterDetection}%
              </div>
              <div className="text-xs text-purple-600">Détection émetteur</div>
            </div>

            <div className="bg-orange-50 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <Zap className="h-5 w-5 text-orange-600" />
              </div>
              <div className="text-lg font-semibold text-orange-900">
                {comparisonData[activePipeline].documentsProcessed}
              </div>
              <div className="text-xs text-orange-600">Documents traités</div>
            </div>
          </div>

          {/* Comparison Chart */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="text-sm font-medium text-gray-900 mb-4">Comparaison Mistral vs DONUT</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={getComparisonBars()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip 
                  formatter={(value: number, name: string) => [
                    `${value}${getComparisonBars().find(d => d.mistral === value || d.donut === value)?.unit || ''}`,
                    name === 'mistral' ? 'Mistral MLX' : 'DONUT'
                  ]}
                />
                <Bar dataKey="mistral" fill="#3b82f6" name="mistral" />
                <Bar dataKey="donut" fill="#8b5cf6" name="donut" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Time Series */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="text-sm font-medium text-gray-900 mb-4">Évolution dans le temps</h4>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={comparisonData.timeSeriesData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="timestamp" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line 
                  type="monotone" 
                  dataKey="mistralAccuracy" 
                  stroke="#3b82f6" 
                  strokeWidth={2}
                  name="Mistral MLX"
                />
                <Line 
                  type="monotone" 
                  dataKey="donutAccuracy" 
                  stroke="#8b5cf6" 
                  strokeWidth={2}
                  name="DONUT"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Category Performance */}
          <div className="bg-white p-4 rounded-lg border">
            <h4 className="text-sm font-medium text-gray-900 mb-4">Performance par catégorie</h4>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={getCategoryData()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} angle={-45} textAnchor="end" height={60} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="mistral" fill="#3b82f6" name="Mistral MLX" />
                <Bar dataKey="donut" fill="#8b5cf6" name="DONUT" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="text-center py-12 text-gray-500">
          <BarChart3 className="h-8 w-8 text-gray-300 mx-auto mb-2" />
          <p className="text-sm">Aucune donnée de performance disponible</p>
        </div>
      )}
    </div>
  );
}