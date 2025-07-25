'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Loader2 } from 'lucide-react';
import { useToast } from '@/contexts/ToastContext';

interface UploadedFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error';
  progress: number;
  result?: unknown;
  error?: string;
}

export function DocumentUpload({ onUploadComplete }: { onUploadComplete?: () => void }) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const toast = useToast();

  const handleUpload = useCallback(async (uploadedFile: UploadedFile) => {
    const formData = new FormData();
    formData.append('file', uploadedFile.file);

    // Update status to uploading
    setFiles(prev => prev.map(f => 
      f.id === uploadedFile.id ? { ...f, status: 'uploading', progress: 30 } : f
    ));

    try {
      // Upload file
      const uploadResponse = await fetch('http://localhost:8000/api/v1/documents/upload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: formData
      });

      if (!uploadResponse.ok) {
        const errorData = await uploadResponse.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(errorData.detail || 'Upload failed');
      }

      const uploadResult = await uploadResponse.json();
      toast.success('Upload réussi', `Le fichier "${uploadedFile.file.name}" a été uploadé avec succès`);

      // Update status to processing
      setFiles(prev => prev.map(f => 
        f.id === uploadedFile.id ? { ...f, status: 'processing', progress: 60 } : f
      ));

      // Process OCR
      const ocrFormData = new FormData();
      ocrFormData.append('file', uploadedFile.file);

      const ocrResponse = await fetch('http://localhost:8000/api/v1/ocr/process', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: ocrFormData
      });

      if (!ocrResponse.ok) {
        const errorData = await ocrResponse.json().catch(() => ({ detail: 'OCR processing failed' }));
        throw new Error(errorData.detail || 'OCR processing failed');
      }

      const ocrResult = await ocrResponse.json();
      toast.success('OCR terminé', `Le texte a été extrait de "${uploadedFile.file.name}" avec ${(ocrResult.confidence * 100).toFixed(0)}% de confiance`);

      // Update status to success
      setFiles(prev => prev.map(f => 
        f.id === uploadedFile.id ? { 
          ...f, 
          status: 'success', 
          progress: 100,
          result: ocrResult 
        } : f
      ));

      // Optional: Process with Mistral for advanced analysis
      if (ocrResult.text) {
        try {
          const analysisResponse = await fetch('http://localhost:8000/api/v1/intelligence/analyze', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              text: ocrResult.text,
              analysis_types: ['classification', 'key_extraction']
            })
          });

          if (analysisResponse.ok) {
            const analysisData = await analysisResponse.json();
            setFiles(prev => prev.map(f => 
              f.id === uploadedFile.id ? { 
                ...f, 
                result: { ...(f.result || {}), analysis: analysisData.result } 
              } : f
            ));
            
            if (analysisData.result?.classification?.type) {
              toast.info('Classification IA', `Document classé comme: ${analysisData.result.classification.type}`);
            }
          }
        } catch (error) {
          toast.warning('Analyse IA', 'L\'analyse avancée a échoué, mais l\'OCR de base a réussi');
        }
      }

      if (onUploadComplete) {
        onUploadComplete();
      }
      
      toast.success('Traitement terminé', `"${uploadedFile.file.name}" a été entièrement traité et indexé`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      
      setFiles(prev => prev.map(f => 
        f.id === uploadedFile.id ? { 
          ...f, 
          status: 'error', 
          error: errorMessage 
        } : f
      ));
      
      toast.error('Erreur de traitement', `Échec du traitement de "${uploadedFile.file.name}": ${errorMessage}`);
    }
  }, [onUploadComplete]);

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
                        <p className="text-xs text-purple-500">Traitement OCR...</p>
                      </div>
                    )}
                    {file.status === 'success' && (
                      <div>
                        <p className="text-xs text-green-500">✓ Traité avec succès</p>
                        {file.result && typeof file.result === 'object' ? (
                          <div className="mt-2 text-xs text-gray-600">
                            <p>Texte extrait: {(file.result as any).word_count || 'N/A'} mots</p>
                            {(file.result as any).confidence && (
                              <p>Confiance: {((file.result as any).confidence * 100).toFixed(1)}%</p>
                            )}
                            {(file.result as any).analysis && (
                              <div className="mt-1 p-2 bg-gray-50 rounded">
                                <p className="font-medium">Analyse IA:</p>
                                <p>Type: {(file.result as any).analysis.classification?.type}</p>
                                {(file.result as any).analysis.entities?.dates?.length > 0 && (
                                  <p>Dates: {(file.result as any).analysis.entities.dates.join(', ')}</p>
                                )}
                                {(file.result as any).analysis.entities?.amounts?.length > 0 && (
                                  <p>Montants: {(file.result as any).analysis.entities.amounts.join(', ')}</p>
                                )}
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
                  {(file.status === 'uploading' || file.status === 'processing') && (
                    <div className="mt-2 w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                        style={{ width: `${file.progress}%` }}
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
  );
}