'use client';

import { useState, useEffect, useCallback, useRef } from 'react';

export interface BatchFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error';
  progress: number;
  error?: string;
  result?: any;
}

export interface BatchConfig {
  batch_name?: string;
  pipeline_type: 'mistral' | 'donut';
  auto_rollback_on_error: boolean;
  max_retries_per_file: number;
  pause_on_error: boolean;
}

export interface BatchOperation {
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

export interface BatchDetail extends BatchOperation {
  documents: Array<{
    filename: string;
    status: string;
    processing_time?: number;
    error_message?: string;
    category?: string;
    confidence?: number;
  }>;
  recent_logs: Array<{
    timestamp: string;
    level: string;
    message: string;
    document_id?: number;
  }>;
}

interface UseBatchProcessingOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
  maxFiles?: number;
  onBatchComplete?: (batchId: number, results: any) => void;
  onBatchError?: (error: string) => void;
}

export function useBatchProcessing(options: UseBatchProcessingOptions = {}) {
  const {
    autoRefresh = true,
    refreshInterval = 5000,
    maxFiles = 50,
    onBatchComplete,
    onBatchError
  } = options;

  // État des fichiers sélectionnés
  const [files, setFiles] = useState<BatchFile[]>([]);
  
  // État des batches
  const [batches, setBatches] = useState<BatchOperation[]>([]);
  const [activeBatches, setActiveBatches] = useState<BatchOperation[]>([]);
  const [selectedBatch, setSelectedBatch] = useState<BatchDetail | null>(null);
  
  // État du traitement
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentBatchId, setCurrentBatchId] = useState<number | null>(null);
  
  // Configuration
  const [config, setConfig] = useState<BatchConfig>({
    pipeline_type: 'mistral',
    auto_rollback_on_error: true,
    max_retries_per_file: 3,
    pause_on_error: false
  });
  
  // États UI
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Refs pour le nettoyage
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const refreshIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // === Gestion des fichiers ===
  
  const addFiles = useCallback((newFiles: File[]) => {
    if (files.length + newFiles.length > maxFiles) {
      throw new Error(`Maximum ${maxFiles} fichiers autorisés`);
    }

    const supportedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg', 'image/tiff', 'image/bmp'];
    const validFiles = newFiles.filter(file => {
      return supportedTypes.includes(file.type) || file.name.match(/\\.(pdf|png|jpe?g|tiff?|bmp)$/i);
    });

    const batchFiles: BatchFile[] = validFiles.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      status: 'pending',
      progress: 0
    }));

    setFiles(prev => [...prev, ...batchFiles]);
    return batchFiles;
  }, [files.length, maxFiles]);

  const removeFile = useCallback((fileId: string) => {
    if (isProcessing) {
      throw new Error('Impossible de supprimer des fichiers pendant le traitement');
    }
    setFiles(prev => prev.filter(f => f.id !== fileId));
  }, [isProcessing]);

  const clearFiles = useCallback(() => {
    if (isProcessing) {
      throw new Error('Impossible de vider la liste pendant le traitement');
    }
    setFiles([]);
  }, [isProcessing]);

  const updateFileStatus = useCallback((fileId: string, updates: Partial<BatchFile>) => {
    setFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, ...updates } : f
    ));
  }, []);

  // === API Calls ===
  
  const createBatch = async (files: File[], config: BatchConfig): Promise<number> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    // Ajouter la configuration
    Object.entries(config).forEach(([key, value]) => {
      if (value !== undefined) {
        formData.append(key, value.toString());
      }
    });

    const response = await fetch('/api/v1/batch/create', {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Erreur lors de la création du batch');
    }

    const data = await response.json();
    return data.batch_id;
  };

  const startBatch = async (batchId: number, files: File[]): Promise<void> => {
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    const response = await fetch(`/api/v1/batch/${batchId}/start`, {
      method: 'POST',
      body: formData
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Erreur lors du démarrage du batch');
    }
  };

  const fetchBatches = async (): Promise<BatchOperation[]> => {
    const response = await fetch('/api/v1/batch/list');
    if (!response.ok) {
      throw new Error('Erreur lors de la récupération des batches');
    }
    const data = await response.json();
    return data.batches || [];
  };

  const fetchBatchDetail = async (batchId: number): Promise<BatchDetail> => {
    const response = await fetch(`/api/v1/batch/${batchId}/status`);
    if (!response.ok) {
      throw new Error('Erreur lors de la récupération du détail');
    }
    return response.json();
  };

  const pauseBatch = async (batchId: number): Promise<void> => {
    const response = await fetch(`/api/v1/batch/${batchId}/pause`, { method: 'POST' });
    if (!response.ok) {
      throw new Error('Erreur lors de la pause');
    }
  };

  const resumeBatch = async (batchId: number): Promise<void> => {
    const response = await fetch(`/api/v1/batch/${batchId}/resume`, { method: 'POST' });
    if (!response.ok) {
      throw new Error('Erreur lors de la reprise');
    }
  };

  const rollbackBatch = async (batchId: number, reason: string = 'User requested'): Promise<void> => {
    const response = await fetch(`/api/v1/batch/${batchId}/rollback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reason })
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || 'Erreur lors du rollback');
    }
  };

  // === Actions publiques ===
  
  const startBatchProcessing = useCallback(async () => {
    if (files.length === 0) {
      throw new Error('Aucun fichier à traiter');
    }

    try {
      setError(null);
      setIsProcessing(true);
      
      // 1. Créer le batch
      const batchId = await createBatch(files.map(f => f.file), config);
      setCurrentBatchId(batchId);
      
      // 2. Démarrer le traitement
      await startBatch(batchId, files.map(f => f.file));
      
      // 3. Démarrer le polling
      pollBatchStatus(batchId);
      
      return batchId;
      
    } catch (error) {
      setIsProcessing(false);
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      setError(errorMessage);
      onBatchError?.(errorMessage);
      throw error;
    }
  }, [files, config, onBatchError]);

  const pauseCurrentBatch = useCallback(async () => {
    if (!currentBatchId) return;
    
    try {
      await pauseBatch(currentBatchId);
      setIsPaused(true);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      setError(errorMessage);
      throw error;
    }
  }, [currentBatchId]);

  const resumeCurrentBatch = useCallback(async () => {
    if (!currentBatchId) return;
    
    try {
      await resumeBatch(currentBatchId);
      setIsPaused(false);
      pollBatchStatus(currentBatchId); // Reprendre le polling
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      setError(errorMessage);
      throw error;
    }
  }, [currentBatchId]);

  const rollbackCurrentBatch = useCallback(async (reason?: string) => {
    if (!currentBatchId) return;
    
    try {
      await rollbackBatch(currentBatchId, reason);
      setIsProcessing(false);
      setIsPaused(false);
      setCurrentBatchId(null);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      setError(errorMessage);
      throw error;
    }
  }, [currentBatchId]);

  const refreshBatches = useCallback(async () => {
    try {
      setLoading(true);
      const batchList = await fetchBatches();
      setBatches(batchList);
      
      // Filtrer les batches actifs
      const active = batchList.filter(batch => 
        ['pending', 'validating', 'processing', 'paused'].includes(batch.status)
      );
      setActiveBatches(active);
      
    } catch (error) {
      console.error('Erreur refresh batches:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const selectBatch = useCallback(async (batchId: number) => {
    try {
      const detail = await fetchBatchDetail(batchId);
      setSelectedBatch(detail);
    } catch (error) {
      console.error('Erreur select batch:', error);
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      setError(errorMessage);
    }
  }, []);

  // === Polling du statut ===
  
  const pollBatchStatus = useCallback((batchId: number) => {
    // Nettoyer le polling précédent
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
    }

    const poll = async () => {
      try {
        const status = await fetchBatchDetail(batchId);
        
        // Mettre à jour les statuts des fichiers
        status.documents?.forEach((doc, index) => {
          if (files[index]) {
            updateFileStatus(files[index].id, {
              status: doc.status === 'success' ? 'success' : 
                     doc.status === 'failed' ? 'error' : 
                     doc.status === 'processing' ? 'processing' : 'pending',
              progress: doc.status === 'success' ? 100 : 
                       doc.status === 'processing' ? 50 : 0,
              error: doc.error_message
            });
          }
        });

        // Vérifier si le batch est terminé
        if (['completed', 'failed', 'rolled_back', 'partial_success'].includes(status.status)) {
          setIsProcessing(false);
          setIsPaused(false);
          setCurrentBatchId(null);
          
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          
          if (status.status === 'completed' || status.status === 'partial_success') {
            onBatchComplete?.(batchId, status.documents);
          } else {
            onBatchError?.('Batch failed or rolled back');
          }
          return;
        }

      } catch (error) {
        console.error('Erreur polling status:', error);
      }
    };

    // Polling initial
    poll();
    
    // Puis polling régulier
    pollIntervalRef.current = setInterval(poll, 2000);
  }, [files, updateFileStatus, onBatchComplete, onBatchError]);

  // === Effects ===
  
  // Auto-refresh des batches
  useEffect(() => {
    if (autoRefresh) {
      refreshBatches();
      
      refreshIntervalRef.current = setInterval(() => {
        refreshBatches();
      }, refreshInterval);
    }
    
    return () => {
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, [autoRefresh, refreshInterval, refreshBatches]);

  // Nettoyage
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
      if (refreshIntervalRef.current) {
        clearInterval(refreshIntervalRef.current);
      }
    };
  }, []);

  // === Statistiques calculées ===
  
  const stats = {
    totalFiles: files.length,
    successCount: files.filter(f => f.status === 'success').length,
    errorCount: files.filter(f => f.status === 'error').length,
    processingCount: files.filter(f => f.status === 'processing').length,
    pendingCount: files.filter(f => f.status === 'pending').length,
    progressPercentage: files.length > 0 ? 
      ((files.filter(f => f.status === 'success' || f.status === 'error').length) / files.length) * 100 : 0
  };

  return {
    // État des fichiers
    files,
    addFiles,
    removeFile,
    clearFiles,
    updateFileStatus,
    
    // État des batches
    batches,
    activeBatches,
    selectedBatch,
    selectBatch,
    refreshBatches,
    
    // État du traitement
    isProcessing,
    isPaused,
    currentBatchId,
    
    // Configuration
    config,
    setConfig,
    
    // Actions
    startBatchProcessing,
    pauseCurrentBatch,
    resumeCurrentBatch,
    rollbackCurrentBatch,
    
    // État UI
    loading,
    error,
    setError,
    
    // Statistiques
    stats
  };
}