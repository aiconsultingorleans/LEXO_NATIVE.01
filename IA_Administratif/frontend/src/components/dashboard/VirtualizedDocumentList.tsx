'use client';

import { useState, useEffect, useMemo } from 'react';
import { FixedSizeList as List } from 'react-window';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { FileText, Download, Edit, Trash2, Search, Eye } from 'lucide-react';

interface Document {
  id: string;
  name: string;
  category: string;
  uploadDate: Date;
  status: 'processed' | 'processing' | 'error' | 'pending';
  confidence: number;
  size: number;
  pages?: number;
  thumbnail?: string;
}

interface VirtualizedDocumentListProps {
  documents: Document[];
  onDocumentSelect?: (document: Document) => void;
  onDocumentEdit?: (document: Document) => void;
  onDocumentDelete?: (document: Document) => void;
  onDocumentDownload?: (document: Document) => void;
  height?: number;
  itemHeight?: number;
}

const ITEM_HEIGHT = 80;

export function VirtualizedDocumentList({
  documents,
  onDocumentSelect,
  onDocumentEdit,
  onDocumentDelete,
  onDocumentDownload,
  height = 400,
  itemHeight = ITEM_HEIGHT
}: VirtualizedDocumentListProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'name' | 'uploadDate' | 'category' | 'status'>('uploadDate');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');

  const filteredAndSortedDocuments = useMemo(() => {
    let filtered = documents.filter(doc =>
      doc.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      doc.category.toLowerCase().includes(searchTerm.toLowerCase())
    );

    filtered.sort((a, b) => {
      let aValue: any = a[sortBy];
      let bValue: any = b[sortBy];

      if (sortBy === 'uploadDate') {
        aValue = a.uploadDate.getTime();
        bValue = b.uploadDate.getTime();
      }

      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = bValue.toLowerCase();
      }

      if (sortOrder === 'asc') {
        return aValue < bValue ? -1 : aValue > bValue ? 1 : 0;
      } else {
        return aValue > bValue ? -1 : aValue < bValue ? 1 : 0;
      }
    });

    return filtered;
  }, [documents, searchTerm, sortBy, sortOrder]);

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusColor = (status: Document['status']) => {
    switch (status) {
      case 'processed':
        return 'bg-green-100 text-green-800';
      case 'processing':
        return 'bg-yellow-100 text-yellow-800';
      case 'error':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status: Document['status']) => {
    switch (status) {
      case 'processed':
        return 'Traité';
      case 'processing':
        return 'En cours';
      case 'error':
        return 'Erreur';
      case 'pending':
        return 'En attente';
      default:
        return 'Inconnu';
    }
  };

  const DocumentItem = ({ index, style }: { index: number; style: any }) => {
    const document = filteredAndSortedDocuments[index];

    return (
      <div style={style} className="px-4">
        <div className="flex items-center space-x-4 py-3 border-b border-border-light hover:bg-hover-background transition-colors rounded-lg px-3">
          {/* Document Icon/Thumbnail */}
          <div className="flex-shrink-0">
            {document.thumbnail ? (
              <img
                src={document.thumbnail}
                alt={document.name}
                className="w-12 h-12 object-cover rounded-lg border border-border"
              />
            ) : (
              <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-primary" />
              </div>
            )}
          </div>

          {/* Document Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium text-foreground truncate">
                {document.name}
              </h4>
              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(document.status)}`}>
                {getStatusLabel(document.status)}
              </span>
            </div>
            
            <div className="flex items-center space-x-4 mt-1 text-xs text-foreground-secondary">
              <span className="inline-flex items-center px-2 py-1 rounded-full bg-background-secondary">
                {document.category}
              </span>
              <span>{formatFileSize(document.size)}</span>
              {document.pages && <span>{document.pages} page(s)</span>}
              <span>{document.confidence}% confiance</span>
              <span>{document.uploadDate.toLocaleDateString('fr-FR')}</span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center space-x-1">
            {onDocumentSelect && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDocumentSelect(document)}
                className="p-2"
              >
                <Eye className="w-4 h-4" />
              </Button>
            )}
            
            {onDocumentDownload && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDocumentDownload(document)}
                className="p-2"
              >
                <Download className="w-4 h-4" />
              </Button>
            )}
            
            {onDocumentEdit && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDocumentEdit(document)}
                className="p-2"
              >
                <Edit className="w-4 h-4" />
              </Button>
            )}
            
            {onDocumentDelete && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDocumentDelete(document)}
                className="p-2 text-error hover:text-error"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <Card className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-foreground">
          Documents ({filteredAndSortedDocuments.length})
        </h3>
        
        <div className="flex items-center space-x-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
            <Input
              type="text"
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10 w-64"
            />
          </div>

          {/* Sort Options */}
          <div className="flex items-center space-x-2">
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as 'name' | 'uploadDate' | 'category' | 'status')}
              className="px-3 py-2 text-sm border border-border rounded-md bg-card-background text-foreground"
            >
              <option value="uploadDate">Date</option>
              <option value="name">Nom</option>
              <option value="category">Catégorie</option>
              <option value="status">Statut</option>
            </select>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            >
              {sortOrder === 'asc' ? '↑' : '↓'}
            </Button>
          </div>
        </div>
      </div>

      {/* Virtualized List */}
      {filteredAndSortedDocuments.length > 0 ? (
        <List
          height={height}
          width="100%"
          itemCount={filteredAndSortedDocuments.length}
          itemSize={itemHeight}
          className="border border-border rounded-lg"
        >
          {DocumentItem}
        </List>
      ) : (
        <div className="text-center py-12">
          <FileText className="h-12 w-12 text-foreground-muted mx-auto mb-4" />
          <h3 className="text-lg font-medium text-foreground mb-2">
            {searchTerm ? 'Aucun résultat' : 'Aucun document'}
          </h3>
          <p className="text-foreground-secondary">
            {searchTerm 
              ? `Aucun document ne correspond à "${searchTerm}"`
              : 'Uploadez votre premier document pour commencer'
            }
          </p>
        </div>
      )}

      {/* Performance Info */}
      <div className="flex justify-between items-center mt-4 text-xs text-foreground-muted">
        <span>Performance: Virtualisation activée</span>
        <span>
          Affichage: {Math.min(Math.ceil(height / itemHeight), filteredAndSortedDocuments.length)} / {filteredAndSortedDocuments.length} éléments
        </span>
      </div>
    </Card>
  );
}

export default VirtualizedDocumentList;