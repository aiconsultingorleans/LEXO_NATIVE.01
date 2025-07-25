'use client';

import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { DocumentsList } from '@/components/documents/DocumentsList';
import { Card } from '@/components/ui/Card';

export default function DocumentsPage() {
  return (
    <AuthGuard requireAuth={true}>
      <MainLayout>
        <div className="space-y-8">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Tous les documents</h1>
            <p className="text-foreground-secondary mt-2">
              Gérez et consultez tous vos documents traités
            </p>
          </div>
          
          <Card className="p-6">
            <DocumentsList />
          </Card>
        </div>
      </MainLayout>
    </AuthGuard>
  );
}