'use client';

import { useState, useEffect } from 'react';
import { FileText, Calendar, Tag, Eye, Download, Trash2, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { useAuth } from '@/hooks/useAuth';

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
  created_at: string;
  processed_at: string | null;
}

interface DocumentsListResponse {
  documents: Document[];
  total: number;
  page: number;
  limit: number;
}

export function DocumentsList() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const { user } = useAuth();

  const fetchDocuments = async () => {
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
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [page]);

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

  const handleDelete = async (id: number) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer ce document ?')) return;

    try {
      const response = await fetch(`http://localhost:8000/api/v1/documents/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });

      if (response.ok) {
        await fetchDocuments();
      }
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Mes documents</h2>
        <p className="text-sm text-gray-500">{total} document{total > 1 ? 's' : ''}</p>
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
                    <h3 className="font-medium text-gray-900">{doc.filename}</h3>
                    <span className={`px-2 py-1 text-xs font-medium rounded-full ${getCategoryColor(doc.category)}`}>
                      {doc.category}
                    </span>
                    {doc.confidence_score > 0 && (
                      <span className="text-xs text-gray-500">
                        Confiance: {(doc.confidence_score * 100).toFixed(0)}%
                      </span>
                    )}
                  </div>

                  <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-3">
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
                        <span key={idx} className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded">
                          {entity}
                        </span>
                      ))}
                      {doc.entities.length > 5 && (
                        <span className="text-xs text-gray-500">
                          +{doc.entities.length - 5} autres
                        </span>
                      )}
                    </div>
                  )}

                  {doc.ocr_text && (
                    <p className="text-sm text-gray-600 line-clamp-2">
                      {doc.ocr_text}
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-2 ml-4">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setSelectedDocument(doc)}
                  >
                    <Eye className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(doc.id)}
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
          <span className="flex items-center px-4 text-sm text-gray-600">
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
      {selectedDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6">
            <div className="flex justify-between items-start mb-4">
              <h3 className="text-xl font-semibold">{selectedDocument.filename}</h3>
              <button
                onClick={() => setSelectedDocument(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="h-6 w-6" />
              </button>
            </div>
            
            <div className="space-y-4">
              <div>
                <h4 className="font-medium text-gray-700 mb-2">Informations</h4>
                <dl className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <dt className="text-gray-500">Catégorie</dt>
                    <dd className="font-medium">{selectedDocument.category}</dd>
                  </div>
                  <div>
                    <dt className="text-gray-500">Confiance</dt>
                    <dd className="font-medium">{(selectedDocument.confidence_score * 100).toFixed(0)}%</dd>
                  </div>
                  {selectedDocument.document_date && (
                    <div>
                      <dt className="text-gray-500">Date du document</dt>
                      <dd className="font-medium">{formatDate(selectedDocument.document_date)}</dd>
                    </div>
                  )}
                  {selectedDocument.amount && (
                    <div>
                      <dt className="text-gray-500">Montant</dt>
                      <dd className="font-medium">{selectedDocument.amount.toFixed(2)} €</dd>
                    </div>
                  )}
                </dl>
              </div>

              {selectedDocument.entities.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Entités détectées</h4>
                  <div className="flex flex-wrap gap-2">
                    {selectedDocument.entities.map((entity, idx) => (
                      <span key={idx} className="px-3 py-1 bg-gray-100 text-gray-700 text-sm rounded">
                        {entity}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedDocument.ocr_text && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">Texte extrait</h4>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <pre className="whitespace-pre-wrap text-sm text-gray-700 font-mono">
                      {selectedDocument.ocr_text}
                    </pre>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Fix for X import
import { X } from 'lucide-react';