'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  FileText,
  Folder,
  Eye,
  Trash2,
  RefreshCw
} from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';

interface BatchOperation {
  id: number;
  batch_name: string;
  status: string;
  progress_percentage: number;
  files_processed: number;
  files_succeeded: number;
  files_failed: number;
  total_files: number;
  pipeline_type: string;
  started_at?: string;
  completed_at?: string;
  can_rollback: boolean;
  success_rate?: number;
  processing_time_seconds?: number;
}

interface BatchDocument {
  filename: string;
  status: string;
  processing_time?: number;
  error_message?: string;
  category?: string;
  confidence?: number;
}

interface BatchDetail extends BatchOperation {
  documents: BatchDocument[];
  recent_logs: Array<{
    timestamp: string;
    level: string;
    message: string;
    document_id?: number;
  }>;
}

interface BatchProgressProps {
  refreshInterval?: number;
  showOnlyActive?: boolean;
  className?: string;
}

export function BatchProgress({ 
  refreshInterval = 5000, 
  showOnlyActive = false,
  className = '' 
}: BatchProgressProps) {
  const [batches, setBatches] = useState<BatchOperation[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<BatchDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { showToast } = useToast();

  // Récupération de la liste des batches
  const fetchBatches = async (silent = false) => {
    try {
      if (!silent) setRefreshing(true);
      
      const response = await fetch('/api/v1/batch/list');
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération des batches');
      }
      
      const data = await response.json();
      let batchList = data.batches || [];
      
      // Filtrer les batches actifs si demandé
      if (showOnlyActive) {
        batchList = batchList.filter((batch: BatchOperation) => 
          ['pending', 'validating', 'processing', 'paused'].includes(batch.status)
        );
      }
      
      setBatches(batchList);
      setLoading(false);
      
    } catch (error) {
      console.error('Erreur fetchBatches:', error);
      if (!silent) {
        showToast('Erreur lors de la récupération des batches', 'error');
      }
    } finally {
      setRefreshing(false);
    }
  };

  // Récupération du détail d'un batch
  const fetchBatchDetail = async (batchId: number) => {
    try {
      const response = await fetch(`/api/v1/batch/${batchId}/status`);
      if (!response.ok) {
        throw new Error('Erreur lors de la récupération du détail');
      }
      
      const detail: BatchDetail = await response.json();
      setSelectedBatch(detail);
      
    } catch (error) {
      console.error('Erreur fetchBatchDetail:', error);
      showToast('Erreur lors de la récupération du détail', 'error');
    }
  };

  // Actions sur les batches
  const pauseBatch = async (batchId: number) => {
    try {
      const response = await fetch(`/api/v1/batch/${batchId}/pause`, { method: 'POST' });
      if (response.ok) {
        showToast('Batch mis en pause', 'info');
        fetchBatches(true);
        if (selectedBatch?.id === batchId) {
          fetchBatchDetail(batchId);
        }
      }
    } catch (error) {
      showToast('Erreur lors de la pause', 'error');
    }
  };

  const resumeBatch = async (batchId: number) => {
    try {
      const response = await fetch(`/api/v1/batch/${batchId}/resume`, { method: 'POST' });
      if (response.ok) {
        showToast('Batch repris', 'info');
        fetchBatches(true);
        if (selectedBatch?.id === batchId) {
          fetchBatchDetail(batchId);
        }
      }
    } catch (error) {
      showToast('Erreur lors de la reprise', 'error');
    }
  };

  const rollbackBatch = async (batchId: number) => {
    const confirmed = window.confirm(
      'Êtes-vous sûr de vouloir annuler ce batch ? Toutes les modifications seront supprimées.'
    );
    if (!confirmed) return;
    
    try {
      const response = await fetch(`/api/v1/batch/${batchId}/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'User rollback from interface' })
      });
      
      if (response.ok) {
        showToast('Batch annulé et modifications supprimées', 'info');
        fetchBatches(true);
        if (selectedBatch?.id === batchId) {
          setSelectedBatch(null);
        }
      }
    } catch (error) {
      showToast('Erreur lors de l\\'annulation', 'error');
    }
  };

  // Rafraîchissement automatique
  useEffect(() => {
    fetchBatches();
    
    const interval = setInterval(() => {
      fetchBatches(true);
      
      // Rafraîchir le détail si un batch est sélectionné et actif
      if (selectedBatch && ['processing', 'paused'].includes(selectedBatch.status)) {
        fetchBatchDetail(selectedBatch.id);
      }
    }, refreshInterval);
    
    return () => clearInterval(interval);
  }, [refreshInterval, selectedBatch?.id]);

  // Utilitaires
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'failed':
      case 'rolled_back':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'processing':
        return <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'paused':
        return <Pause className="w-5 h-5 text-yellow-500" />;
      case 'partial_success':
        return <AlertCircle className="w-5 h-5 text-orange-500" />;
      default:
        return <Clock className="w-5 h-5 text-gray-500" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'failed':
      case 'rolled_back':
        return 'bg-red-100 text-red-800';
      case 'processing':
        return 'bg-blue-100 text-blue-800';
      case 'paused':
        return 'bg-yellow-100 text-yellow-800';
      case 'partial_success':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'N/A';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}m ${secs}s`;
  };

  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'N/A';
    return new Date(timestamp).toLocaleString('fr-FR');
  };

  if (loading) {
    return (
      <Card className={`p-6 ${className}`}>
        <div className="flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
          <span className="ml-2">Chargement des batches...</span>
        </div>
      </Card>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header avec contrôles */}
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">
          {showOnlyActive ? 'Batches en cours' : 'Historique des batches'}
        </h2>
        <Button
          onClick={() => fetchBatches()}
          disabled={refreshing}
          variant="secondary"
          className="flex items-center space-x-2"
        >
          <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          <span>Actualiser</span>
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Liste des batches */}
        <Card className="p-4">
          <h3 className="text-lg font-medium mb-4">Liste des batches</h3>
          
          {batches.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              {showOnlyActive ? 'Aucun batch en cours' : 'Aucun batch trouvé'}
            </div>
          ) : (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {batches.map((batch) => (
                <div
                  key={batch.id}
                  className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedBatch?.id === batch.id ? 'border-blue-500 bg-blue-50' : 'hover:bg-gray-50'
                  }`}
                  onClick={() => fetchBatchDetail(batch.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      {getStatusIcon(batch.status)}
                      
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-gray-900 truncate">
                          {batch.batch_name || `Batch #${batch.id}`}
                        </h4>
                        
                        <div className="flex items-center space-x-4 text-xs text-gray-500 mt-1">
                          <span>{batch.total_files} fichiers</span>
                          <span className="capitalize">{batch.pipeline_type}</span>
                          {batch.started_at && (
                            <span>{formatTimestamp(batch.started_at)}</span>
                          )}
                        </div>
                        
                        {/* Barre de progression */}
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                          <div 
                            className="bg-blue-600 h-2 rounded-full transition-all"
                            style={{ width: `${batch.progress_percentage}%` }}
                          />
                        </div>
                        
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                          <span>{batch.progress_percentage.toFixed(1)}%</span>
                          <span>
                            {batch.files_succeeded} réussis / {batch.files_failed} échecs
                          </span>
                        </div>
                      </div>
                    </div>
                    
                    <span className={`text-xs px-2 py-1 rounded-full ml-2 ${getStatusColor(batch.status)}`}>
                      {batch.status}
                    </span>
                  </div>
                  
                  {/* Actions rapides */}
                  {['processing', 'paused'].includes(batch.status) && (
                    <div className="flex space-x-2 mt-3" onClick={(e) => e.stopPropagation()}>
                      {batch.status === 'processing' && (
                        <Button
                          onClick={() => pauseBatch(batch.id)}
                          size="sm"
                          variant="secondary"
                          className="flex items-center space-x-1"
                        >
                          <Pause className="w-3 h-3" />
                          <span>Pause</span>
                        </Button>
                      )}
                      
                      {batch.status === 'paused' && (
                        <Button
                          onClick={() => resumeBatch(batch.id)}
                          size="sm"
                          variant="secondary"
                          className="flex items-center space-x-1"
                        >
                          <Play className="w-3 h-3" />
                          <span>Reprendre</span>
                        </Button>
                      )}
                      
                      {batch.can_rollback && (
                        <Button
                          onClick={() => rollbackBatch(batch.id)}
                          size="sm"
                          variant="danger"
                          className="flex items-center space-x-1"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Annuler</span>
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Détails du batch sélectionné */}
        <Card className="p-4">
          <h3 className="text-lg font-medium mb-4">
            {selectedBatch ? `Détails - ${selectedBatch.batch_name || `Batch #${selectedBatch.id}`}` : 'Sélectionnez un batch'}
          </h3>
          
          {selectedBatch ? (
            <div className="space-y-4">
              {/* Informations générales */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Statut:</span>
                  <div className="flex items-center space-x-2 mt-1">
                    {getStatusIcon(selectedBatch.status)}
                    <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(selectedBatch.status)}`}>
                      {selectedBatch.status}
                    </span>
                  </div>
                </div>
                
                <div>
                  <span className="font-medium">Pipeline:</span>
                  <div className="mt-1 capitalize">{selectedBatch.pipeline_type}</div>
                </div>
                
                <div>
                  <span className="font-medium">Progression:</span>
                  <div className="mt-1">{selectedBatch.progress_percentage.toFixed(1)}%</div>
                </div>
                
                <div>
                  <span className="font-medium">Taux de succès:</span>
                  <div className="mt-1">
                    {selectedBatch.success_rate?.toFixed(1) || 0}%
                  </div>
                </div>
                
                <div>
                  <span className="font-medium">Démarré:</span>
                  <div className="mt-1">{formatTimestamp(selectedBatch.started_at)}</div>
                </div>
                
                <div>
                  <span className="font-medium">Durée:</span>
                  <div className="mt-1">{formatDuration(selectedBatch.processing_time_seconds)}</div>
                </div>
              </div>

              {/* Statistiques des fichiers */}
              <div className="border-t pt-4">
                <h4 className="font-medium mb-2">Fichiers ({selectedBatch.total_files})</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div className="text-center p-2 bg-green-50 rounded">
                    <div className="text-2xl font-bold text-green-600">{selectedBatch.files_succeeded}</div>
                    <div className="text-green-600">Réussis</div>
                  </div>
                  <div className="text-center p-2 bg-red-50 rounded">
                    <div className="text-2xl font-bold text-red-600">{selectedBatch.files_failed}</div>
                    <div className="text-red-600">Échecs</div>
                  </div>
                  <div className="text-center p-2 bg-blue-50 rounded">
                    <div className="text-2xl font-bold text-blue-600">
                      {selectedBatch.total_files - selectedBatch.files_processed}
                    </div>
                    <div className="text-blue-600">Restants</div>
                  </div>
                </div>
              </div>

              {/* Liste des documents */}
              <div className="border-t pt-4">
                <h4 className="font-medium mb-2">Documents</h4>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {selectedBatch.documents.map((doc, index) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                      <div className="flex items-center space-x-2 flex-1 min-w-0">
                        <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                        <span className="text-sm truncate">{doc.filename}</span>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        {doc.category && (
                          <span className="text-xs bg-gray-200 px-2 py-1 rounded">
                            {doc.category}
                          </span>
                        )}
                        
                        <span className={`text-xs px-2 py-1 rounded ${getStatusColor(doc.status)}`}>
                          {doc.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Logs récents */}
              {selectedBatch.recent_logs.length > 0 && (
                <div className="border-t pt-4">
                  <h4 className="font-medium mb-2">Logs récents</h4>
                  <div className="space-y-1 max-h-32 overflow-y-auto text-xs">
                    {selectedBatch.recent_logs.map((log, index) => (
                      <div key={index} className="p-2 bg-gray-50 rounded">
                        <div className="flex justify-between">
                          <span className={`font-medium ${
                            log.level === 'ERROR' ? 'text-red-600' :
                            log.level === 'WARNING' ? 'text-yellow-600' :
                            'text-gray-600'
                          }`}>
                            [{log.level}]
                          </span>
                          <span className="text-gray-500">
                            {new Date(log.timestamp).toLocaleTimeString('fr-FR')}
                          </span>
                        </div>
                        <div className="mt-1">{log.message}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8 text-gray-500">
              Cliquez sur un batch pour voir les détails
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}