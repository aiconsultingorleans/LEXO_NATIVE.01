const API_BASE_URL = 'http://localhost:8000/api/v1';

export interface DashboardStats {
  documentsProcessed: number;
  averageConfidence: number;
  securityStatus: number;
  pendingDocuments: number;
}

export interface ActivityItem {
  id: string;
  type: 'upload' | 'ocr_complete' | 'classification' | 'error';
  message: string;
  timestamp: string;
  status: 'success' | 'warning' | 'error' | 'info';
}

class ApiService {
  private getAuthHeaders() {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }

  async getDashboardStats(): Promise<DashboardStats> {
    try {
      // Pour l'instant, calculons les stats depuis les documents existants
      const response = await fetch(`${API_BASE_URL}/documents?limit=1000`, {
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch documents');
      }

      const data = await response.json();
      const documents = data.documents || [];

      // Calculer les vraies statistiques
      const documentsProcessed = documents.length;
      const processedDocs = documents.filter((doc: any) => doc.confidence_score > 0);
      const averageConfidence = processedDocs.length > 0 
        ? Math.round(processedDocs.reduce((sum: number, doc: any) => sum + doc.confidence_score, 0) / processedDocs.length * 100)
        : 0;
      const pendingDocuments = documents.filter((doc: any) => !doc.processed_at).length;
      const securityStatus = 100; // Toujours 100% pour local

      return {
        documentsProcessed,
        averageConfidence,
        securityStatus,
        pendingDocuments
      };
    } catch (error) {
      console.error('Error fetching dashboard stats:', error);
      // Fallback vers des stats par défaut
      return {
        documentsProcessed: 0,
        averageConfidence: 0,
        securityStatus: 100,
        pendingDocuments: 0
      };
    }
  }

  async getRecentActivity(): Promise<ActivityItem[]> {
    try {
      // Pour l'instant, simulons l'activité basée sur les documents récents
      const response = await fetch(`${API_BASE_URL}/documents?limit=10&order=desc`, {
        headers: this.getAuthHeaders()
      });

      if (!response.ok) {
        throw new Error('Failed to fetch recent documents');
      }

      const data = await response.json();
      const documents = data.documents || [];

      // Générer l'activité depuis les documents
      const activities: ActivityItem[] = documents.map((doc: any, index: number) => {
        const timestamp = new Date(doc.created_at);
        const minutesAgo = Math.floor((Date.now() - timestamp.getTime()) / (1000 * 60));
        
        let type: ActivityItem['type'] = 'upload';
        let status: ActivityItem['status'] = 'success';
        let message = `Document "${doc.filename}" uploadé`;

        if (doc.processed_at) {
          type = 'ocr_complete';
          message = `OCR terminé pour "${doc.filename}"`;
        }

        if (doc.category && doc.category !== 'autre') {
          type = 'classification';
          message = `"${doc.filename}" classé comme ${doc.category}`;
          status = 'success';
        }

        if (doc.confidence_score < 0.7) {
          status = 'warning';
        }

        return {
          id: `activity-${doc.id}`,
          type,
          message,
          timestamp: this.formatRelativeTime(minutesAgo),
          status
        };
      });

      return activities.slice(0, 5); // Limiter à 5 activités récentes
    } catch (error) {
      console.error('Error fetching recent activity:', error);
      return [];
    }
  }

  private formatRelativeTime(minutesAgo: number): string {
    if (minutesAgo < 1) return 'À l\'instant';
    if (minutesAgo < 60) return `Il y a ${minutesAgo} min`;
    if (minutesAgo < 1440) return `Il y a ${Math.floor(minutesAgo / 60)}h`;
    return `Il y a ${Math.floor(minutesAgo / 1440)} jour${Math.floor(minutesAgo / 1440) > 1 ? 's' : ''}`;
  }

  async getDocumentStats() {
    try {
      const response = await fetch(`${API_BASE_URL}/documents/stats`, {
        headers: this.getAuthHeaders()
      });

      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('Error fetching document stats:', error);
    }
    
    return null;
  }

  async getOCRHealth() {
    try {
      const response = await fetch(`${API_BASE_URL}/health`);
      if (response.ok) {
        const data = await response.json();
        return data.status === 'healthy';
      }
    } catch (error) {
      console.error('Error checking OCR health:', error);
    }
    
    return false;
  }
}

export const apiService = new ApiService();