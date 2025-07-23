'use client';

import { useAuth } from '@/hooks/useAuth';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import { FileText, Upload, Zap, Shield } from 'lucide-react';

export default function DashboardPage() {
  return (
    <AuthGuard requireAuth={true}>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardContent() {
  const { getUserFullName } = useAuth();

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Hero Section */}
        <div className="text-center bg-gradient-to-br from-background-secondary to-background-tertiary p-8 rounded-2xl border border-card-border">
          <div className="mx-auto w-20 h-20 bg-gradient-to-br from-primary to-primary-dark rounded-2xl shadow-lg flex items-center justify-center mb-6">
            <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h1 className="text-4xl font-bold text-foreground mb-4">
            Bienvenue sur LEXO v1
          </h1>
          <p className="text-xl text-foreground-secondary mb-8">
            Bonjour {getUserFullName()}, votre assistant IA pour la gestion administrative intelligente
          </p>
          <div className="flex justify-center space-x-4">
            <Button size="lg" className="shadow-lg">
              <Upload className="mr-2 h-5 w-5" />
              Uploader un document
            </Button>
            <Button variant="outline" size="lg">
              <FileText className="mr-2 h-5 w-5" />
              Voir mes documents
            </Button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border hover:border-border-light transition-all duration-200">
            <div className="flex items-center">
              <div className="p-3 bg-primary/10 rounded-xl">
                <FileText className="h-6 w-6 text-primary" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-foreground-secondary">Documents traités</p>
                <p className="text-2xl font-bold text-foreground">42</p>
              </div>
            </div>
          </div>

          <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border hover:border-border-light transition-all duration-200">
            <div className="flex items-center">
              <div className="p-3 bg-success/10 rounded-xl">
                <Zap className="h-6 w-6 text-success" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-foreground-secondary">Précision OCR</p>
                <p className="text-2xl font-bold text-foreground">98%</p>
              </div>
            </div>
          </div>

          <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border hover:border-border-light transition-all duration-200">
            <div className="flex items-center">
              <div className="p-3 bg-warning/10 rounded-xl">
                <Shield className="h-6 w-6 text-warning" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-foreground-secondary">Sécurité</p>
                <p className="text-2xl font-bold text-foreground">100%</p>
              </div>
            </div>
          </div>

          <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border hover:border-border-light transition-all duration-200">
            <div className="flex items-center">
              <div className="p-3 bg-purple-500/10 rounded-xl">
                <FileText className="h-6 w-6 text-purple-400" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-foreground-secondary">En attente</p>
                <p className="text-2xl font-bold text-foreground">3</p>
              </div>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border">
          <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Actions rapides
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Button variant="outline" className="justify-start h-12 hover:bg-hover-background">
              <Upload className="mr-3 h-5 w-5" />
              Glisser-déposer des documents
            </Button>
            <Button variant="outline" className="justify-start h-12 hover:bg-hover-background">
              <FileText className="mr-3 h-5 w-5" />
              Rechercher dans mes documents
            </Button>
            <Button variant="outline" className="justify-start h-12 hover:bg-hover-background">
              <Zap className="mr-3 h-5 w-5" />
              Générer un rapport
            </Button>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="bg-card-background p-6 rounded-xl shadow-lg border border-card-border">
          <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
            <svg className="w-5 h-5 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Activité récente
          </h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-success/5 border border-success/10">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-success rounded-full mr-4"></div>
                <span className="text-sm text-foreground">Facture EDF classée automatiquement</span>
              </div>
              <span className="text-xs text-foreground-muted bg-background-secondary px-2 py-1 rounded-full">Il y a 5 min</span>
            </div>
            <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-primary/5 border border-primary/10">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-primary rounded-full mr-4"></div>
                <span className="text-sm text-foreground">RIB Crédit Agricole traité</span>
              </div>
              <span className="text-xs text-foreground-muted bg-background-secondary px-2 py-1 rounded-full">Il y a 12 min</span>
            </div>
            <div className="flex items-center justify-between py-3 px-4 rounded-lg bg-warning/5 border border-warning/10">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-warning rounded-full mr-4"></div>
                <span className="text-sm text-foreground">Document en attente de classification</span>
              </div>
              <span className="text-xs text-foreground-muted bg-background-secondary px-2 py-1 rounded-full">Il y a 1h</span>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}