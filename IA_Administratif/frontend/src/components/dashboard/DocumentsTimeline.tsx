'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FileText, CheckCircle, XCircle, Clock, Filter, Calendar } from 'lucide-react';

interface TimelineEvent {
  id: string;
  timestamp: Date;
  type: 'upload' | 'processed' | 'error' | 'classified';
  title: string;
  description: string;
  documentName: string;
  status: 'success' | 'error' | 'processing' | 'pending';
  category?: string;
  confidence?: number;
}

interface DocumentsTimelineProps {
  maxEvents?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function DocumentsTimeline({ 
  maxEvents = 50, 
  autoRefresh = true, 
  refreshInterval = 30000 
}: DocumentsTimelineProps) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [filter, setFilter] = useState<'all' | 'upload' | 'processed' | 'error'>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const generateMockEvents = (): TimelineEvent[] => {
      const mockEvents: TimelineEvent[] = [];
      const types: TimelineEvent['type'][] = ['upload', 'processed', 'error', 'classified'];
      const statuses: TimelineEvent['status'][] = ['success', 'error', 'processing', 'pending'];
      const categories = ['Factures', 'Contrats', 'RIB/IBAN', 'Attestations', 'Cartes'];
      const documentNames = [
        'facture_edf_2024.pdf',
        'contrat_location.pdf',
        'rib_credit_agricole.pdf',
        'attestation_assurance.jpg',
        'carte_identite.png',
        'devis_travaux.pdf',
        'bulletin_salaire.pdf'
      ];

      for (let i = 0; i < maxEvents; i++) {
        const timestamp = new Date();
        timestamp.setMinutes(timestamp.getMinutes() - i * 15);

        const type = types[Math.floor(Math.random() * types.length)];
        const status = type === 'error' ? 'error' : statuses[Math.floor(Math.random() * statuses.length)];
        const documentName = documentNames[Math.floor(Math.random() * documentNames.length)];
        const category = categories[Math.floor(Math.random() * categories.length)];

        let title = '';
        let description = '';

        switch (type) {
          case 'upload':
            title = 'Document uploadé';
            description = `${documentName} a été ajouté à la plateforme`;
            break;
          case 'processed':
            title = 'OCR terminé';
            description = `Extraction de texte terminée pour ${documentName}`;
            break;
          case 'error':
            title = 'Erreur de traitement';
            description = `Échec du traitement de ${documentName}`;
            break;
          case 'classified':
            title = 'Document classifié';
            description = `${documentName} classé en ${category}`;
            break;
        }

        mockEvents.push({
          id: `event-${i}`,
          timestamp,
          type,
          title,
          description,
          documentName,
          status,
          category: type === 'classified' ? category : undefined,
          confidence: type === 'classified' ? Math.floor(Math.random() * 30) + 70 : undefined
        });
      }

      return mockEvents.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    };

    const loadEvents = () => {
      setLoading(true);
      setTimeout(() => {
        setEvents(generateMockEvents());
        setLoading(false);
      }, 500);
    };

    loadEvents();

    if (autoRefresh) {
      const interval = setInterval(loadEvents, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [maxEvents, autoRefresh, refreshInterval]);

  const filteredEvents = events.filter(event => {
    if (filter === 'all') return true;
    return event.type === filter;
  });

  const getEventIcon = (type: TimelineEvent['type'], status: TimelineEvent['status']) => {
    if (status === 'error') return XCircle;
    if (status === 'processing') return Clock;
    
    switch (type) {
      case 'upload':
        return FileText;
      case 'processed':
      case 'classified':
        return CheckCircle;
      default:
        return FileText;
    }
  };

  const getEventColor = (status: TimelineEvent['status']) => {
    switch (status) {
      case 'success':
        return 'text-green-500 bg-green-500/10';
      case 'error':
        return 'text-red-500 bg-red-500/10';
      case 'processing':
        return 'text-yellow-500 bg-yellow-500/10';
      case 'pending':
        return 'text-gray-500 bg-gray-500/10';
      default:
        return 'text-gray-500 bg-gray-500/10';
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    const now = new Date();
    const diffInMinutes = Math.floor((now.getTime() - timestamp.getTime()) / (1000 * 60));
    
    if (diffInMinutes < 1) return 'À l\'instant';
    if (diffInMinutes < 60) return `Il y a ${diffInMinutes}min`;
    if (diffInMinutes < 1440) return `Il y a ${Math.floor(diffInMinutes / 60)}h`;
    return timestamp.toLocaleDateString('fr-FR', { 
      day: 'numeric', 
      month: 'short', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  if (loading) {
    return (
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-foreground mb-6 flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary" />
          Timeline des documents
        </h3>
        <div className="space-y-4">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="flex items-start space-x-4 animate-pulse">
              <div className="w-10 h-10 bg-gray-200 rounded-full"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-foreground flex items-center gap-2">
          <Calendar className="w-5 h-5 text-primary" />
          Timeline des documents
        </h3>
        
        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-foreground-secondary" />
          <div className="flex bg-background-secondary rounded-lg p-1">
            <Button
              size="sm"
              variant={filter === 'all' ? 'primary' : 'ghost'}
              onClick={() => setFilter('all')}
              className="h-8 px-3 text-xs"
            >
              Tout
            </Button>
            <Button
              size="sm"
              variant={filter === 'upload' ? 'primary' : 'ghost'}
              onClick={() => setFilter('upload')}
              className="h-8 px-3 text-xs"
            >
              Upload
            </Button>
            <Button
              size="sm"
              variant={filter === 'processed' ? 'primary' : 'ghost'}
              onClick={() => setFilter('processed')}
              className="h-8 px-3 text-xs"
            >
              OCR
            </Button>
            <Button
              size="sm"
              variant={filter === 'error' ? 'primary' : 'ghost'}
              onClick={() => setFilter('error')}
              className="h-8 px-3 text-xs"
            >
              Erreurs
            </Button>
          </div>
        </div>
      </div>

      <div className="space-y-4 max-h-96 overflow-y-auto">
        {filteredEvents.map((event, index) => {
          const Icon = getEventIcon(event.type, event.status);
          const colorClasses = getEventColor(event.status);

          return (
            <div key={event.id} className="flex items-start space-x-4">
              <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${colorClasses}`}>
                <Icon className="w-5 h-5" />
              </div>
              
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-medium text-foreground">{event.title}</p>
                  <p className="text-xs text-foreground-muted">{formatTimestamp(event.timestamp)}</p>
                </div>
                
                <p className="text-sm text-foreground-secondary mt-1">{event.description}</p>
                
                {event.category && event.confidence && (
                  <div className="flex items-center space-x-4 mt-2">
                    <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-primary/10 text-primary">
                      {event.category}
                    </span>
                    <span className="text-xs text-foreground-muted">
                      Confiance: {event.confidence}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        
        {filteredEvents.length === 0 && (
          <div className="text-center py-8 text-foreground-secondary">
            <Calendar className="h-8 w-8 text-foreground-muted mx-auto mb-2" />
            <p className="text-sm">Aucun événement à afficher</p>
            <p className="text-xs text-foreground-muted mt-1">
              Les activités apparaîtront ici une fois que vous commencerez à traiter des documents
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}

export default DocumentsTimeline;