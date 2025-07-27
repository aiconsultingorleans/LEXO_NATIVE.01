'use client';

import { useState, useEffect, useCallback } from 'react';
import { useToast } from '@/contexts/ToastContext';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { 
  FolderOpen, 
  Folder, 
  FileText, 
  RefreshCw, 
  ChevronRight, 
  ChevronDown, 
  Bot,
  Lightbulb,
  AlertCircle,
  Sparkles,
  Hash,
  MoreVertical,
  Edit2,
  Move,
  Trash2,
  Check,
  X
} from 'lucide-react';

interface FolderNode {
  name: string;
  path: string;
  type: 'folder' | 'file';
  children?: FolderNode[];
  documentCount?: number;
  isAutoCreated?: boolean;
  emitter?: string;
  category?: string;
  lastModified?: string;
  size?: number;
}

interface FolderStructureResponse {
  tree: FolderNode;
  metadata: {
    totalFolders: number;
    totalDocuments: number;
    autoCreatedFolders: number;
    categories: string[];
    emitters: string[];
    lastUpdate: string;
  };
  stats: {
    pipeline: 'mistral' | 'donut';
    organizationLevel: number; // Pourcentage d'organisation
    efficiency: number; // Efficacité du classement
  };
}

interface FolderStructureProps {
  className?: string;
  showDetails?: boolean;
  maxDepth?: number;
  autoRefreshInterval?: number;
}

