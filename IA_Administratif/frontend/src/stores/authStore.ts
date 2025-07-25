import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface User {
  id: string;
  email: string;
  name: string;
  role: 'user' | 'admin';
  created_at: string;
  last_login: string | null;
}

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  loginTime: number | null;
  lastActivity: number | null;
}

interface AuthActions {
  login: (email: string, password: string) => Promise<void>;
  register: (userData: {
    email: string;
    password: string;
    name: string;
  }) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  validateToken: () => Promise<boolean>;
  updateActivity: () => void;
  checkSessionExpiration: () => boolean;
}

type AuthStore = AuthState & AuthActions;

const initialState: AuthState = {
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: false,
  error: null,
  loginTime: null,
  lastActivity: null,
};

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
          const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email, password }),
          });

          if (!loginResponse.ok) {
            const error = await loginResponse.json();
            throw new Error(error.detail || 'Erreur de connexion');
          }

          const loginData = await loginResponse.json();
          
          // Récupérer les informations utilisateur avec le token
          const userResponse = await fetch('http://localhost:8000/api/v1/auth/me', {
            headers: {
              'Authorization': `Bearer ${loginData.access_token}`,
            },
          });

          if (!userResponse.ok) {
            throw new Error('Impossible de récupérer les informations utilisateur');
          }

          const userData = await userResponse.json();
          
          const now = Date.now();
          set({
            user: userData,
            accessToken: loginData.access_token,
            refreshToken: loginData.refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
            loginTime: now,
            lastActivity: now,
          });
          
          // Store tokens in localStorage for API calls
          localStorage.setItem('access_token', loginData.access_token);
          localStorage.setItem('refresh_token', loginData.refresh_token);
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Erreur de connexion',
          });
          throw error;
        }
      },

      register: async (userData) => {
        set({ isLoading: true, error: null });

        try {
          const response = await fetch('http://localhost:8000/api/v1/auth/register', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              email: userData.email,
              password: userData.password,
              name: userData.name,
            }),
          });

          if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Erreur lors de la création du compte');
          }

          set({ isLoading: false, error: null });
        } catch (error) {
          set({
            isLoading: false,
            error: error instanceof Error ? error.message : 'Erreur lors de la création du compte',
          });
          throw error;
        }
      },

      logout: () => {
        // Appel optionnel à l'API pour invalider le token côté serveur
        fetch('http://localhost:8000/api/v1/auth/logout', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${get().accessToken}`,
          },
        }).catch(() => {
          // Ignorer les erreurs de logout côté serveur
        });

        // Clear localStorage
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');

        set({
          ...initialState,
        });
      },

      refreshAuth: async () => {
        const { refreshToken } = get();
        
        if (!refreshToken) {
          throw new Error('Pas de refresh token disponible');
        }

        try {
          const response = await fetch('http://localhost:8000/api/v1/auth/refresh', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ refresh_token: refreshToken }),
          });

          if (!response.ok) {
            throw new Error('Impossible de rafraîchir le token');
          }

          const data = await response.json();
          const now = Date.now();
          
          set({
            user: data.user,
            accessToken: data.access_token,
            refreshToken: data.refresh_token || refreshToken,
            isAuthenticated: true,
            lastActivity: now,
          });
          
          // Update localStorage
          localStorage.setItem('access_token', data.access_token);
          if (data.refresh_token) {
            localStorage.setItem('refresh_token', data.refresh_token);
          }
        } catch (error) {
          // Si le refresh token est invalide, déconnecter l'utilisateur
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          set({ ...initialState });
          throw error;
        }
      },

      validateToken: async () => {
        const { accessToken } = get();
        
        if (!accessToken) {
          return false;
        }

        try {
          const response = await fetch('http://localhost:8000/api/v1/auth/me', {
            headers: {
              'Authorization': `Bearer ${accessToken}`,
            },
          });

          if (response.ok) {
            const userData = await response.json();
            set({ 
              user: userData,
              lastActivity: Date.now()
            });
            return true;
          } else {
            // Token invalide, déconnecter
            get().logout();
            return false;
          }
        } catch {
          // Erreur réseau ou autre, déconnecter par sécurité
          get().logout();
          return false;
        }
      },

      updateActivity: () => {
        set({ lastActivity: Date.now() });
      },

      checkSessionExpiration: () => {
        const { lastActivity, isAuthenticated } = get();
        
        if (!isAuthenticated || !lastActivity) {
          return false;
        }

        const now = Date.now();
        const oneHour = 60 * 60 * 1000; // 1 heure en millisecondes
        
        if (now - lastActivity > oneHour) {
          // Session expirée
          get().logout();
          return true;
        }
        
        return false;
      },

      clearError: () => set({ error: null }),
      
      setLoading: (loading: boolean) => set({ isLoading: loading }),
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
        loginTime: state.loginTime,
        lastActivity: state.lastActivity,
      }),
    }
  )
);

// Fonctions utilitaires pour accéder aux données d'auth
export const getAuthToken = () => useAuthStore.getState().accessToken;
export const getUser = () => useAuthStore.getState().user;
export const isAuthenticated = () => useAuthStore.getState().isAuthenticated;