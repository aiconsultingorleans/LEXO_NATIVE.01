'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';

export const ActivityTracker = ({ children }: { children: React.ReactNode }) => {
  const { updateActivity, checkSessionExpiration, isAuthenticated } = useAuthStore();

  useEffect(() => {
    if (!isAuthenticated) return;

    // Fonction pour mettre à jour l'activité
    const handleActivity = () => {
      updateActivity();
    };

    // Événements à surveiller pour l'activité utilisateur
    const events = [
      'mousedown',
      'mouseup',
      'keypress',
      'scroll',
      'touchstart',
      'click'
    ];

    // Ajouter les listeners
    events.forEach(event => {
      document.addEventListener(event, handleActivity, true);
    });

    // Vérifier l'expiration de session toutes les minutes
    const sessionCheckInterval = setInterval(() => {
      checkSessionExpiration();
    }, 60000); // 1 minute

    // Nettoyage
    return () => {
      events.forEach(event => {
        document.removeEventListener(event, handleActivity, true);
      });
      clearInterval(sessionCheckInterval);
    };
  }, [isAuthenticated, updateActivity, checkSessionExpiration]);

  return <>{children}</>;
};