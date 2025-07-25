'use client';

import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, FileText, X, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/hooks/useAuth';

interface UploadedFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'processing' | 'success' | 'error';
  progress: number;
  result?: any;
  error?: string;
}

export function DocumentUpload({ onUploadComplete }: { onUploadComplete?: () => void }) {
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const { user } = useAuth();

  const onDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles = acceptedFiles.map(file => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending' as const,
      progress: 0
    }));
    setFiles(prev => [...prev, ...newFiles]);
    
    // Start uploading files
    newFiles.forEach(uploadFile => {
      handleUpload(uploadFile);
    });
  }, []);

  const handleUpload = async (uploadedFile: UploadedFile) => {
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
        throw new Error('Upload failed');
      }

      const document = await uploadResponse.json();

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
        throw new Error('OCR processing failed');
      }

      const ocrResult = await ocrResponse.json();

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
          const analysisResponse = await fetch('http://localhost:8000/api/v1/documents/analyze', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
              'Content-Type': 'application/json'
            },
            body: JSON.stringify({
              text: ocrResult.text,
              filename: uploadedFile.file.name
            })
          });

          if (analysisResponse.ok) {
            const analysis = await analysisResponse.json();
            setFiles(prev => prev.map(f => 
              f.id === uploadedFile.id ? { 
                ...f, 
                result: { ...f.result, analysis } 
              } : f
            ));
          }
        } catch (error) {
          console.error('Analysis failed:', error);
        }
      }

      if (onUploadComplete) {
        onUploadComplete();
      }
    } catch (error) {
      setFiles(prev => prev.map(f => 
        f.id === uploadedFile.id ? { 
          ...f, 
          status: 'error', 
          error: error instanceof Error ? error.message : 'Upload failed' 
        } : f
      ));
    }
  };

  const removeFile = (id: string) => {
    setFiles(prev => prev.filter(f => f.id !== id));
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp']
    }
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
                        {file.result && (
                          <div className="mt-2 text-xs text-gray-600">
                            <p>Texte extrait: {file.result.word_count} mots</p>
                            {file.result.confidence && (
                              <p>Confiance: {(file.result.confidence * 100).toFixed(1)}%</p>
                            )}
                            {file.result.analysis && (
                              <div className="mt-1 p-2 bg-gray-50 rounded">
                                <p className="font-medium">Analyse IA:</p>
                                <p>Type: {file.result.analysis.classification?.type}</p>
                                {file.result.analysis.entities?.dates?.length > 0 && (
                                  <p>Dates: {file.result.analysis.entities.dates.join(', ')}</p>
                                )}
                                {file.result.analysis.entities?.amounts?.length > 0 && (
                                  <p>Montants: {file.result.analysis.entities.amounts.join(', ')}</p>
                                )}
                              </div>
                            )}
                          </div>
                        )}
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