import { useAuthStore } from '@/stores/authStore';

export const useAuth = () => {
  const store = useAuthStore();

  return {
    // État d'authentification
    user: store.user,
    isAuthenticated: store.isAuthenticated,
    isLoading: store.isLoading,
    error: store.error,
    accessToken: store.accessToken,
    refreshToken: store.refreshToken,

    // Actions
    login: store.login,
    register: store.register,
    logout: store.logout,
    refreshAuth: store.refreshAuth,
    clearError: store.clearError,
    setLoading: store.setLoading,

    // Utilitaires
    hasRole: (role: 'user' | 'admin') => store.user?.role === role,
    isAdmin: () => store.user?.role === 'admin',
    getUserFullName: () => 
      store.user ? store.user.name : '',
  };
};

export default useAuth;