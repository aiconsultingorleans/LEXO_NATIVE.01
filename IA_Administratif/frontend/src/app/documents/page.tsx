'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { DocumentsList } from '@/components/documents/DocumentsList';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

function DocumentsPageContent() {
  const searchParams = useSearchParams();
  const category = searchParams.get('category');

  // Mappage des noms de catégories pour l'affichage
  const categoryDisplayNames: Record<string, string> = {
    'factures': 'Factures',
    'attestations': 'Attestations',
    'rib': 'RIB',
    'contrats': 'Contrats',
    'impots': 'Impôts',
    'courriers': 'Courriers',
    'En attente': 'En attente',
    'non_classes': 'Non classés'
  };

  const getTitle = () => {
    if (category) {
      const displayName = categoryDisplayNames[category] || category;
      return `Documents - ${displayName}`;
    }
    return 'Tous les documents';
  };

  const getDescription = () => {
    if (category) {
      const displayName = categoryDisplayNames[category] || category;
      return `Consultez tous les documents de la catégorie ${displayName.toLowerCase()}`;
    }
    return 'Gérez et consultez tous vos documents traités';
  };

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center space-x-4 mb-4">
          {category && (
            <Button
              variant="ghost"
              size="sm"
              asChild
              className="text-foreground-secondary hover:text-foreground"
            >
              <Link href="/documents">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Tous les documents
              </Link>
            </Button>
          )}
        </div>
        
        <h1 className="text-3xl font-bold text-foreground">{getTitle()}</h1>
        <p className="text-foreground-secondary mt-2">
          {getDescription()}
        </p>
        
        {category && (
          <div className="mt-4">
            <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800">
              Filtré par: {categoryDisplayNames[category] || category}
            </span>
          </div>
        )}
      </div>
      
      <Card className="p-6">
        <DocumentsList />
      </Card>
    </div>
  );
}

export default function DocumentsPage() {
  return (
    <AuthGuard requireAuth={true}>
      <MainLayout>
        <Suspense fallback={<div>Chargement...</div>}>
          <DocumentsPageContent />
        </Suspense>
      </MainLayout>
    </AuthGuard>
  );
}