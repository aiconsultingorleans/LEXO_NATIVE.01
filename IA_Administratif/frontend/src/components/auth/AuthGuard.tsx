'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { useAuthStore } from '@/stores/authStore';

interface AuthGuardProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  requireRole?: 'user' | 'admin';
  fallback?: React.ReactNode;
}

export const AuthGuard = ({ 
  children, 
  requireAuth = true,
  requireRole,
  fallback 
}: AuthGuardProps) => {
  const router = useRouter();
  const { isAuthenticated, user, isLoading } = useAuth();
  const { validateToken, checkSessionExpiration } = useAuthStore();
  const [isValidating, setIsValidating] = useState(true);

  useEffect(() => {
    const checkAuthentication = async () => {
      // Vérifier l'expiration de session
      const sessionExpired = checkSessionExpiration();
      if (sessionExpired) {
        router.push('/auth/login?reason=session_expired');
        return;
      }

      // Si l'utilisateur semble authentifié, vérifier la validité du token
      if (isAuthenticated) {
        const isValid = await validateToken();
        if (!isValid) {
          router.push('/auth/login?reason=invalid_token');
          return;
        }
      }

      setIsValidating(false);

      if (!isLoading && !isValidating) {
        // Si l'authentification est requise mais l'utilisateur n'est pas connecté
        if (requireAuth && !isAuthenticated) {
          router.push('/auth/login');
          return;
        }

        // Si un rôle spécifique est requis
        if (requireRole && (!user || user.role !== requireRole)) {
          router.push('/403'); // Page d'accès refusé
          return;
        }
      }
    };

    checkAuthentication();
  }, [isAuthenticated, user, isLoading, requireAuth, requireRole, router, validateToken, checkSessionExpiration, isValidating]);

  // Afficher un loading pendant la vérification
  if (isLoading || isValidating) {
    return fallback || <LoadingSpinner />;
  }

  // Si l'authentification est requise mais pas encore vérifiée
  if (requireAuth && !isAuthenticated) {
    return fallback || <LoadingSpinner />;
  }

  // Si un rôle spécifique est requis mais l'utilisateur ne l'a pas
  if (requireRole && (!user || user.role !== requireRole)) {
    return fallback || <AccessDenied />;
  }

  return <>{children}</>;
};

// Composant de loading par défaut
const LoadingSpinner = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
  </div>
);

// Composant d'accès refusé par défaut
const AccessDenied = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <h1 className="text-4xl font-bold text-gray-900 mb-4">403</h1>
      <p className="text-lg text-gray-600 mb-8">Accès refusé</p>
      <p className="text-sm text-gray-500">
        Vous n&apos;avez pas les permissions nécessaires pour accéder à cette page.
      </p>
    </div>
  </div>
);

export default AuthGuard;