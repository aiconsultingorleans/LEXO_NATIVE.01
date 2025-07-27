import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type PipelineType = 'mistral' | 'donut';

interface PipelineState {
  activePipeline: PipelineType;
  isLoading: boolean;
  lastSwitchTime: number | null;
  error: string | null;
  availablePipelines: {
    mistral: { status: 'active' | 'inactive' | 'unknown'; lastCheck: number | null };
    donut: { status: 'active' | 'inactive' | 'unknown'; lastCheck: number | null };
  };
}

interface PipelineActions {
  switchPipeline: (pipeline: PipelineType) => Promise<boolean>;
  checkPipelineStatus: (pipeline?: PipelineType) => Promise<void>;
  setLoading: (loading: boolean) => void;
  clearError: () => void;
  updatePipelineStatus: (pipeline: PipelineType, status: 'active' | 'inactive' | 'unknown') => void;
}

type PipelineStore = PipelineState & PipelineActions;

const initialState: PipelineState = {
  activePipeline: 'mistral', // Mistral par défaut selon CLAUDE.md
  isLoading: false,
  lastSwitchTime: null,
  error: null,
  availablePipelines: {
    mistral: { status: 'unknown', lastCheck: null },
    donut: { status: 'unknown', lastCheck: null },
  },
};

export const usePipelineStore = create<PipelineStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      switchPipeline: async (pipeline: PipelineType) => {
        const currentPipeline = get().activePipeline;
        if (currentPipeline === pipeline) {
          return true; // Déjà sur ce pipeline
        }

        set({ isLoading: true, error: null });

        try {
          const token = localStorage.getItem('access_token');
          if (!token) {
            throw new Error('Token d\'authentification manquant');
          }

          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          const response = await fetch(`${apiUrl}/api/v1/models/switch`, {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ pipeline: pipeline }),
          });

          if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: 'Erreur de basculement' }));
            
            // Fallback automatique vers Mistral si DONUT échoue
            if (pipeline === 'donut' && currentPipeline !== 'mistral') {
              console.warn('DONUT indisponible, fallback vers Mistral MLX');
              set({
                activePipeline: 'mistral',
                isLoading: false,
                error: 'DONUT indisponible - Fallback automatique vers Mistral MLX',
              });
              get().updatePipelineStatus('donut', 'inactive');
              get().updatePipelineStatus('mistral', 'active');
              return true; // Succès avec fallback
            }
            
            throw new Error(errorData.detail || `Impossible de basculer vers ${pipeline}`);
          }

          const result = await response.json();
          
          set({
            activePipeline: pipeline,
            isLoading: false,
            lastSwitchTime: Date.now(),
            error: null,
          });

          // Mettre à jour le statut du pipeline activé
          get().updatePipelineStatus(pipeline, 'active');

          return true;
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Erreur de basculement';
          set({
            isLoading: false,
            error: errorMessage,
          });
          return false;
        }
      },

      checkPipelineStatus: async (targetPipeline?: PipelineType) => {
        const token = localStorage.getItem('access_token');
        if (!token) return;

        const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
        const now = Date.now();

        try {
          // Vérifier le statut global
          const response = await fetch(`${apiUrl}/api/v1/models/status`, {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
          });

          if (response.ok) {
            const data = await response.json();
            
            // Debug logging
            console.log('🔄 Pipeline status check:', {
              mistral_service_status: data.mistral_service_status,
              donut_service_status: data.donut_service_status,
              active_pipeline: data.active_pipeline,
              timestamp: new Date().toISOString()
            });
            
            // Mapping des statuts API vers statuts frontend
            const mapStatus = (serviceStatus: string) => {
              if (serviceStatus === 'available') return 'active';
              if (serviceStatus === 'unavailable') return 'inactive';
              return 'unknown';
            };
            
            const mistralStatus = mapStatus(data.mistral_service_status || 'unknown');
            const donutStatus = mapStatus(data.donut_service_status || 'unknown');
            
            console.log('📊 Mapped statuses:', { mistral: mistralStatus, donut: donutStatus });
            
            set(state => ({
              availablePipelines: {
                mistral: {
                  status: mistralStatus,
                  lastCheck: now,
                },
                donut: {
                  status: donutStatus, 
                  lastCheck: now,
                },
              },
            }));

            // Mettre à jour le pipeline actif si spécifié dans la réponse
            if (data.active_pipeline && data.active_pipeline !== get().activePipeline) {
              console.log(`🔄 Pipeline switch detected: ${get().activePipeline} → ${data.active_pipeline}`);
              set({ activePipeline: data.active_pipeline });
            }
          } else {
            console.warn('❌ Pipeline status check failed:', response.status, response.statusText);
          }
        } catch (error) {
          console.warn('Erreur lors de la vérification du statut des pipelines:', error);
          
          // Marquer comme inconnu en cas d'erreur
          const pipelinesToCheck = targetPipeline ? [targetPipeline] : ['mistral', 'donut'] as const;
          
          set(state => ({
            availablePipelines: {
              ...state.availablePipelines,
              ...Object.fromEntries(
                pipelinesToCheck.map(p => [p, { status: 'unknown' as const, lastCheck: now }])
              ),
            },
          }));
        }
      },

      updatePipelineStatus: (pipeline: PipelineType, status: 'active' | 'inactive' | 'unknown') => {
        set(state => ({
          availablePipelines: {
            ...state.availablePipelines,
            [pipeline]: {
              ...state.availablePipelines[pipeline],
              status,
              lastCheck: Date.now(),
            },
          },
        }));
      },

      setLoading: (loading: boolean) => set({ isLoading: loading }),
      
      clearError: () => set({ error: null }),
    }),
    {
      name: 'pipeline-storage',
      partialize: (state) => ({
        activePipeline: state.activePipeline,
        lastSwitchTime: state.lastSwitchTime,
        availablePipelines: state.availablePipelines,
      }),
    }
  )
);

// Utilitaires pour accéder aux données
export const getActivePipeline = () => usePipelineStore.getState().activePipeline;
export const isPipelineLoading = () => usePipelineStore.getState().isLoading;
export const getPipelineError = () => usePipelineStore.getState().error;