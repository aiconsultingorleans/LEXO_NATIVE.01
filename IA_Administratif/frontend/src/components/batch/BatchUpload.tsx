'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Upload, X, FileText, Play, Pause, RotateCcw, AlertCircle, Check } from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';

interface BatchFile {
  id: string;
  file: File;
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error';
  progress: number;
  error?: string;
  result?: any;
}

interface BatchUploadProps {
  onBatchStart?: (batchId: number) => void;
  onBatchComplete?: (batchId: number, results: any[]) => void;
  onBatchError?: (error: string) => void;
  maxFiles?: number;
  className?: string;
}

interface BatchCreateRequest {
  batch_name?: string;
  pipeline_type: 'mistral' | 'donut';
  auto_rollback_on_error: boolean;
  max_retries_per_file: number;
  pause_on_error: boolean;
}

export function BatchUpload({
  onBatchStart,
  onBatchComplete,
  onBatchError,
  maxFiles = 50,
  className = ''
}: BatchUploadProps) {
  const [files, setFiles] = useState<BatchFile[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [currentBatchId, setCurrentBatchId] = useState<number | null>(null);
  const [config, setConfig] = useState<BatchCreateRequest>({
    pipeline_type: 'mistral',
    auto_rollback_on_error: true,
    max_retries_per_file: 3,
    pause_on_error: false
  });
  const [dragActive, setDragActive] = useState(false);
  
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { showToast } = useToast();

  // Gestion du drag & drop
  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const droppedFiles = Array.from(e.dataTransfer.files);
    handleFileSelection(droppedFiles);
  }, []);

  const handleFileSelection = useCallback((selectedFiles: File[]) => {
    if (files.length + selectedFiles.length > maxFiles) {
      showToast(`Maximum ${maxFiles} fichiers autorisés`, 'error');
      return;
    }

    // Validation des types de fichiers
    const supportedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg', 'image/tiff', 'image/bmp'];
    const validFiles = selectedFiles.filter(file => {
      if (!supportedTypes.includes(file.type) && !file.name.match(/\\.(pdf|png|jpe?g|tiff?|bmp)$/i)) {
        showToast(`Format non supporté: ${file.name}`, 'error');
        return false;
      }
      return true;
    });

    // Ajouter les fichiers avec IDs uniques
    const newFiles: BatchFile[] = validFiles.map(file => ({
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      file,
      status: 'pending',
      progress: 0
    }));

    setFiles(prev => [...prev, ...newFiles]);
    
    if (newFiles.length > 0) {
      showToast(`${newFiles.length} fichier(s) ajouté(s)`, 'success');
    }
  }, [files.length, maxFiles, showToast]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files);
      handleFileSelection(selectedFiles);
      e.target.value = ''; // Reset input
    }
  }, [handleFileSelection]);

  const removeFile = useCallback((fileId: string) => {
    if (isProcessing) {
      showToast('Impossible de supprimer des fichiers pendant le traitement', 'error');
      return;
    }
    setFiles(prev => prev.filter(f => f.id !== fileId));
  }, [isProcessing, showToast]);

  const clearAllFiles = useCallback(() => {
    if (isProcessing) {
      showToast('Impossible de vider la liste pendant le traitement', 'error');
      return;
    }
    setFiles([]);
  }, [isProcessing, showToast]);

  const updateFileStatus = useCallback((fileId: string, updates: Partial<BatchFile>) => {
    setFiles(prev => prev.map(f => 
      f.id === fileId ? { ...f, ...updates } : f
    ));
  }, []);

  const startBatchProcessing = async () => {
    if (files.length === 0) {
      showToast('Aucun fichier à traiter', 'error');
      return;
    }

    try {
      setIsProcessing(true);
      
      // 1. Créer le batch
      const formData = new FormData();
      files.forEach(({ file }) => {
        formData.append('files', file);
      });

      const createResponse = await fetch('/api/v1/batch/create', {
        method: 'POST',
        body: formData,
        // Note: Les paramètres de config seraient passés via query params ou headers
      });

      if (!createResponse.ok) {
        throw new Error('Erreur lors de la création du batch');
      }

      const { batch_id } = await createResponse.json();
      setCurrentBatchId(batch_id);
      onBatchStart?.(batch_id);

      // 2. Démarrer le traitement
      const startFormData = new FormData();
      files.forEach(({ file }) => {
        startFormData.append('files', file);
      });

      const startResponse = await fetch(`/api/v1/batch/${batch_id}/start`, {
        method: 'POST',
        body: startFormData
      });

      if (!startResponse.ok) {
        throw new Error('Erreur lors du démarrage du traitement');
      }

      showToast('Traitement batch démarré', 'success');
      
      // 3. Démarrer le polling du statut
      pollBatchStatus(batch_id);

    } catch (error) {
      setIsProcessing(false);
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      showToast(errorMessage, 'error');
      onBatchError?.(errorMessage);
    }
  };

  const pollBatchStatus = async (batchId: number) => {
    const poll = async () => {
      try {
        const response = await fetch(`/api/v1/batch/${batchId}/status`);
        if (!response.ok) return;

        const status = await response.json();
        
        // Mettre à jour les statuts des fichiers
        status.documents?.forEach((doc: any, index: number) => {
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
          
          if (status.status === 'completed' || status.status === 'partial_success') {
            showToast(`Batch terminé: ${status.files_succeeded}/${status.total_files} réussis`, 'success');
            onBatchComplete?.(batchId, status.documents);
          } else {
            showToast('Batch échoué ou annulé', 'error');
            onBatchError?.('Batch failed');
          }
          return;
        }

        // Continuer le polling si en cours
        if (status.status === 'processing' && !isPaused) {
          setTimeout(poll, 2000); // Poll toutes les 2 secondes
        }

      } catch (error) {
        console.error('Erreur polling status:', error);
        setTimeout(poll, 5000); // Retry dans 5 secondes en cas d'erreur
      }
    };

    poll();
  };

  const pauseBatch = async () => {
    if (!currentBatchId) return;
    
    try {
      const response = await fetch(`/api/v1/batch/${currentBatchId}/pause`, {
        method: 'POST'
      });
      
      if (response.ok) {
        setIsPaused(true);
        showToast('Batch mis en pause', 'info');
      }
    } catch (error) {
      showToast('Erreur lors de la pause', 'error');
    }
  };

  const resumeBatch = async () => {
    if (!currentBatchId) return;
    
    try {
      const response = await fetch(`/api/v1/batch/${currentBatchId}/resume`, {
        method: 'POST'
      });
      
      if (response.ok) {
        setIsPaused(false);
        showToast('Batch repris', 'info');
        pollBatchStatus(currentBatchId); // Reprendre le polling
      }
    } catch (error) {
      showToast('Erreur lors de la reprise', 'error');
    }
  };

  const rollbackBatch = async () => {
    if (!currentBatchId) return;
    
    const confirmed = window.confirm('Êtes-vous sûr de vouloir annuler ce batch ? Toutes les modifications seront supprimées.');
    if (!confirmed) return;
    
    try {
      const response = await fetch(`/api/v1/batch/${currentBatchId}/rollback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'User cancellation' })
      });
      
      if (response.ok) {
        setIsProcessing(false);
        setIsPaused(false);
        setCurrentBatchId(null);
        showToast('Batch annulé et modifications supprimées', 'info');
      }
    } catch (error) {
      showToast('Erreur lors de l\\'annulation', 'error');
    }
  };

  // Calculs de progression
  const totalFiles = files.length;
  const successCount = files.filter(f => f.status === 'success').length;
  const errorCount = files.filter(f => f.status === 'error').length;
  const processingCount = files.filter(f => f.status === 'processing').length;
  const progressPercentage = totalFiles > 0 ? ((successCount + errorCount) / totalFiles) * 100 : 0;

  // Estimation du temps restant (basé sur 2s par fichier)
  const remainingFiles = totalFiles - successCount - errorCount;
  const estimatedMinutesRemaining = (remainingFiles * 2) / 60;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Configuration du batch */}
      <Card className="p-4">
        <h3 className="text-lg font-semibold mb-4">Configuration du traitement</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Pipeline</label>
            <select 
              value={config.pipeline_type}
              onChange={(e) => setConfig(prev => ({ ...prev, pipeline_type: e.target.value as 'mistral' | 'donut' }))}
              className="w-full p-2 border rounded-md"
              disabled={isProcessing}
            >
              <option value="mistral">Mistral MLX (Recommandé)</option>
              <option value="donut">DONUT Alternative</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">Retry par fichier</label>
            <input
              type="number"
              min="0"
              max="10"
              value={config.max_retries_per_file}
              onChange={(e) => setConfig(prev => ({ ...prev, max_retries_per_file: parseInt(e.target.value) }))}
              className="w-full p-2 border rounded-md"
              disabled={isProcessing}
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="auto-rollback"
              checked={config.auto_rollback_on_error}
              onChange={(e) => setConfig(prev => ({ ...prev, auto_rollback_on_error: e.target.checked }))}
              disabled={isProcessing}
            />
            <label htmlFor="auto-rollback" className="text-sm">Rollback automatique en cas d'erreur</label>
          </div>
          
          <div className="flex items-center space-x-2">
            <input
              type="checkbox"
              id="pause-on-error"
              checked={config.pause_on_error}
              onChange={(e) => setConfig(prev => ({ ...prev, pause_on_error: e.target.checked }))}
              disabled={isProcessing}
            />
            <label htmlFor="pause-on-error" className="text-sm">Pause en cas d'erreur</label>
          </div>
        </div>
      </Card>

      {/* Zone de drop des fichiers */}
      <Card 
        className={`p-8 border-2 border-dashed transition-colors cursor-pointer ${
          dragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
        } ${isProcessing ? 'pointer-events-none opacity-50' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <div className="text-center">
          <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Glissez-déposez vos fichiers ici
          </h3>
          <p className="text-sm text-gray-500 mb-4">
            ou cliquez pour sélectionner (max {maxFiles} fichiers)
          </p>
          <p className="text-xs text-gray-400">
            Formats supportés: PDF, PNG, JPG, JPEG, TIFF, BMP
          </p>
        </div>
        
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
          onChange={handleFileInputChange}
          className="hidden"
          disabled={isProcessing}
        />
      </Card>

      {/* Barre de progression globale */}
      {files.length > 0 && (
        <Card className="p-4">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-sm font-medium">Progression globale</h3>
            <span className="text-sm text-gray-500">
              {successCount + errorCount}/{totalFiles} fichiers traités
            </span>
          </div>
          
          <div className="w-full bg-gray-200 rounded-full h-3 mb-4">
            <div 
              className="bg-blue-600 h-3 rounded-full transition-all duration-300" 
              style={{ width: `${progressPercentage}%` }}
            />
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-green-500 rounded-full"></div>
              <span>Réussis: {successCount}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
              <span>Échecs: {errorCount}</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-3 h-3 bg-blue-500 rounded-full"></div>
              <span>En cours: {processingCount}</span>
            </div>
            {isProcessing && estimatedMinutesRemaining > 0 && (
              <div className="text-gray-500">
                Temps estimé: {Math.ceil(estimatedMinutesRemaining)}min
              </div>
            )}
          </div>
        </Card>
      )}

      {/* Contrôles du batch */}
      {files.length > 0 && (
        <div className="flex justify-between items-center">
          <div className="flex space-x-2">
            <Button
              onClick={startBatchProcessing}
              disabled={isProcessing || files.length === 0}
              className="flex items-center space-x-2"
            >
              <Play className="w-4 h-4" />
              <span>Démarrer le traitement</span>
            </Button>
            
            {isProcessing && !isPaused && (
              <Button onClick={pauseBatch} variant="secondary" className="flex items-center space-x-2">
                <Pause className="w-4 h-4" />
                <span>Pause</span>
              </Button>
            )}
            
            {isProcessing && isPaused && (
              <Button onClick={resumeBatch} variant="secondary" className="flex items-center space-x-2">
                <Play className="w-4 h-4" />
                <span>Reprendre</span>
              </Button>
            )}
            
            {isProcessing && (
              <Button onClick={rollbackBatch} variant="danger" className="flex items-center space-x-2">
                <RotateCcw className="w-4 h-4" />
                <span>Annuler</span>
              </Button>
            )}
          </div>
          
          <Button 
            onClick={clearAllFiles} 
            variant="secondary" 
            disabled={isProcessing}
            className="flex items-center space-x-2"
          >
            <X className="w-4 h-4" />
            <span>Vider ({files.length})</span>
          </Button>
        </div>
      )}

      {/* Liste des fichiers */}
      {files.length > 0 && (
        <Card className="p-4">
          <h3 className="text-lg font-semibold mb-4">Fichiers sélectionnés ({files.length})</h3>
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {files.map((batchFile) => (
              <div key={batchFile.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center space-x-3 flex-1">
                  <FileText className="w-5 h-5 text-gray-400" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {batchFile.file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {(batchFile.file.size / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    {batchFile.status === 'success' && (
                      <Check className="w-5 h-5 text-green-500" />
                    )}
                    {batchFile.status === 'error' && (
                      <AlertCircle className="w-5 h-5 text-red-500" />
                    )}
                    {batchFile.status === 'processing' && (
                      <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    )}
                    
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      batchFile.status === 'success' ? 'bg-green-100 text-green-800' :
                      batchFile.status === 'error' ? 'bg-red-100 text-red-800' :
                      batchFile.status === 'processing' ? 'bg-blue-100 text-blue-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {batchFile.status === 'pending' ? 'En attente' :
                       batchFile.status === 'processing' ? 'Traitement...' :
                       batchFile.status === 'success' ? 'Réussi' :
                       batchFile.status === 'error' ? 'Échec' : batchFile.status}
                    </span>
                  </div>
                </div>
                
                {!isProcessing && (
                  <Button
                    onClick={() => removeFile(batchFile.id)}
                    variant="ghost"
                    size="sm"
                    className="ml-2"
                  >
                    <X className="w-4 h-4" />
                  </Button>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}