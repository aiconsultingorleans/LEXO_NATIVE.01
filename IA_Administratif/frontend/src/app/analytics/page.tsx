'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useStats } from '@/hooks/useStats';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { Button } from '@/components/ui/Button';
import DashboardWidget from '@/components/dashboard/DashboardWidget';
import DocumentsChart from '@/components/dashboard/DocumentsChart';
import KPIWidget from '@/components/dashboard/KPIWidget';
import DocumentsTimeline from '@/components/dashboard/DocumentsTimeline';
import AdvancedFilters, { FilterOptions } from '@/components/dashboard/AdvancedFilters';
import VirtualizedDocumentList from '@/components/dashboard/VirtualizedDocumentList';
import { 
  FileText, 
  Zap, 
  Shield, 
  Clock, 
  TrendingUp, 
  Users, 
  Database,
  Activity,
  Layout,
  Plus
} from 'lucide-react';

export default function AnalyticsPage() {
  return (
    <AuthGuard requireAuth={true}>
      <AnalyticsContent />
    </AuthGuard>
  );
}

function AnalyticsContent() {
  const { getUserFullName } = useAuth();
  const { stats, loading } = useStats();
  type WidgetSize = 'small' | 'medium' | 'large';
  interface Widget {
    id: string;
    size: WidgetSize;
    visible: boolean;
  }
  
  const [widgets, setWidgets] = useState<Widget[]>([
    { id: 'kpis', size: 'large', visible: true },
    { id: 'chart', size: 'large', visible: true },
    { id: 'timeline', size: 'medium', visible: true },
    { id: 'filters', size: 'medium', visible: true },
    { id: 'documents', size: 'large', visible: true }
  ]);

  // Mock KPI data
  const kpiData = [
    {
      label: 'Documents traités',
      value: stats.documentsProcessed,
      previousValue: stats.documentsProcessed - 5,
      format: 'number' as const,
      icon: FileText,
      color: 'blue' as const
    },
    {
      label: 'Précision OCR',
      value: stats.averageConfidence,
      previousValue: stats.averageConfidence - 2,
      format: 'percentage' as const,
      icon: Zap,
      color: 'green' as const
    },
    {
      label: 'Temps moyen',
      value: 4.2,
      previousValue: 4.8,
      format: 'duration' as const,
      icon: Clock,
      color: 'yellow' as const
    },
    {
      label: 'Sécurité',
      value: stats.securityStatus,
      previousValue: stats.securityStatus,
      format: 'percentage' as const,
      icon: Shield,
      color: 'green' as const
    },
    {
      label: 'Croissance',
      value: 23.5,
      previousValue: 20.1,
      format: 'percentage' as const,
      icon: TrendingUp,
      color: 'purple' as const
    },
    {
      label: 'Utilisateurs actifs',
      value: 12,
      previousValue: 10,
      format: 'number' as const,
      icon: Users,
      color: 'blue' as const
    },
    {
      label: 'Stockage utilisé',
      value: 67.3,
      previousValue: 65.1,
      format: 'percentage' as const,
      icon: Database,
      color: 'yellow' as const
    },
    {
      label: 'Performance',
      value: 98.7,
      previousValue: 97.9,
      format: 'percentage' as const,
      icon: Activity,
      color: 'green' as const
    }
  ];

  // Mock documents data for virtualized list
  const mockDocuments = Array.from({ length: 1000 }, (_, i) => ({
    id: `doc-${i}`,
    name: `Document-${i + 1}.pdf`,
    category: ['Factures', 'Contrats', 'RIB/IBAN', 'Attestations', 'Cartes'][i % 5],
    uploadDate: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000),
    status: ['processed', 'processing', 'error', 'pending'][Math.floor(Math.random() * 4)] as any,
    confidence: Math.floor(Math.random() * 30) + 70,
    size: Math.floor(Math.random() * 5000000) + 100000,
    pages: Math.floor(Math.random() * 10) + 1
  }));

  const handleWidgetResize = (id: string, size: 'small' | 'medium' | 'large') => {
    setWidgets(prev =>
      prev.map(widget =>
        widget.id === id ? { ...widget, size } : widget
      )
    );
  };

  const handleWidgetRemove = (id: string) => {
    setWidgets(prev =>
      prev.map(widget =>
        widget.id === id ? { ...widget, visible: false } : widget
      )
    );
  };

  const handleFilterChange = (filters: FilterOptions) => {
    console.log('Filters changed:', filters);
    // Implement filter logic here
  };

  const handleExport = (filters: FilterOptions) => {
    console.log('Exporting with filters:', filters);
    // Implement export logic here
  };

  const handleFilterReset = () => {
    console.log('Filters reset');
    // Implement reset logic here
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Analytics Dashboard</h1>
            <p className="text-foreground-secondary mt-2">
              Vue d'ensemble avancée de vos données documentaires
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">
              <Layout className="w-4 h-4 mr-2" />
              Personnaliser
            </Button>
            <Button size="sm">
              <Plus className="w-4 h-4 mr-2" />
              Ajouter widget
            </Button>
          </div>
        </div>

        {/* Dashboard Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-4 xl:grid-cols-6 gap-6 auto-rows-fr">
          {/* KPIs Widget */}
          {widgets.find(w => w.id === 'kpis')?.visible && (
            <div className="lg:col-span-4 xl:col-span-6 lg:row-span-1">
              <DashboardWidget
                id="kpis"
                title="Indicateurs de performance en temps réel"
                size={widgets.find(w => w.id === 'kpis')?.size}
                onResize={(size) => handleWidgetResize('kpis', size)}
                onRemove={() => handleWidgetRemove('kpis')}
                actions={
                  <div className="flex items-center text-xs text-green-500">
                    <Activity className="w-3 h-3 mr-1" />
                    Live
                  </div>
                }
              >
                <KPIWidget kpis={kpiData} refreshInterval={5000} />
              </DashboardWidget>
            </div>
          )}

          {/* Charts Widget */}
          {widgets.find(w => w.id === 'chart')?.visible && (
            <div className="lg:col-span-4 xl:col-span-4 lg:row-span-2">
              <DashboardWidget
                id="chart"
                title="Analyse des tendances"
                size={widgets.find(w => w.id === 'chart')?.size}
                onResize={(size) => handleWidgetResize('chart', size)}
                onRemove={() => handleWidgetRemove('chart')}
              >
                <DocumentsChart />
              </DashboardWidget>
            </div>
          )}

          {/* Timeline Widget */}
          {widgets.find(w => w.id === 'timeline')?.visible && (
            <div className="lg:col-span-2 xl:col-span-2 lg:row-span-2">
              <DashboardWidget
                id="timeline"
                title="Activité récente"
                size={widgets.find(w => w.id === 'timeline')?.size}
                onResize={(size) => handleWidgetResize('timeline', size)}
                onRemove={() => handleWidgetRemove('timeline')}
              >
                <DocumentsTimeline maxEvents={20} autoRefresh={true} />
              </DashboardWidget>
            </div>
          )}

          {/* Filters Widget */}
          {widgets.find(w => w.id === 'filters')?.visible && (
            <div className="lg:col-span-4 xl:col-span-6 lg:row-span-1">
              <AdvancedFilters
                onFilterChange={handleFilterChange}
                onExport={handleExport}
                onReset={handleFilterReset}
              />
            </div>
          )}

          {/* Documents List Widget */}
          {widgets.find(w => w.id === 'documents')?.visible && (
            <div className="lg:col-span-4 xl:col-span-6 lg:row-span-3">
              <VirtualizedDocumentList
                documents={mockDocuments}
                height={600}
                onDocumentSelect={(doc) => console.log('Select:', doc)}
                onDocumentEdit={(doc) => console.log('Edit:', doc)}
                onDocumentDelete={(doc) => console.log('Delete:', doc)}
                onDocumentDownload={(doc) => console.log('Download:', doc)}
              />
            </div>
          )}
        </div>

        {/* Summary Stats */}
        <div className="bg-gradient-to-r from-primary/10 to-success/10 p-6 rounded-xl border border-border">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-center">
            <div>
              <div className="text-2xl font-bold text-foreground">{mockDocuments.length}</div>
              <div className="text-sm text-foreground-secondary">Documents totaux</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">
                {mockDocuments.filter(d => d.status === 'processed').length}
              </div>
              <div className="text-sm text-foreground-secondary">Traités avec succès</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">
                {(mockDocuments.filter(d => d.status === 'processed').length / mockDocuments.length * 100).toFixed(1)}%
              </div>
              <div className="text-sm text-foreground-secondary">Taux de réussite</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-foreground">
                {(mockDocuments.reduce((acc, doc) => acc + doc.size, 0) / 1024 / 1024).toFixed(1)} MB
              </div>
              <div className="text-sm text-foreground-secondary">Volume total</div>
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}