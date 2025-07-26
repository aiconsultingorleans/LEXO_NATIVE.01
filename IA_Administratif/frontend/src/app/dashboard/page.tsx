'use client';

import { useState, useRef, useCallback, useEffect, lazy, Suspense } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useStats } from '@/hooks/useStats';
import { useToast } from '@/contexts/ToastContext';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DashboardSkeleton } from '@/components/ui/Loading';
import { BatchProgressDisplay } from '@/components/ui/ProgressBar';
import { FileText, Upload, Zap, Shield, RefreshCw, Database, X } from 'lucide-react';

// Lazy loading des composants non critiques
const DocumentUpload = lazy(() => import('@/components/documents/DocumentUpload').then(module => ({ default: module.DocumentUpload })));
const DocumentsList = lazy(() => import('@/components/documents/DocumentsList').then(module => ({ default: module.DocumentsList })));

// Composants de loading pour les composants lazy
const DocumentUploadSkeleton = () => (
  <div className="animate-pulse bg-gray-200 h-32 rounded-lg"></div>
);

const DocumentsListSkeleton = () => (
  <div className="animate-pulse space-y-4">
    {[1, 2, 3].map(i => (
      <div key={i} className="bg-gray-200 h-16 rounded-lg"></div>
    ))}
  </div>
);

interface UploadFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error';
  progress: number;
  name: string;
  result?: unknown;
  error?: string;
}