export function FolderStructure({ 
  className, 
  showDetails = true, 
  maxDepth = 3,
  autoRefreshInterval = 30000 
}: FolderStructureProps) {
  const [folderData, setFolderData] = useState<FolderStructureResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set(['/OCR']));
  const [lastUpdate, setLastUpdate] = useState<number>(0);
  const [editingFolder, setEditingFolder] = useState<string | null>(null);
  const [editName, setEditName] = useState<string>('');
  const [showActions, setShowActions] = useState<string | null>(null);
  const toast = useToast();

  const fetchFolderStructure = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Token d\'authentification manquant');
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/folders/structure`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          // Endpoint pas encore implémenté - données mockées
          const mockData: FolderStructureResponse = {
            tree: {
              name: 'OCR',
              path: '/OCR',
              type: 'folder',
              children: [
                {
                  name: 'factures',
                  path: '/OCR/factures',
                  type: 'folder',
                  documentCount: 15,
                  isAutoCreated: false,
                  category: 'factures',
                  children: [
                    {
                      name: 'EDF',
                      path: '/OCR/factures/EDF',
                      type: 'folder',
                      documentCount: 6,
                      isAutoCreated: true,
                      emitter: 'EDF',
                      lastModified: new Date().toISOString(),
                    },
                    {
                      name: 'Orange',
                      path: '/OCR/factures/Orange',
                      type: 'folder',
                      documentCount: 4,
                      isAutoCreated: true,
                      emitter: 'Orange',
                      lastModified: new Date().toISOString(),
                    },
                  ],
                },
                {
                  name: 'attestations',
                  path: '/OCR/attestations',
                  type: 'folder',
                  documentCount: 8,
                  isAutoCreated: false,
                  category: 'attestations',
                  children: [
                    {
                      name: 'CPAM',
                      path: '/OCR/attestations/CPAM',
                      type: 'folder',
                      documentCount: 3,
                      isAutoCreated: true,
                      emitter: 'CPAM',
                      lastModified: new Date().toISOString(),
                    },
                    {
                      name: 'CAF',
                      path: '/OCR/attestations/CAF',
                      type: 'folder',
                      documentCount: 2,
                      isAutoCreated: true,
                      emitter: 'CAF',
                      lastModified: new Date().toISOString(),
                    },
                  ],
                },
                {
                  name: 'rib',
                  path: '/OCR/rib',
                  type: 'folder',
                  documentCount: 5,
                  isAutoCreated: false,
                  category: 'rib',
                },
                {
                  name: 'carte_grise',
                  path: '/OCR/carte_grise',
                  type: 'folder',
                  documentCount: 2,
                  isAutoCreated: true,
                  category: 'carte_grise',
                  children: [
                    {
                      name: 'Prefecture_Loire',
                      path: '/OCR/carte_grise/Prefecture_Loire',
                      type: 'folder',
                      documentCount: 2,
                      isAutoCreated: true,
                      emitter: 'Préfecture Loire',
                      lastModified: new Date().toISOString(),
                    },
                  ],
                },
              ],
            },
            metadata: {
              totalFolders: 7,
              totalDocuments: 30,
              autoCreatedFolders: 5,
              categories: ['factures', 'attestations', 'rib', 'carte_grise'],
              emitters: ['EDF', 'Orange', 'CPAM', 'CAF', 'Préfecture Loire'],
              lastUpdate: new Date().toISOString(),
            },
            stats: {
              pipeline: 'donut',
              organizationLevel: 87,
              efficiency: 92,
            },
          };
          setFolderData(mockData);
          return;
        }
        
        const errorData = await response.json().catch(() => ({ detail: 'Erreur de récupération' }));
        throw new Error(errorData.detail || 'Impossible de récupérer la structure');
      }

      const data = await response.json();
      setFolderData(data);
      setLastUpdate(Date.now());

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur inconnue';
      setError(errorMessage);
      console.error('Erreur lors de la récupération de la structure:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Auto-refresh
  useEffect(() => {
    fetchFolderStructure();
    
    if (autoRefreshInterval > 0) {
      const interval = setInterval(fetchFolderStructure, autoRefreshInterval);
      return () => clearInterval(interval);
    }
  }, [fetchFolderStructure, autoRefreshInterval]);

  // Close actions menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setShowActions(null);
    };

    if (showActions) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showActions]);

  const toggleExpanded = (path: string) => {
    setExpandedPaths(prev => {
      const newSet = new Set(prev);
      if (newSet.has(path)) {
        newSet.delete(path);
      } else {
        newSet.add(path);
      }
      return newSet;
    });
  };

  const handleStartEdit = (path: string, currentName: string) => {
    setEditingFolder(path);
    setEditName(currentName);
    setShowActions(null);
  };

  const handleCancelEdit = () => {
    setEditingFolder(null);
    setEditName('');
  };

  const handleSaveEdit = async () => {
    if (!editingFolder || !editName.trim()) return;

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Token d\'authentification manquant');
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/folders/rename`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          oldPath: editingFolder,
          newName: editName.trim(),
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur de renommage' }));
        throw new Error(errorData.detail || 'Impossible de renommer le dossier');
      }

      toast.success('Dossier renommé', `Le dossier a été renommé avec succès`);
      await fetchFolderStructure(); // Rafraîchir la structure
      handleCancelEdit();

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur de renommage';
      toast.error('Erreur', errorMessage);
    }
  };

  const handleDeleteFolder = async (path: string, folderName: string) => {
    const confirmed = window.confirm(
      `Êtes-vous sûr de vouloir supprimer le dossier "${folderName}" ?\n\n` +
      'Cette action déplacera tous les documents vers le dossier parent.\n' +
      'Cette action est irréversible.'
    );

    if (!confirmed) return;

    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        throw new Error('Token d\'authentification manquant');
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/v1/folders/delete`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ path }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Erreur de suppression' }));
        throw new Error(errorData.detail || 'Impossible de supprimer le dossier');
      }

      toast.success('Dossier supprimé', `Le dossier "${folderName}" a été supprimé`);
      await fetchFolderStructure(); // Rafraîchir la structure
      setShowActions(null);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Erreur de suppression';
      toast.error('Erreur', errorMessage);
    }
  };

  const renderFolderNode = (node: FolderNode, depth: number = 0): JSX.Element => {
    if (depth > maxDepth) return <></>;

    const isExpanded = expandedPaths.has(node.path);
    const hasChildren = node.children && node.children.length > 0;
    const indentation = depth * 20;
    const isEditing = editingFolder === node.path;
    const showActionsMenu = showActions === node.path;
    const canManage = node.isAutoCreated && node.type === 'folder' && depth > 0; // Ne pas permettre la gestion du dossier racine

    return (
      <div key={node.path} className="select-none group">
        <div
          className={cn(
            'flex items-center py-2 px-3 rounded-lg transition-all duration-150 relative',
            {
              'bg-blue-50 border border-blue-200': isExpanded && hasChildren,
              'hover:bg-gray-50 cursor-pointer': hasChildren && !isEditing,
              'bg-purple-50 border border-purple-200': isEditing,
            }
          )}
          style={{ marginLeft: `${indentation}px` }}
        >
          {/* Toggle Icon */}
          <div className="w-5 h-5 flex items-center justify-center mr-2">
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown 
                  className="h-4 w-4 text-gray-400 cursor-pointer" 
                  onClick={() => !isEditing && toggleExpanded(node.path)}
                />
              ) : (
                <ChevronRight 
                  className="h-4 w-4 text-gray-400 cursor-pointer" 
                  onClick={() => !isEditing && toggleExpanded(node.path)}
                />
              )
            ) : null}
          </div>

          {/* Folder/File Icon */}
          <div className="mr-3">
            {node.type === 'folder' ? (
              isExpanded ? (
                <FolderOpen className="h-5 w-5 text-blue-500" />
              ) : (
                <Folder className="h-5 w-5 text-gray-500" />
              )
            ) : (
              <FileText className="h-4 w-4 text-gray-400" />
            )}
          </div>

          {/* Name and Info */}
          <div className="flex-1 min-w-0">
            {isEditing ? (
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="text-sm font-medium bg-white border border-purple-300 rounded px-2 py-1 flex-1 min-w-0"
                  autoFocus
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleSaveEdit();
                    if (e.key === 'Escape') handleCancelEdit();
                  }}
                />
                <button
                  onClick={handleSaveEdit}
                  className="p-1 text-green-600 hover:bg-green-100 rounded"
                >
                  <Check className="h-4 w-4" />
                </button>
                <button
                  onClick={handleCancelEdit}
                  className="p-1 text-red-600 hover:bg-red-100 rounded"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <div>
                <div className="flex items-center space-x-2">
                  <span 
                    className={cn(
                      'text-sm font-medium truncate',
                      node.type === 'folder' ? 'text-gray-900' : 'text-gray-600'
                    )}
                    onClick={() => hasChildren && !isEditing && toggleExpanded(node.path)}
                  >
                    {node.name}
                  </span>

                  {/* Auto-created badge */}
                  {node.isAutoCreated && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                      <Sparkles className="h-3 w-3 mr-1" />
                      Auto
                    </span>
                  )}

                  {/* Document count */}
                  {node.documentCount !== undefined && node.documentCount > 0 && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
                      <Hash className="h-3 w-3 mr-1" />
                      {node.documentCount}
                    </span>
                  )}
                </div>

                {/* Additional info */}
                {showDetails && (node.emitter || node.category) && (
                  <div className="flex items-center space-x-2 mt-1">
                    {node.emitter && (
                      <span className="text-xs text-gray-500">
                        Émetteur: {node.emitter}
                      </span>
                    )}
                    {node.category && (
                      <span className="text-xs text-blue-600">
                        • {node.category}
                      </span>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Actions Menu */}
          {canManage && !isEditing && (
            <div className="relative">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setShowActions(showActionsMenu ? null : node.path);
                }}
                className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded transition-all duration-150"
              >
                <MoreVertical className="h-4 w-4" />
              </button>

              {/* Actions Dropdown */}
              {showActionsMenu && (
                <div className="absolute right-0 top-full mt-1 bg-white border border-gray-200 rounded-lg shadow-lg z-10 min-w-32">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleStartEdit(node.path, node.name);
                    }}
                    className="flex items-center space-x-2 w-full px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 rounded-t-lg"
                  >
                    <Edit2 className="h-4 w-4" />
                    <span>Renommer</span>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteFolder(node.path, node.name);
                    }}
                    className="flex items-center space-x-2 w-full px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-b-lg"
                  >
                    <Trash2 className="h-4 w-4" />
                    <span>Supprimer</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Children */}
        {hasChildren && isExpanded && (
          <div className="mt-1">
            {node.children!.map(child => renderFolderNode(child, depth + 1))}
          </div>
        )}
      </div>
    );
  };

  const handleRefresh = async () => {
    await fetchFolderStructure();
    toast.success('Structure mise à jour', 'Arborescence des dossiers actualisée');
  };

  if (error) {
    return (
      <div className={cn('bg-card-background p-6 rounded-xl shadow-lg border border-card-border', className)}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-red-500" />
            Erreur structure dossiers
          </h3>
          <Button variant="ghost" size="sm" onClick={handleRefresh}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
        <div className="text-center py-8">
          <p className="text-sm text-red-600 mb-4">{error}</p>
          <Button variant="outline" onClick={handleRefresh}>
            Réessayer
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('bg-card-background rounded-xl shadow-lg border border-card-border', className)}>
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
            </svg>
            Structure intelligente
          </h3>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={cn('h-4 w-4', { 'animate-spin': loading })} />
          </Button>
        </div>

        {/* Stats */}
        {folderData && folderData.metadata && folderData.stats && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
            <div className="bg-blue-50 p-3 rounded-lg">
              <div className="text-lg font-semibold text-blue-600">
                {folderData.metadata.totalDocuments ?? 0}
              </div>
              <div className="text-xs text-blue-600">Documents</div>
            </div>
            <div className="bg-green-50 p-3 rounded-lg">
              <div className="text-lg font-semibold text-green-600">
                {folderData.metadata.totalFolders ?? 0}
              </div>
              <div className="text-xs text-green-600">Dossiers</div>
            </div>
            <div className="bg-purple-50 p-3 rounded-lg">
              <div className="text-lg font-semibold text-purple-600">
                {folderData.metadata.autoCreatedFolders ?? 0}
              </div>
              <div className="text-xs text-purple-600">Auto-créés</div>
            </div>
            <div className="bg-gray-50 p-3 rounded-lg">
              <div className="text-lg font-semibold text-gray-600">
                {folderData.stats.organizationLevel ?? 0}%
              </div>
              <div className="text-xs text-gray-600">Organisation</div>
            </div>
          </div>
        )}

        {/* Pipeline indicator */}
        {folderData && folderData.stats && (
          <div className="mt-4 flex items-center justify-between text-sm">
            <div className="flex items-center space-x-2">
              {folderData.stats.pipeline === 'donut' ? (
                <Lightbulb className="h-4 w-4 text-purple-600" />
              ) : (
                <Bot className="h-4 w-4 text-blue-600" />
              )}
              <span className="text-gray-600">
                Organisé par {folderData.stats.pipeline === 'donut' ? 'DONUT' : 'Mistral MLX'}
              </span>
            </div>
            {lastUpdate > 0 && (
              <span className="text-gray-500">
                {new Date(lastUpdate).toLocaleTimeString()}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Tree */}
      <div className="p-4 max-h-96 overflow-y-auto">
        {loading && !folderData ? (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-gray-400 mr-2" />
            <span className="text-gray-500">Chargement de la structure...</span>
          </div>
        ) : folderData ? (
          <div className="space-y-1">
            {renderFolderNode(folderData.tree)}
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <Folder className="h-8 w-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm">Aucune structure disponible</p>
          </div>
        )}
      </div>

      {/* Footer */}
      {folderData && folderData.stats && (
        <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-xl">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-1">
                <Sparkles className="h-3 w-3 text-purple-500" />
                <span>Auto-créé</span>
              </div>
              <div className="flex items-center space-x-1">
                <Hash className="h-3 w-3 text-gray-400" />
                <span>Nb. documents</span>
              </div>
            </div>
            <div>
              Efficacité: {folderData.stats.efficiency ?? 0}%
            </div>
          </div>
        </div>
      )}
    </div>
  );
}