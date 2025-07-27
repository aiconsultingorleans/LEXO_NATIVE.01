'use client';

import { useState } from 'react';
import { 
  FolderOpen, 
  Folder, 
  FileText, 
  ChevronRight, 
  ChevronDown,
  AlertCircle,
  RefreshCw 
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useOCRFolders, FolderItem } from '@/hooks/useOCRFolders';

interface FolderTreeItemProps {
  folder: FolderItem;
  level: number;
  isExpanded: boolean;
  onToggle: (folderPath: string) => void;
  expandedFolders: Set<string>;
}

function FolderTreeItem({ folder, level, isExpanded, onToggle, expandedFolders }: FolderTreeItemProps) {
  const hasChildren = folder.children && folder.children.length > 0;
  const indentClass = level > 0 ? `ml-${level * 4}` : '';
  const router = useRouter();

  const handleFolderClick = (e: React.MouseEvent) => {
    e.preventDefault();
    
    if (hasChildren) {
      // Si le dossier a des enfants, toggle l'expansion
      onToggle(folder.path);
    } else {
      // Si pas d'enfants, naviguer vers la page documents filtrée
      router.push(`/documents?category=${encodeURIComponent(folder.name)}`);
    }
  };

  const handleNavigateToCategory = (e: React.MouseEvent) => {
    e.stopPropagation();
    router.push(`/documents?category=${encodeURIComponent(folder.name)}`);
  };

  return (
    <div className="w-full">
      {/* Élément principal du dossier */}
      <div
        className={cn(
          'flex items-center justify-between px-3 py-2 text-sm font-medium rounded-lg transition-all duration-200 group cursor-pointer',
          'text-foreground-secondary hover:bg-hover-background hover:text-foreground',
          indentClass
        )}
        onClick={handleFolderClick}
      >
        <div className="flex items-center min-w-0 flex-1">
          {/* Icône expand/collapse */}
          {hasChildren && (
            <div className="mr-2 flex-shrink-0">
              {isExpanded ? (
                <ChevronDown className="h-4 w-4 text-foreground-muted" />
              ) : (
                <ChevronRight className="h-4 w-4 text-foreground-muted" />
              )}
            </div>
          )}
          
          {/* Icône dossier */}
          <div className="mr-2 flex-shrink-0">
            {hasChildren ? (
              isExpanded ? (
                <FolderOpen className="h-4 w-4 text-foreground-muted group-hover:text-foreground" />
              ) : (
                <Folder className="h-4 w-4 text-foreground-muted group-hover:text-foreground" />
              )
            ) : (
              <FileText className="h-4 w-4 text-foreground-muted group-hover:text-foreground" />
            )}
          </div>
          
          {/* Nom du dossier */}
          <span className="truncate flex-1">
            {folder.name}
          </span>
        </div>

        {/* Compteur de fichiers */}
        <div className="flex items-center space-x-1">
          <span 
            className={cn(
              "text-xs px-2 py-1 rounded-full font-medium transition-colors flex-shrink-0 cursor-pointer",
              "bg-background-tertiary text-foreground-muted group-hover:bg-hover-background group-hover:text-foreground"
            )}
            onClick={handleNavigateToCategory}
            title={`Voir les ${folder.count} documents de ${folder.name}`}
          >
            {folder.count}
          </span>
        </div>
      </div>

      {/* Enfants (sous-dossiers) */}
      {hasChildren && isExpanded && (
        <div className="ml-2 border-l border-border-light/50">
          {folder.children.map((child) => (
            <FolderTreeItem
              key={child.path}
              folder={child}
              level={level + 1}
              isExpanded={expandedFolders.has(child.path)}
              onToggle={onToggle}
              expandedFolders={expandedFolders}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface FolderTreeViewProps {
  className?: string;
}

export function FolderTreeView({ className }: FolderTreeViewProps) {
  const { folders, totalFiles, loading, error, refresh, expandedFolders, toggleFolder } = useOCRFolders();

  if (loading) {
    return (
      <div className={cn("space-y-2", className)}>
        <div className="flex items-center justify-between px-4 mb-3">
          <h3 className="text-xs font-semibold text-foreground-muted uppercase tracking-wider animate-pulse">
            Dossiers OCR
          </h3>
        </div>
        {/* Skeleton loader */}
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="animate-pulse">
            <div className="flex items-center justify-between px-3 py-2 rounded-lg">
              <div className="flex items-center flex-1">
                <div className="w-4 h-4 bg-gray-300 rounded mr-2"></div>
                <div className="h-4 bg-gray-300 rounded flex-1 max-w-24"></div>
              </div>
              <div className="w-6 h-5 bg-gray-300 rounded-full"></div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("space-y-2", className)}>
        <div className="flex items-center justify-between px-4 mb-3">
          <h3 className="text-xs font-semibold text-foreground-muted uppercase tracking-wider">
            Dossiers OCR
          </h3>
          <button
            onClick={refresh}
            className="text-foreground-muted hover:text-foreground transition-colors"
            title="Actualiser"
          >
            <RefreshCw className="h-3 w-3" />
          </button>
        </div>
        <div className="flex items-center px-3 py-2 text-sm text-red-600 bg-red-50 rounded-lg">
          <AlertCircle className="h-4 w-4 mr-2 flex-shrink-0" />
          <span className="text-xs">Erreur: {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("space-y-1", className)}>
      {/* En-tête avec total */}
      <div className="flex items-center justify-between px-4 mb-3">
        <h3 className="text-xs font-semibold text-foreground-muted uppercase tracking-wider">
          Dossiers OCR
        </h3>
        <div className="flex items-center space-x-2">
          <span className="text-xs text-foreground-muted">
            {totalFiles} fichiers
          </span>
          <button
            onClick={refresh}
            className="text-foreground-muted hover:text-foreground transition-colors"
            title="Actualiser"
          >
            <RefreshCw className="h-3 w-3" />
          </button>
        </div>
      </div>

      {/* Liste des dossiers avec scroll si > 7 */}
      <div className={cn(
        "space-y-1",
        folders.length > 7 ? "max-h-80 overflow-y-auto pr-2" : ""
      )}>
        {folders.length > 0 ? (
          folders.map((folder) => (
            <FolderTreeItem
              key={folder.path}
              folder={folder}
              level={0}
              isExpanded={expandedFolders.has(folder.path)}
              onToggle={toggleFolder}
              expandedFolders={expandedFolders}
            />
          ))
        ) : (
          <div className="text-center py-4 text-foreground-muted">
            <Folder className="h-8 w-8 text-gray-300 mx-auto mb-2" />
            <p className="text-sm">Aucun dossier trouvé</p>
            <p className="text-xs text-gray-400 mt-1">
              Les dossiers apparaîtront ici une fois créés
            </p>
          </div>
        )}
      </div>
    </div>
  );
}