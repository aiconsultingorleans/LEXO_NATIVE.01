'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useStats } from '@/hooks/useStats';
import { useToast } from '@/contexts/ToastContext';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { DashboardSkeleton } from '@/components/ui/Loading';
import { FileText, Upload, Zap, Shield, RefreshCw, Database } from 'lucide-react';
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { DocumentsList } from '@/components/documents/DocumentsList';

export default function DashboardPage() {
  return (
    <AuthGuard requireAuth={true}>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const { getUserFullName } = useAuth();
  const { stats, activity, loading, error, refresh } = useStats();
  const toast = useToast();
  const [showUpload, setShowUpload] = useState(false);
  const [refreshList, setRefreshList] = useState(0);
  const [processingBatch, setProcessingBatch] = useState(false);
  const [clearingRAG, setClearingRAG] = useState(false);

  const handleRefresh = async () => {
    try {
      await refresh();
      toast.success('Données actualisées', 'Les statistiques ont été mises à jour');
    } catch (err) {
      toast.error('Erreur', 'Impossible d\'actualiser les données');
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
      const scanResponse = await fetch('/api/v1/batch/scan-folder', {
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
      const processResponse = await fetch('/api/v1/batch/process-unprocessed', {
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
      
      toast.success(
        'Traitement lancé !',
        `${processData.count} fichiers sont en cours d'analyse automatique`
      );
      
      // Actualiser les données après un délai
      setTimeout(() => {
        handleRefresh();
        setRefreshList(prev => prev + 1);
      }, 10000); // 10 secondes pour laisser le temps au traitement

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

      const response = await fetch('http://localhost:8000/api/v1/rag/clear', {
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
              onClick={() => setShowUpload(!showUpload)}
            >
              <Upload className="mr-2 h-5 w-5" />
              {showUpload ? 'Fermer l\'upload' : 'Uploader un document'}
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
              disabled={processingBatch}
              className="shadow-lg"
            >
              <Zap className="mr-2 h-5 w-5" />
              {processingBatch ? 'Analyse en cours...' : 'Analyser les fichiers non traités'}
            </Button>
          </div>
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
            <DocumentUpload 
              onUploadComplete={() => {
                setRefreshList(prev => prev + 1);
                setTimeout(() => setShowUpload(false), 2000);
              }}
            />
          </Card>
        )}

        {/* Documents List */}
        {!showUpload && (
          <Card className="p-6">
            <DocumentsList refreshTrigger={refreshList} />
          </Card>
        )}

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
                <p className="text-xs text-gray-400 mt-1">L'activité apparaîtra ici une fois que vous commencerez à uploader des documents</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </MainLayout>
  );
}