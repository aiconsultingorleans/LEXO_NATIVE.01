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
  const [lastFetchTime, setLastFetchTime] = useState<number>(0);
  const [isFromCache, setIsFromCache] = useState(false);

  // Cache intelligent : 5 minutes pour les stats, 2 minutes pour l'activité
  const STATS_CACHE_DURATION = 5 * 60 * 1000; // 5 minutes
  const ACTIVITY_CACHE_DURATION = 2 * 60 * 1000; // 2 minutes

  const fetchStats = useCallback(async (forceRefresh: boolean = false) => {
    const now = Date.now();
    
    // Vérifier si on peut utiliser le cache
    if (!forceRefresh && lastFetchTime > 0 && (now - lastFetchTime) < STATS_CACHE_DURATION) {
      console.log('📊 Utilisation du cache pour les stats dashboard');
      setIsFromCache(true);
      return;
    }

    try {
      setError(null);
      setIsFromCache(false);
      
      console.log('📊 Récupération fresh des stats dashboard');
      const [statsData, activityData] = await Promise.all([
        apiService.getDashboardStats(),
        apiService.getRecentActivity()
      ]);
      
      setStats(statsData);
      setActivity(activityData);
      setLastFetchTime(now);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erreur lors du chargement des statistiques');
      console.error('Error fetching stats:', err);
    } finally {
      setLoading(false);
    }
  }, [lastFetchTime]);

  useEffect(() => {
    fetchStats();
    
    // Auto-refresh intelligent des statistiques
    const interval = setInterval(() => {
      fetchStats(false); // Utilise le cache si disponible
    }, refreshInterval);
    
    return () => clearInterval(interval);
  }, [fetchStats, refreshInterval]);

  return {
    stats,
    activity,
    loading,
    error,
    isFromCache,
    lastUpdate: lastFetchTime,
    refresh: (force = true) => fetchStats(force)
  };
}

export function useDocumentCount() {
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchCount = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/api/v1/documents?limit=1`, {
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