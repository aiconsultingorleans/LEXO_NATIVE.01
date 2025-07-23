'use client';

import { useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider = ({ children }: AuthProviderProps) => {
  const { refreshAuth, accessToken, refreshToken, logout } = useAuth();

  useEffect(() => {
    // Si on a un refresh token mais pas d'access token, essayer de rafraîchir
    if (refreshToken && !accessToken) {
      refreshAuth().catch(() => {
        // Si le refresh échoue, déconnecter l'utilisateur
        logout();
      });
    }
  }, [refreshToken, accessToken, refreshAuth, logout]);

  // Note: Dans une implémentation plus robuste, on utiliserait
    // un intercepteur axios ou une autre solution pour gérer
    // automatiquement le refresh des tokens sur les réponses 401

  return <>{children}</>;
};

export default AuthProvider;