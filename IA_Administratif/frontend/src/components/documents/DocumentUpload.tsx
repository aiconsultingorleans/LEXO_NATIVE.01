'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Loader2 } from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';
import { AnimatedProgressBar, ProgressBarStyles } from '@/components/ui/AnimatedProgressBar';

interface UploadedFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error';
  progress: number;
  result?: unknown;
  error?: string;
  isAnimating?: boolean;
  startTime?: number;
}

export function DocumentUpload({ onUploadComplete }: { onUploadComplete?: () => void }) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const toast = useToast();

  const handleUpload = useCallback(async (uploadedFile: UploadedFile) => {
    const formData = new FormData();
    formData.append('file', uploadedFile.file);
    const startTime = Date.now();

    // Start animation
    setFiles(prev => prev.map(f => 
      f.id === uploadedFile.id ? { 
        ...f, 
        status: 'uploading', 
        progress: 0,
        isAnimating: true,
        startTime
      } : f
    ));

    try {
      // Pipeline unifié : Upload + OCR + Mistral + Classification en un seul appel
      const response = await fetch('http://localhost:8000/api/v1/documents/upload-and-process', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Pipeline processing failed' }));
        throw new Error(errorData.detail || 'Pipeline processing failed');
      }

      toast.info('Pipeline démarré', `Traitement complet de "${uploadedFile.file.name}" en cours...`);

      const result = await response.json();

      // Update status to success avec tous les résultats
      setFiles(prev => prev.map(f => 
        f.id === uploadedFile.id ? { 
          ...f, 
          status: 'success', 
          progress: 100,
          isAnimating: false,
          result: {
            document_id: result.id,
            category: result.category,
            confidence_score: result.confidence_score,
            summary: result.summary,
            ocr_text: result.ocr_text,
            word_count: result.ocr_text ? result.ocr_text.split(' ').length : 0,
            entities: result.entities || [],
            detected_entities: result.entities ? result.entities.reduce((acc: any, entity: string) => {
              const [type, value] = entity.split(':');
              if (type && value) {
                if (!acc[type]) acc[type] = [];
                acc[type].push(value);
              }
              return acc;
            }, {}) : {}
          }
        } : f
      ));

      // Messages de succès détaillés
      toast.success('Upload réussi', `"${uploadedFile.file.name}" a été uploadé avec succès`);
      
      if (result.category && result.category !== 'non_classes') {
        toast.success('Classification IA', `Document classé comme: ${result.category} (${(result.confidence_score * 100).toFixed(0)}% confiance)`);
      }
      
      if (result.summary) {
        toast.info('Résumé généré', 'Un résumé intelligent a été généré par l\'IA');
      }

      if (onUploadComplete) {
        onUploadComplete();
      }
      
      toast.success('Pipeline complet terminé', `"${uploadedFile.file.name}" a été entièrement traité et indexé`);

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Pipeline processing failed';
      
      setFiles(prev => prev.map(f => 
        f.id === uploadedFile.id ? { 
          ...f, 
          status: 'error',
          isAnimating: false,
          error: errorMessage 
        } : f
      ));
      
      toast.error('Erreur Pipeline', `Échec du traitement complet de "${uploadedFile.file.name}": ${errorMessage}`);
    }
  }, [onUploadComplete, toast]);

  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any[]) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      rejectedFiles.forEach(rejection => {
        const errors = rejection.errors.map((e: any) => e.message).join(', ');
        toast.error('Fichier rejeté', `"${rejection.file.name}": ${errors}`);
      });
    }

    // Handle accepted files
    if (acceptedFiles.length > 0) {
      const newFiles = acceptedFiles.map(file => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
        status: 'pending' as const,
        progress: 0
      }));
      
      setFiles(prev => [...prev, ...newFiles]);
      
      toast.info('Fichiers ajoutés', `${acceptedFiles.length} fichier${acceptedFiles.length > 1 ? 's' : ''} en cours de traitement`);
      
      // Start uploading files
      newFiles.forEach(uploadFile => {
        handleUpload(uploadFile);
      });
    }
  }, [handleUpload, toast]);

  const removeFile = (id: string) => {
    const fileToRemove = files.find(f => f.id === id);
    if (fileToRemove) {
      setFiles(prev => prev.filter(f => f.id !== id));
      
      if (fileToRemove.status === 'success') {
        toast.info('Fichier retiré', `"${fileToRemove.file.name}" retiré de la liste (le document reste sauvegardé)`);
      } else {
        toast.info('Fichier annulé', `Upload de "${fileToRemove.file.name}" annulé`);
      }
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    },
    maxSize: 50 * 1024 * 1024, // 50MB max
    multiple: true
  });

  return (
    <>
      <ProgressBarStyles />
      <div className="space-y-6">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
          isDragActive 
            ? 'border-primary bg-primary/5' 
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
        {isDragActive ? (
          <p className="text-sm text-gray-600">Déposez les fichiers ici...</p>
        ) : (
          <div>
            <p className="text-sm text-gray-600">
              Glissez-déposez des fichiers ici, ou cliquez pour sélectionner
            </p>
            <p className="text-xs text-gray-500 mt-2">
              Formats supportés: PDF, PNG, JPG, JPEG, TIFF, BMP
            </p>
          </div>
        )}
      </div>

      {/* Files list */}
      {files.length > 0 && (
        <div className="space-y-3">
          {files.map(file => (
            <div
              key={file.id}
              className="bg-white rounded-lg border p-4 flex items-center justify-between"
            >
              <div className="flex items-center space-x-3 flex-1">
                <FileText className="h-8 w-8 text-gray-400" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">
                    {file.file.name}
                  </p>
                  <div className="mt-1">
                    {file.status === 'pending' && (
                      <p className="text-xs text-gray-500">En attente...</p>
                    )}
                    {file.status === 'uploading' && (
                      <div className="flex items-center space-x-2">
                        <Loader2 className="h-3 w-3 animate-spin text-blue-500" />
                        <p className="text-xs text-blue-500">Upload en cours...</p>
                      </div>
                    )}
                    {file.status === 'processing' && (
                      <div className="flex items-center space-x-2">
                        <Loader2 className="h-3 w-3 animate-spin text-purple-500" />
                        <p className="text-xs text-purple-500">OCR + IA + Classification...</p>
                      </div>
                    )}
                    {file.status === 'success' && (
                      <div>
                        <p className="text-xs text-green-500">✓ Traité avec succès</p>
                        {file.result && typeof file.result === 'object' ? (
                          <div className="mt-2 text-xs text-gray-600">
                            <div className="flex items-center space-x-2 mb-2">
                              <p>📄 {(file.result as any).word_count || 'N/A'} mots extraits</p>
                              {(file.result as any).confidence_score && (
                                <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">
                                  {((file.result as any).confidence_score * 100).toFixed(0)}% confiance
                                </span>
                              )}
                            </div>
                            
                            {(file.result as any).category && (file.result as any).category !== 'non_classes' && (
                              <p className="text-blue-600 font-medium mb-2">
                                📂 Catégorie: {(file.result as any).category}
                              </p>
                            )}
                            
                            {(file.result as any).summary && (
                              <div className="mt-2 p-2 bg-purple-50 rounded">
                                <p className="font-medium text-purple-700">🤖 Résumé IA:</p>
                                <p className="text-purple-600 text-xs mt-1">
                                  {(file.result as any).summary}
                                </p>
                              </div>
                            )}
                            
                            {(file.result as any).detected_entities && Object.keys((file.result as any).detected_entities).length > 0 && (
                              <div className="mt-2 p-2 bg-blue-50 rounded">
                                <p className="font-medium text-blue-700">🔍 Entités détectées:</p>
                                {Object.entries((file.result as any).detected_entities).map(([key, value]: [string, any]) => (
                                  <p key={key} className="text-blue-600 text-xs">
                                    {key}: {Array.isArray(value) ? value.join(', ') : value}
                                  </p>
                                ))}
                              </div>
                            )}
                            
                            {(file.result as any).entities && (file.result as any).entities.length > 0 && (
                              <div className="mt-2 p-2 bg-gray-50 rounded">
                                <p className="font-medium text-gray-700">🏷️ Tags:</p>
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {(file.result as any).entities.slice(0, 5).map((entity: string, idx: number) => (
                                    <span key={idx} className="bg-gray-200 text-gray-700 px-1 rounded text-xs">
                                      {entity.length > 20 ? entity.substring(0, 20) + '...' : entity}
                                    </span>
                                  ))}
                                  {(file.result as any).entities.length > 5 && (
                                    <span className="text-gray-500 text-xs">
                                      +{(file.result as any).entities.length - 5} autres
                                    </span>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        ) : null}
                      </div>
                    )}
                    {file.status === 'error' && (
                      <p className="text-xs text-red-500">Erreur: {file.error}</p>
                    )}
                  </div>
                  {(file.status === 'uploading' || file.status === 'processing') && file.isAnimating && (
                    <div className="mt-2">
                      <AnimatedProgressBar
                        isActive={true}
                        estimatedDuration={8000}
                        fileName={file.file.name}
                        size="lg"
                        showText={true}
                        showPercentage={true}
                        onComplete={() => {
                          // Animation complétée
                        }}
                      />
                    </div>
                  )}
                  {(file.status === 'uploading' || file.status === 'processing') && !file.isAnimating && (
                    <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-gray-400 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: '50%' }}
                      />
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={() => removeFile(file.id)}
                className="ml-4 text-gray-400 hover:text-gray-600"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
          ))}
        </div>
      )}
      </div>
    </>
  );
}