export default function DashboardPage() {
  return (
    <AuthGuard requireAuth={true}>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const { getUserFullName } = useAuth();
  const { stats, activity, loading, isFromCache, lastUpdate, refresh } = useStats();
  const toast = useToast();
  const [showUpload, setShowUpload] = useState(false);
  const [refreshList, setRefreshList] = useState(0);
  const [processingBatch, setProcessingBatch] = useState(false);
  const [clearingRAG, setClearingRAG] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [compactUploadFiles, setCompactUploadFiles] = useState<UploadFile[]>([]);
  const [showSecondaryContent, setShowSecondaryContent] = useState(false);
  
  // État pour le statut des services avec polling adaptatif
  const [systemStatus, setSystemStatus] = useState<{
    pipeline: string;
    mistral: string;
    lastCheck: string;
    stableCount: number;
    pollInterval: number;
  }>({
    pipeline: 'unknown',
    mistral: 'unknown', 
    lastCheck: '',
    stableCount: 0,
    pollInterval: 30000 // Start with 30s
  });
  
  // État pour le suivi de progression batch
  const [batchProgress, setBatchProgress] = useState({
    isActive: false,
    current: 0,
    total: 0,
    startTime: null as number | null,
    currentFile: undefined as string | undefined,
    completionTime: undefined as string | undefined,
    batchId: null as number | null
  });

  // Vérification statut système avec polling adaptatif
  const checkSystemStatus = async () => {
    try {
      const token = localStorage.getItem('access_token');
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/health/pipeline`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        const newPipeline = data.pipeline_status;
        const newMistral = data.components?.mistral_mlx?.status || 'unknown';
        
        setSystemStatus(prevStatus => {
          // Vérifier si le système est stable
          const isStable = prevStatus.pipeline === newPipeline && prevStatus.mistral === newMistral;
          const newStableCount = isStable ? prevStatus.stableCount + 1 : 0;
          
          // Ajuster l'intervalle de polling selon la stabilité
          let newInterval = 30000; // Default 30s
          if (newStableCount >= 5) { // Après 5 checks stables
            newInterval = 60000; // Passer à 1 minute
          } else if (newStableCount >= 10) { // Après 10 checks stables
            newInterval = 120000; // Passer à 2 minutes
          }
          
          console.log(`🔄 System polling: stable=${isStable}, count=${newStableCount}, interval=${newInterval/1000}s`);
          
          return {
            pipeline: newPipeline,
            mistral: newMistral,
            lastCheck: new Date().toLocaleTimeString(),
            stableCount: newStableCount,
            pollInterval: newInterval
          };
        });
      }
    } catch (error) {
      console.warn('Erreur vérification statut système:', error);
      // Reset en cas d'erreur
      setSystemStatus(prev => ({
        ...prev,
        stableCount: 0,
        pollInterval: 30000
      }));
    }
  };

  const handleRefresh = async () => {
    try {
      await refresh(true); // Force refresh - bypass cache
      await checkSystemStatus(); // Vérifier aussi le statut système
      const cacheStatus = isFromCache ? ' (cache)' : ' (fresh)';
      toast.success('Données actualisées', `Les statistiques ont été mises à jour${cacheStatus}`);
    } catch {
      toast.error('Erreur', 'Impossible d\'actualiser les données');
    }
  };

  const handleUploadClick = () => {
    // Ouvrir le sélecteur de fichiers ET afficher la zone d'upload
    if (fileInputRef.current) {
      fileInputRef.current.click();
    }
    setShowUpload(true);
  };

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const fileArray = Array.from(files);
    await processFiles(fileArray);
    
    // Reset the input
    event.target.value = '';
  };

  const handleSingleFileUpload = async (uploadFile: UploadFile) => {
    const formData = new FormData();
    formData.append('file', uploadFile.file);

    try {
      // Update status to uploading
      setCompactUploadFiles(prev => prev.map(f => 
        f.id === uploadFile.id ? { ...f, status: 'uploading', progress: 20 } : f
      ));

      // Pipeline unifié : Upload + OCR + Mistral + Classification en un seul appel
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/documents/upload-and-process`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errorData.detail || 'Pipeline processing failed');
      }

      // Update status to processing (OCR + Mistral en cours)
      setCompactUploadFiles(prev => prev.map(f => 
        f.id === uploadFile.id ? { ...f, status: 'processing', progress: 70 } : f
      ));

      const result = await response.json();

      // Update status to success avec tous les résultats
      setCompactUploadFiles(prev => prev.map(f => 
        f.id === uploadFile.id ? { 
          ...f, 
          status: 'success', 
          progress: 100,
          result: {
            document_id: result.id,
            category: result.category,
            confidence_score: result.confidence_score,
            summary: result.summary,
            word_count: result.ocr_text ? result.ocr_text.split(' ').length : 0,
            entities_count: result.entities ? result.entities.length : 0
          }
        } : f
      ));

      // Message de succès détaillé
      let successMessage = `"${uploadFile.file.name}" a été traité avec succès`;
      if (result.category && result.category !== 'non_classes') {
        successMessage += ` - Classé comme: ${result.category}`;
      }
      if (result.confidence_score) {
        successMessage += ` (${(result.confidence_score * 100).toFixed(0)}% confiance)`;
      }
      
      toast.success('Pipeline complet terminé', successMessage);

      // Refresh data
      setTimeout(() => {
        handleRefresh();
        setRefreshList(prev => prev + 1);
      }, 1000);

    } catch (error) {
      setCompactUploadFiles(prev => prev.map(f => 
        f.id === uploadFile.id ? { 
          ...f, 
          status: 'error', 
          error: error instanceof Error ? error.message : 'Pipeline processing failed'
        } : f
      ));
      toast.error('Erreur Pipeline', `Échec du traitement complet de "${uploadFile.file.name}": ${error instanceof Error ? error.message : 'Erreur inconnue'}`);
    }
  };

  const processFiles = async (files: File[]) => {
    const newFiles: UploadFile[] = files.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending' as const,
      progress: 0,
      name: file.name
    }));

    setCompactUploadFiles(prev => [...prev, ...newFiles]);
    toast.info('Fichiers ajoutés', `${files.length} fichier${files.length > 1 ? 's' : ''} en cours de traitement`);

    // Process each file
    for (const uploadFile of newFiles) {
      await handleSingleFileUpload(uploadFile);
    }
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const files = Array.from(e.dataTransfer.files).filter(file => 
      file.type === 'application/pdf' || file.type.startsWith('image/')
    );
    
    if (files.length > 0) {
      processFiles(files);
    }
  }, [processFiles]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
  }, []);

  const removeCompactFile = (id: string) => {
    setCompactUploadFiles(prev => prev.filter(f => f.id !== id));
  };

  // Polling de progression pour batch
  const pollBatchProgress = async (batchId: number) => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) return;

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/batch/progress/${batchId}`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        // Si la progression n'existe plus, arrêter le polling
        if (response.status === 404) {
          setBatchProgress(prev => ({ ...prev, isActive: false }));
          return;
        }
        throw new Error('Erreur lors de la récupération de la progression');
      }

      const progressData = await response.json();
      
      setBatchProgress(prev => ({
        ...prev,
        current: progressData.current,
        total: progressData.total,
        currentFile: progressData.current_file,
        isActive: progressData.status !== 'completed'
      }));

      // Si terminé, afficher le temps total et arrêter le polling
      if (progressData.status === 'completed') {
        const completionTimeStr = `${progressData.completion_time.toFixed(1)}s`;
        setBatchProgress(prev => ({
          ...prev,
          isActive: false,
          completionTime: completionTimeStr
        }));
        
        toast.success(
          'Traitement batch terminé !',
          `${progressData.total} fichiers analysés en ${completionTimeStr}`
        );
        
        // Actualiser les données
        setTimeout(() => {
          handleRefresh();
          setRefreshList(prev => prev + 1);
        }, 1000);
        
        // Nettoyer la progression après 10 secondes
        setTimeout(() => {
          setBatchProgress({
            isActive: false,
            current: 0,
            total: 0,
            startTime: null,
            currentFile: undefined,
            completionTime: undefined,
            batchId: null
          });
        }, 10000);
        
        return; // Arrêter le polling
      }

      // Continuer le polling si en cours
      if (progressData.status === 'processing') {
        setTimeout(() => pollBatchProgress(batchId), 500); // Poll toutes les 500ms
      }

    } catch (err) {
      console.error('Erreur polling progression:', err);
      // Arrêter le polling en cas d'erreur
      setBatchProgress(prev => ({ ...prev, isActive: false }));
    }
  };

  const handleProcessUnprocessed = async () => {
    if (processingBatch) return;
    
    setProcessingBatch(true);
    
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        toast.error('Erreur', 'Token d\'authentification manquant');
        return;
      }

      // Scanner d'abord pour voir combien de fichiers
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const scanResponse = await fetch(`${apiUrl}/api/v1/batch/scan-folder`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!scanResponse.ok) {
        throw new Error('Erreur lors du scan');
      }

      const scanData = await scanResponse.json();
      
      if (scanData.unprocessed_files === 0) {
        toast.success('Aucun fichier à traiter', 'Tous les fichiers ont déjà été analysés');
        return;
      }

      // Lancer le traitement
      const processResponse = await fetch(`${apiUrl}/api/v1/batch/process-unprocessed`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!processResponse.ok) {
        throw new Error('Erreur lors du traitement');
      }

      const processData = await processResponse.json();
      
      // Initialiser le suivi de progression
      setBatchProgress({
        isActive: true,
        current: 0,
        total: processData.count,
        startTime: Date.now(),
        currentFile: undefined,
        completionTime: undefined,
        batchId: processData.batch_id
      });
      
      toast.success(
        'Traitement lancé !',
        `${processData.count} fichiers sont en cours d'analyse automatique`
      );
      
      // Démarrer le polling de progression
      setTimeout(() => pollBatchProgress(processData.batch_id), 1000); // Démarrer après 1s

    } catch (err) {
      console.error('Erreur traitement batch:', err);
      toast.error('Erreur', 'Impossible de lancer le traitement automatique');
    } finally {
      setProcessingBatch(false);
    }
  };

  const handleClearRAG = async () => {
    if (clearingRAG) return;
    
    const confirmed = window.confirm(
      'Êtes-vous sûr de vouloir vider complètement la base ?\n\n' +
      'Cette action supprimera :\n' +
      '• TOUS les documents de la liste\n' +
      '• TOUS les embeddings ChromaDB\n' +
      '• TOUTES les données vectorielles\n\n' +
      'Vous pourrez ensuite re-scanner le dossier OCR pour ajouter de nouveaux documents.\n\n' +
      'Cette action est IRRÉVERSIBLE.'
    );
    
    if (!confirmed) return;
    
    setClearingRAG(true);
    
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        toast.error('Erreur', 'Token d\'authentification manquant');
        return;
      }

      console.log('RAG Clear - Token:', token ? 'Present' : 'Missing');

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/rag/clear`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      console.log('RAG Clear - Response status:', response.status);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
        console.error('RAG Clear - Error:', errorMessage, errorData);
        throw new Error(`Erreur lors du vidage de la base RAG: ${errorMessage}`);
      }

      const data = await response.json();
      
      toast.success(
        'Base complètement vidée !',
        `${data.collections_cleared || 0} éléments supprimés (documents + ChromaDB)`
      );
      
      // Actualiser les données et forcer le refresh de la liste des documents
      await handleRefresh();
      setRefreshList(prev => prev + 1);

    } catch (err) {
      console.error('Erreur vidage RAG:', err);
      toast.error('Erreur', 'Impossible de vider la base RAG');
    } finally {
      setClearingRAG(false);
    }
  };

  // Vérifier le statut au chargement avec polling adaptatif
  useEffect(() => {
    checkSystemStatus();
    
    let intervalId: any;
    
    const setupInterval = () => {
      intervalId = setInterval(checkSystemStatus, systemStatus.pollInterval);
    };
    
    setupInterval();
    
    // Recreate interval when pollInterval changes
    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [systemStatus.pollInterval]);

  // Lazy load secondary content after main dashboard is loaded
  useEffect(() => {
    if (!loading) {
      const timer = setTimeout(() => {
        setShowSecondaryContent(true);
      }, 1000); // Delay 1s after main content loads
      
      return () => clearTimeout(timer);
    }
  }, [loading]);

  if (loading) {
    return (
      <MainLayout>
        <DashboardSkeleton />
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Hero Section */}
        <div className="text-center bg-gradient-to-br from-background-secondary to-background-tertiary p-8 rounded-2xl border border-card-border">
          <div className="mx-auto w-20 h-20 bg-gradient-to-br from-primary to-primary-dark rounded-2xl shadow-lg flex items-center justify-center mb-6">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Bienvenue sur LEXO v1
          </h1>
          <p className="text-xl text-foreground-secondary mb-8">
            Bonjour {getUserFullName()}, votre assistant IA pour la gestion administrative intelligente
          </p>
          <div className="flex justify-center space-x-4">
            <Button 
              size="lg" 
              className="shadow-lg"
              onClick={handleUploadClick}
            >
              <Upload className="mr-2 h-5 w-5" />
              Uploader un document
            </Button>
            <Button 
              variant="outline" 
              size="lg"
              onClick={() => setShowUpload(false)}
            >
              <FileText className="mr-2 h-5 w-5" />
              Voir mes documents
            </Button>
            <Button 
              variant="outline" 
              size="lg"
              onClick={handleRefresh}
            >
              <RefreshCw className="mr-2 h-5 w-5" />
              Actualiser
            </Button>
            <Button 
              variant="outline" 
              size="lg"
              onClick={handleClearRAG}
              disabled={clearingRAG}
              className="text-red-600 hover:text-red-700 hover:border-red-300"
            >
              <Database className="mr-2 h-5 w-5" />
              {clearingRAG ? 'Vidage...' : 'Vider base complète'}
            </Button>
          </div>
          <div className="flex justify-center mt-4">
            <Button 
              variant="secondary" 
              size="lg"
              onClick={handleProcessUnprocessed}
              disabled={processingBatch || batchProgress.isActive}
              className="shadow-lg"
            >
              <Zap className="mr-2 h-5 w-5" />
              {processingBatch || batchProgress.isActive ? 'Analyse en cours...' : 'Analyser les fichiers non traités'}
            </Button>
          </div>

          {/* Affichage de la progression batch */}
          <BatchProgressDisplay batchProgress={batchProgress} />

          {/* Input file caché */}
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
        </div>

        {/* Indicateur de statut système */}
        <div className="bg-card-background p-4 rounded-xl shadow-sm border border-card-border">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  systemStatus.pipeline === 'operational' ? 'bg-green-500' : 
                  systemStatus.pipeline === 'degraded' ? 'bg-yellow-500' : 'bg-gray-400'
                }`}></div>
                <span className="text-sm font-medium">Pipeline documentaire</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  systemStatus.pipeline === 'operational' ? 'bg-green-100 text-green-800' : 
                  systemStatus.pipeline === 'degraded' ? 'bg-yellow-100 text-yellow-800' : 'bg-gray-100 text-gray-600'
                }`}>
                  {systemStatus.pipeline === 'operational' ? 'Opérationnel' : 
                   systemStatus.pipeline === 'degraded' ? 'Dégradé' : 'Inconnu'}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`w-3 h-3 rounded-full ${
                  systemStatus.mistral === 'healthy' ? 'bg-green-500' : 
                  systemStatus.mistral === 'unavailable' ? 'bg-red-500' : 'bg-gray-400'
                }`}></div>
                <span className="text-sm font-medium">Mistral MLX</span>
                <span className={`text-xs px-2 py-1 rounded ${
                  systemStatus.mistral === 'healthy' ? 'bg-green-100 text-green-800' : 
                  systemStatus.mistral === 'unavailable' ? 'bg-red-100 text-red-800' : 'bg-gray-100 text-gray-600'
                }`}>
                  {systemStatus.mistral === 'healthy' ? '🤖 Actif' : 
                   systemStatus.mistral === 'unavailable' ? '❌ Indisponible' : '❓ Inconnu'}
                </span>
              </div>
            </div>
            <div className="text-xs text-gray-500 space-y-1">
              {systemStatus.lastCheck && (
                <div className="flex items-center space-x-2">
                  <span>Système vérifié: {systemStatus.lastCheck}</span>
                  <span className="bg-gray-100 text-gray-600 px-1 py-0.5 rounded text-xs">
                    🔄 {systemStatus.pollInterval/1000}s
                  </span>
                  {systemStatus.stableCount >= 5 && (
                    <span className="bg-green-100 text-green-700 px-1 py-0.5 rounded text-xs">
                      ✅ Stable
                    </span>
                  )}
                </div>
              )}
              {lastUpdate > 0 && (
                <div className="flex items-center space-x-2">
                  <span>Stats: {new Date(lastUpdate).toLocaleTimeString()}</span>
                  {isFromCache && (
                    <span className="bg-blue-100 text-blue-700 px-1 py-0.5 rounded text-xs">
                      📄 Cache
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
          {systemStatus.mistral === 'unavailable' && (
            <div className="mt-2 text-xs text-yellow-600 bg-yellow-50 p-2 rounded">
              ⚠️ Mode fallback actif : OCR seul disponible (sans enrichissement IA)
            </div>
          )}
        </div>

        {/* Zone de drop compacte permanente */}
        <div 
          className="bg-card-background/50 border-2 border-dashed border-gray-300 rounded-xl p-6 text-center hover:border-primary/50 hover:bg-primary/5 transition-all duration-200 cursor-pointer"
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onClick={() => fileInputRef.current?.click()}
        >
          <div className="flex items-center justify-center space-x-3">
            <Upload className="h-6 w-6 text-gray-400" />
            <p className="text-sm text-gray-600">
              ou glissez vos documents ici (PDF, images)
            </p>
          </div>
          
          {/* Liste des fichiers en cours de traitement dans la zone compacte */}
          {compactUploadFiles.length > 0 && (
            <div className="mt-4 space-y-2">
              {compactUploadFiles.map(file => (
                <div key={file.id} className="flex items-center justify-between bg-background-secondary/50 p-2 rounded-lg">
                  <div className="flex items-center space-x-2 flex-1">
                    <FileText className="h-4 w-4 text-gray-400" />
                    <div className="flex-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-700 truncate max-w-32">{file.name}</span>
                        {file.status === 'uploading' && (
                          <span className="text-xs text-blue-500">📤 Upload... ({file.progress}%)</span>
                        )}
                        {file.status === 'processing' && (
                          <span className="text-xs text-purple-500">🔍 OCR → 🤖 Mistral... ({file.progress}%)</span>
                        )}
                      </div>
                      
                      {/* Barre de progression pour upload et processing */}
                      {(file.status === 'uploading' || file.status === 'processing') && (
                        <div className="mt-1 w-full bg-gray-200 rounded-full h-1.5">
                          <div
                            className={`h-1.5 rounded-full transition-all duration-300 ${
                              file.status === 'uploading' ? 'bg-blue-500' : 'bg-purple-500'
                            }`}
                            style={{ width: `${file.progress}%` }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {/* Statut de succès et résultats */}
                  {file.status === 'success' && (
                    <div className="flex flex-col ml-2">
                      <span className="text-xs text-green-500">✓ Terminé</span>
                      {file.result && typeof file.result === 'object' && (
                        <div className="text-xs text-gray-600 mt-1">
                          <div className="flex items-center space-x-2">
                            {(file.result as any).category && (file.result as any).category !== 'non_classes' && (
                              <span className="bg-blue-100 text-blue-800 px-1 rounded text-xs">
                                📂 {(file.result as any).category}
                              </span>
                            )}
                            {(file.result as any).confidence_score && (
                              <span className="bg-green-100 text-green-800 px-1 rounded text-xs">
                                {((file.result as any).confidence_score * 100).toFixed(0)}%
                              </span>
                            )}
                          </div>
                          {(file.result as any).summary && (
                            <div className="text-xs text-gray-500 mt-1 max-w-40 truncate">
                              💬 {(file.result as any).summary}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  
                  {/* Statut d'erreur */}
                  {file.status === 'error' && (
                    <span className="text-xs text-red-500">✗ {file.error}</span>
                  )}
                  
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeCompactFile(file.id);
                    }}
                    className="text-gray-400 hover:text-gray-600"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border hover:border-border-light transition-all duration-200">
            <div className="flex items-center">
              <div className="p-3 bg-primary/10 rounded-xl">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-foreground-secondary">Documents traités</p>
                <p className="text-2xl font-bold text-foreground">{stats.documentsProcessed}</p>
              </div>
            </div>
          </div>

          <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border hover:border-border-light transition-all duration-200">
            <div className="flex items-center">
              <div className="p-3 bg-success/10 rounded-xl">
                <Zap className="h-6 w-6 text-success" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-foreground-secondary">Précision OCR</p>
                <p className="text-2xl font-bold text-foreground">{stats.averageConfidence}%</p>
              </div>
            </div>
          </div>

          <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border hover:border-border-light transition-all duration-200">
            <div className="flex items-center">
              <div className="p-3 bg-success/10 rounded-xl">
                <Shield className="h-6 w-6 text-success" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-foreground-secondary">Sécurité</p>
                <p className="text-2xl font-bold text-foreground">{stats.securityStatus}%</p>
              </div>
            </div>
          </div>

          <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border hover:border-border-light transition-all duration-200">
            <div className="flex items-center">
              <div className="p-3 bg-yellow-500/10 rounded-xl">
                <FileText className="h-6 w-6 text-yellow-500" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-foreground-secondary">En attente</p>
                <p className="text-2xl font-bold text-foreground">{stats.pendingDocuments}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Document Upload Section */}
        {showUpload && (
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
              <Upload className="w-5 h-5 text-primary" />
              Uploader des documents
            </h3>
            <Suspense fallback={<DocumentUploadSkeleton />}>
              <DocumentUpload 
                onUploadComplete={() => {
                  setRefreshList(prev => prev + 1);
                  setTimeout(() => setShowUpload(false), 2000);
                }}
              />
            </Suspense>
          </Card>
        )}

        {/* Documents List */}
        {!showUpload && (
          <Card className="p-6">
            <Suspense fallback={<DocumentsListSkeleton />}>
              <DocumentsList refreshTrigger={refreshList} />
            </Suspense>
          </Card>
        )}

        {/* Secondary Content - Lazy Loaded */}
        {showSecondaryContent && (
          <>
            {/* Quick Actions */}
            <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border">
              <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
                <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Actions rapides
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button 
                  variant="outline" 
                  className="justify-start h-12 hover:bg-hover-background"
                  onClick={() => setShowUpload(true)}
                >
                  <Upload className="mr-3 h-5 w-5" />
                  Glisser-déposer des documents
                </Button>
                <Button variant="outline" className="justify-start h-12 hover:bg-hover-background">
                  <FileText className="mr-3 h-5 w-5" />
                  Rechercher dans mes documents
                </Button>
                <Button variant="outline" className="justify-start h-12 hover:bg-hover-background">
                  <Zap className="mr-3 h-5 w-5" />
                  Générer un rapport
                </Button>
              </div>
            </div>

            {/* Recent Activity */}
            <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border">
              <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
                <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Activité récente
              </h3>
              <div className="space-y-4">
                {activity.length > 0 ? (
                  activity.map((item) => {
                    const statusColors = {
                      success: 'bg-success/5 border-success/10',
                      warning: 'bg-warning/5 border-warning/10',
                      error: 'bg-error/5 border-error/10',
                      info: 'bg-primary/5 border-primary/10'
                    };
                    
                    const dotColors = {
                      success: 'bg-success',
                      warning: 'bg-warning',
                      error: 'bg-error',
                      info: 'bg-primary'
                    };

                    return (
                      <div key={item.id} className={`flex items-center justify-between py-3 px-4 rounded-lg ${statusColors[item.status]} border`}>
                        <div className="flex items-center">
                          <div className={`w-3 h-3 ${dotColors[item.status]} rounded-full mr-4`}></div>
                          <span className="text-sm text-foreground">{item.message}</span>
                        </div>
                        <span className="text-xs text-foreground-muted bg-background-secondary px-2 py-1 rounded-full">{item.timestamp}</span>
                      </div>
                    );
                  })
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <FileText className="h-8 w-8 text-gray-300 mx-auto mb-2" />
                    <p className="text-sm">Aucune activité récente</p>
                    <p className="text-xs text-gray-400 mt-1">L&apos;activité apparaîtra ici une fois que vous commencerez à uploader des documents</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
        
        {/* Loading skeleton for secondary content */}
        {!showSecondaryContent && !loading && (
          <div className="space-y-6">
            <div className="animate-pulse bg-gray-200 h-32 rounded-xl"></div>
            <div className="animate-pulse bg-gray-200 h-48 rounded-xl"></div>
          </div>
        )}
      </div>
    </MainLayout>
  );
}