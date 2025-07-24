'use client';

import { useState, useEffect, useCallback } from 'react';
import { apiService, DashboardStats, ActivityItem } from '@/services/api';

export function useStats(refreshInterval: number = 30000) {
  const [stats, setStats] = useState<DashboardStats>({
    documentsProcessed: 0,
    averageConfidence: 0,
    securityStatus: 100,
    pendingDocuments: 0
  });
  const [activity, setActivity] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    try {
      setError(null);
      const [statsData, activityData] = await Promise.all([
        apiService.getDashboardStats(),
        apiService.getRecentActivity()
      ]);
      
      setStats(statsData);
      setActivity(activityData);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors du chargement des statistiques');
      console.error('Error fetching stats:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
    
    // Auto-refresh des statistiques
    const interval = setInterval(fetchStats, refreshInterval);
    
    return () => clearInterval(interval);
  }, [fetchStats, refreshInterval]);

  return {
    stats,
    activity,
    loading,
    error,
    refresh: fetchStats
  };
}

export function useDocumentCount() {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/v1/documents?limit=1', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('access_token')}`
          }
        });
        
        if (response.ok) {
          const data = await response.json();
          setCount(data.total || 0);
        }
      } catch (error) {
        console.error('Error fetching document count:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchCount();
  }, []);

  return { count, loading };
}