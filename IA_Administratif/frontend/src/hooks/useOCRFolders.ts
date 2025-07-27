'use client';

import { useState, useEffect, useCallback } from 'react';

export interface FolderItem {
  name: string;
  path: string;
  type: 'folder' | 'file';
  count: number;
  children: FolderItem[];
}

export interface OCRFolderStructure {
  folders: FolderItem[];
  total_files: number;
}

interface UseOCRFoldersReturn {
  folders: FolderItem[];
  totalFiles: number;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  expandedFolders: Set<string>;
  toggleFolder: (folderPath: string) => void;
}

export function useOCRFolders(): UseOCRFoldersReturn {
  const [data, setData] = useState<OCRFolderStructure>({ folders: [], total_files: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set());

  const fetchFolders = useCallback(async () => {
    try {
      setError(null);
      const token = localStorage.getItem('access_token');
      
      // Vérifier si l'utilisateur est connecté
      if (!token) {
        setError('Connexion requise pour accéder aux dossiers OCR');
        return;
      }
      
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

      const response = await fetch(`${apiUrl}/api/v1/documents/ocr-folder-structure`, {
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Gestion spécifique des erreurs d'authentification
        if (response.status === 401) {
          setError('Session expirée - Veuillez vous reconnecter');
          return;
        }
        
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      console.error('Erreur lors du fetch des dossiers OCR:', err);
      
      // Améliorer la sérialisation des erreurs
      let errorMessage = 'Erreur inconnue';
      if (err instanceof Error) {
        errorMessage = err.message;
      } else if (typeof err === 'string') {
        errorMessage = err;
      } else if (err && typeof err === 'object') {
        // Tenter de sérialiser l'objet erreur
        try {
          errorMessage = JSON.stringify(err);
        } catch {
          errorMessage = `Erreur: ${String(err)}`;
        }
      }
      
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    setLoading(true);
    await fetchFolders();
  }, [fetchFolders]);

  const toggleFolder = useCallback((folderPath: string) => {
    setExpandedFolders(prev => {
      const newSet = new Set(prev);
      if (newSet.has(folderPath)) {
        newSet.delete(folderPath);
      } else {
        newSet.add(folderPath);
      }
      return newSet;
    });
  }, []);

  // Fetch initial data
  useEffect(() => {
    fetchFolders();
  }, [fetchFolders]);

  // Auto-refresh every 30 seconds (seulement si connecté)
  useEffect(() => {
    const interval = setInterval(() => {
      const token = localStorage.getItem('access_token');
      if (!loading && token) {
        fetchFolders();
      }
    }, 30000); // 30 secondes

    return () => clearInterval(interval);
  }, [fetchFolders, loading]);

  return {
    folders: data.folders,
    totalFiles: data.total_files,
    loading,
    error,
    refresh,
    expandedFolders,
    toggleFolder,
  };
}