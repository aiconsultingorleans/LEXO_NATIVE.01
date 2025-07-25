'use client';

import { useState } from 'react';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { DocumentUpload } from '@/components/documents/DocumentUpload';
import { DocumentsList } from '@/components/documents/DocumentsList';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Upload, FileText } from 'lucide-react';

export default function UploadPage() {
  return (
    <AuthGuard requireAuth={true}>
      <UploadContent />
    </AuthGuard>
  );
}

function UploadContent() {
  const [refreshList, setRefreshList] = useState(0);
  const [showRecent, setShowRecent] = useState(false);

  return (
    <MainLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Upload de documents</h1>
          <p className="text-foreground-secondary mt-2">
            Uploadez et traitez vos documents avec OCR intelligent
          </p>
        </div>

        <Card className="p-6">
          <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
            <Upload className="w-5 h-5 text-primary" />
            Nouveau document
          </h3>
          <DocumentUpload 
            onUploadComplete={() => {
              setRefreshList(prev => prev + 1);
              setShowRecent(true);
            }}
          />
        </Card>

        <div className="flex justify-center">
          <Button 
            variant="outline" 
            onClick={() => setShowRecent(!showRecent)}
            className="flex items-center gap-2"
          >
            <FileText className="w-4 h-4" />
            {showRecent ? 'Masquer' : 'Voir'} les documents récents
          </Button>
        </div>

        {showRecent && (
          <Card className="p-6">
            <h3 className="text-lg font-semibold text-foreground mb-6">Documents récents</h3>
            <DocumentsList key={refreshList} />
          </Card>
        )}
      </div>
    </MainLayout>
  );
}