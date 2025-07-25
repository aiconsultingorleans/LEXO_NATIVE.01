'use client';

import { useState, useEffect, useCallback } from 'react';
import { FileText, Calendar, Eye, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Modal } from '@/components/ui/Modal';
import { ConfirmDialog } from '@/components/ui/Modal';
import { LoadingSpinner, DocumentSkeleton } from '@/components/ui/Loading';
import { useModal, useConfirmDialog } from '@/hooks/useModal';
import { useToast } from '@/contexts/ToastContext';

interface Document {
  id: number;
  filename: string;
  category: string;
  confidence_score: number;
  ocr_text: string | null;
  entities: string[];
  amount: number | null;
  document_date: string | null;
  custom_tags: string[];
  summary: string | null;
  created_at: string;
  processed_at: string | null;
}

interface DocumentsListResponse {
  documents: Document[];
  total: number;
  page: number;
  limit: number;
}

interface DocumentsListProps {
  refreshTrigger?: number;
}

export function DocumentsList({ refreshTrigger }: DocumentsListProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [isDeleting, setIsDeleting] = useState(false);
  
  const viewerModal = useModal();
  const confirmDialog = useConfirmDialog();
  const toast = useToast();

  const fetchDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`http://localhost:8000/api/v1/documents?page=${page}&limit=10`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (response.ok) {
        const data: DocumentsListResponse = await response.json();
        setDocuments(data.documents);
        setTotal(data.total);
      } else {
        toast.error('Erreur', 'Impossible de charger les documents');
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
      toast.error('Erreur de connexion', 'Vérifiez votre connexion internet');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchDocuments();
  }, [page, fetchDocuments]);

  // Écouter les changements du trigger pour forcer le refresh
  useEffect(() => {
    if (refreshTrigger !== undefined) {
      fetchDocuments();
    }
  }, [refreshTrigger, fetchDocuments]);

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      facture: 'bg-blue-100 text-blue-800',
      rib: 'bg-green-100 text-green-800',
      impot: 'bg-red-100 text-red-800',
      contrat: 'bg-purple-100 text-purple-800',
      attestation: 'bg-yellow-100 text-yellow-800',
      autre: 'bg-gray-100 text-gray-800'
    };
    return colors[category] || colors.autre;
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('fr-FR');
  };

  const handleDelete = async (document: Document) => {
    confirmDialog.confirm({
      title: 'Supprimer le document',
      description: `Êtes-vous sûr de vouloir supprimer "${document.filename}" ? Cette action est irréversible.`,
      confirmText: 'Supprimer',
      variant: 'danger',
      onConfirm: () => deleteDocument(document.id)
    });
  };

  const deleteDocument = async (id: number) => {
    try {
      setIsDeleting(true);
      const response = await fetch(`http://localhost:8000/api/v1/documents/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (response.ok) {
        toast.success('Document supprimé', 'Le document a été supprimé avec succès');
        await fetchDocuments();
      } else {
        toast.error('Erreur', 'Impossible de supprimer le document');
      }
    } catch (error) {
      console.error('Failed to delete document:', error);
      toast.error('Erreur de connexion', 'Impossible de supprimer le document');
    } finally {
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <DocumentSkeleton />
        <DocumentSkeleton />
        <DocumentSkeleton />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-foreground">Mes documents</h2>
        <p className="text-sm text-foreground-secondary">{total} document{total > 1 ? 's' : ''}</p>
      </div>

      {documents.length === 0 ? (
        <Card className="p-12 text-center">
          <FileText className="mx-auto h-12 w-12 text-gray-400 mb-4" />
          <p className="text-gray-500">Aucun document trouvé</p>
          <p className="text-sm text-gray-400 mt-2">
            Commencez par uploader un document
          </p>
        </Card>
      ) : (
        <div className="grid gap-4">
          {documents.map((doc) => (
            <Card key={doc.id} className="p-6 hover:shadow-lg transition-shadow">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-3">
                    <FileText className="h-6 w-6 text-gray-400" />
                    <h3 className="font-medium text-foreground">{doc.filename}</h3>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getCategoryColor(doc.category)}`}>
                      {doc.category}
                    </span>
                    {doc.confidence_score > 0 && (
                      <span className="text-xs text-gray-500">
                        Confiance: {(doc.confidence_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-4 text-sm text-foreground-secondary mb-3">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      <span>Créé le {formatDate(doc.created_at)}</span>
                    </div>
                    {doc.document_date && (
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        <span>Document du {formatDate(doc.document_date)}</span>
                      </div>
                    )}
                    {doc.amount && (
                      <div className="flex items-center gap-1">
                        <span className="font-medium">{doc.amount.toFixed(2)} €</span>
                      </div>
                    )}
                  </div>

                  {doc.entities.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {doc.entities.slice(0, 5).map((entity, idx) => (
                        <span key={idx} className="px-2 py-1 bg-card-background text-foreground text-xs rounded border border-border">
                          {entity}
                        </span>
                      ))}
                      {doc.entities.length > 5 && (
                        <span className="text-xs text-foreground-muted">
                          +{doc.entities.length - 5} autres
                        </span>
                      )}
                    </div>
                  )}

                  {doc.summary && (
                    <div className="mb-3 p-3 bg-background-secondary border-l-4 border-primary/30 rounded-r">
                      <div className="flex items-start gap-2">
                        <span className="text-primary text-xs font-medium mt-0.5">Résumé IA</span>
                      </div>
                      <p className="text-sm text-foreground mt-1 leading-relaxed">
                        {doc.summary}
                      </p>
                    </div>
                  )}
                  
                  {!doc.summary && doc.processed_at && (
                    <div className="mb-3 p-2 bg-background-secondary rounded text-xs text-foreground-muted">
                      Document traité - Résumé en cours de génération...
                    </div>
                  )}
                  
                  {!doc.processed_at && (
                    <div className="mb-3 p-2 bg-orange-50 border-l-4 border-orange-200 rounded-r text-xs text-orange-600">
                      Document en attente de traitement
                    </div>
                  )}

                  {doc.ocr_text && (
                    <p className="text-sm text-foreground-secondary line-clamp-2">
                      {doc.ocr_text}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSelectedDocument(doc);
                      viewerModal.openModal();
                    }}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(doc)}
                    disabled={isDeleting}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Pagination */}
      {total > 10 && (
        <div className="flex justify-center gap-2 mt-6">
          <Button
            variant="outline"
            disabled={page === 1}
            onClick={() => setPage(p => p - 1)}
          >
            Précédent
          </Button>
          <span className="flex items-center px-4 text-sm text-foreground-secondary">
            Page {page} / {Math.ceil(total / 10)}
          </span>
          <Button
            variant="outline"
            disabled={page >= Math.ceil(total / 10)}
            onClick={() => setPage(p => p + 1)}
          >
            Suivant
          </Button>
        </div>
      )}

      {/* Document viewer modal */}
      <Modal
        isOpen={viewerModal.isOpen}
        onClose={() => {
          viewerModal.closeModal();
          setSelectedDocument(null);
        }}
        title={selectedDocument?.filename}
        size="lg"
      >
        {selectedDocument && (
          <div className="p-6 space-y-4">
            <div>
              <h4 className="font-medium text-foreground mb-2">Informations</h4>
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-foreground-muted">Catégorie</dt>
                  <dd className="font-medium text-foreground">{selectedDocument.category}</dd>
                </div>
                <div>
                  <dt className="text-foreground-muted">Confiance</dt>
                  <dd className="font-medium text-foreground">{(selectedDocument.confidence_score * 100).toFixed(0)}%</dd>
                </div>
                {selectedDocument.document_date && (
                  <div>
                    <dt className="text-foreground-muted">Date du document</dt>
                    <dd className="font-medium text-foreground">{formatDate(selectedDocument.document_date)}</dd>
                  </div>
                )}
                {selectedDocument.amount && (
                  <div>
                    <dt className="text-foreground-muted">Montant</dt>
                    <dd className="font-medium text-foreground">{selectedDocument.amount.toFixed(2)} €</dd>
                  </div>
                )}
              </dl>
            </div>

            {selectedDocument.entities.length > 0 && (
              <div>
                <h4 className="font-medium text-foreground mb-2">Entités détectées</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedDocument.entities.map((entity, idx) => (
                    <span key={idx} className="px-3 py-1 bg-card-background text-foreground text-sm rounded border border-border">
                      {entity}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {selectedDocument.ocr_text && (
              <div>
                <h4 className="font-medium text-foreground mb-2">Texte extrait</h4>
                <div className="bg-background-secondary p-4 rounded-lg border border-border">
                  <pre className="whitespace-pre-wrap text-sm text-foreground font-mono">
                    {selectedDocument.ocr_text}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Confirm dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        onClose={confirmDialog.close}
        onConfirm={confirmDialog.onConfirm}
        title={confirmDialog.title}
        description={confirmDialog.description}
        confirmText={confirmDialog.confirmText}
        variant={confirmDialog.variant}
        isLoading={isDeleting}
      />
    </div>
  );
}