'use client';

import { useState, useEffect } from 'react';
import { usePipelineStore, type PipelineType } from '@/stores/pipelineStore';
import { useToast } from '@/contexts/ToastContext';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';
import { Zap, Bot, Lightbulb, RefreshCw, AlertCircle, Check } from 'lucide-react';

interface ModelToggleProps {
  className?: string;
  showLabels?: boolean;
  size?: 'sm' | 'md' | 'lg';
}

const pipelineConfig = {
  mistral: {
    name: 'Mistral MLX',
    description: 'Pipeline principal - Apple Silicon optimisé',
    icon: Bot,
    color: 'text-blue-400',
    bgColor: 'bg-blue-900/20',
    borderColor: 'border-blue-600/50',
    badge: 'Principal',
    badgeColor: 'bg-blue-900/30 text-blue-300',
  },
  donut: {
    name: 'DONUT + CamemBERT',
    description: 'Pipeline alternatif - Classification dynamique',
    icon: Lightbulb,
    color: 'text-purple-400',
    bgColor: 'bg-purple-900/20',
    borderColor: 'border-purple-600/50', 
    badge: 'Alternatif',
    badgeColor: 'bg-purple-900/30 text-purple-300',
  },
} as const;

export function ModelToggle({ className, showLabels = true, size = 'md' }: ModelToggleProps) {
  const {
    activePipeline,
    isLoading,
    error,
    availablePipelines,
    switchPipeline,
    checkPipelineStatus,
    clearError,
  } = usePipelineStore();
  
  const toast = useToast();
  const [isChecking, setIsChecking] = useState(false);

  // Vérifier le statut des pipelines au montage
  useEffect(() => {
    checkPipelineStatus();
    
    // Polling toutes les 30 secondes pour maintenir le statut à jour
    const interval = setInterval(() => {
      checkPipelineStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, [checkPipelineStatus]);

  const handleSwitchPipeline = async (pipeline: PipelineType) => {
    if (pipeline === activePipeline || isLoading) return;

    const pipelineStatus = availablePipelines[pipeline].status;
    if (pipelineStatus === 'inactive') {
      toast.error(
        'Pipeline indisponible',
        `Le pipeline ${pipelineConfig[pipeline].name} n'est pas actif`
      );
      return;
    }

    // Toast de début de basculement
    const switchingToast = toast.info(
      'Basculement en cours...',
      `Activation du pipeline ${pipelineConfig[pipeline].name}`,
      { duration: 30000 } // Long timeout pour le process
    );

    clearError();
    
    try {
      const success = await switchPipeline(pipeline);
      
      if (success) {
        toast.success(
          '✅ Pipeline basculé !',
          `Vous utilisez maintenant ${pipelineConfig[pipeline].name}. Prochains uploads utiliseront ce pipeline.`
        );
        
        // Vérifier le statut après basculement
        setTimeout(() => {
          checkPipelineStatus();
        }, 1000);
      } else {
        toast.error(
          '❌ Erreur de basculement',
          error || 'Impossible de changer de pipeline. Vérifiez que le service est démarré.'
        );
      }
    } catch (err) {
      toast.error(
        '❌ Erreur de basculement',
        'Une erreur inattendue s\'est produite. Consultez les logs du système.'
      );
    }
  };

  const handleRefreshStatus = async () => {
    setIsChecking(true);
    try {
      await checkPipelineStatus();
      toast.success('Statut mis à jour', 'Statut des pipelines actualisé');
    } catch (err) {
      toast.error('Erreur', 'Impossible de vérifier le statut');
    } finally {
      setIsChecking(false);
    }
  };

  const getStatusIcon = (pipeline: PipelineType) => {
    const status = availablePipelines[pipeline].status;
    const isActive = pipeline === activePipeline;
    
    if (isActive && status === 'active') {
      return <Check className="h-4 w-4 text-green-600" />;
    }
    
    switch (status) {
      case 'active':
        return <div className="w-3 h-3 bg-green-500 rounded-full" />;
      case 'inactive':
        return <div className="w-3 h-3 bg-red-500 rounded-full" />;
      default:
        return <div className="w-3 h-3 bg-gray-400 rounded-full" />;
    }
  };

  const getStatusText = (pipeline: PipelineType) => {
    const status = availablePipelines[pipeline].status;
    const isActive = pipeline === activePipeline;
    
    if (isActive && status === 'active') return 'Actif';
    
    switch (status) {
      case 'active':
        return 'Disponible';
      case 'inactive':
        return 'Indisponible';
      default:
        return 'Inconnu';
    }
  };

  const sizeClasses = {
    sm: 'text-sm p-3',
    md: 'text-sm p-4',
    lg: 'text-base p-6',
  };

  return (
    <div className={cn('bg-card-background rounded-xl border border-card-border shadow-sm', sizeClasses[size], className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Zap className="h-5 w-5 text-primary" />
          <h3 className="font-semibold text-foreground">Pipeline IA</h3>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefreshStatus}
          disabled={isChecking}
          className="h-8 w-8 p-0"
        >
          <RefreshCw className={cn('h-4 w-4', { 'animate-spin': isChecking })} />
        </Button>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-600/50 rounded-lg flex items-start space-x-2">
          <AlertCircle className="h-4 w-4 text-red-400 mt-0.5 flex-shrink-0" />
          <div className="text-sm text-red-300">
            <p className="font-medium">Erreur</p>
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* Pipeline Options */}
      <div className="space-y-3">
        {(Object.keys(pipelineConfig) as PipelineType[]).map((pipeline) => {
          const config = pipelineConfig[pipeline];
          const isActive = pipeline === activePipeline;
          const status = availablePipelines[pipeline].status;
          const isAvailable = status === 'active';
          const Icon = config.icon;
          
          return (
            <div
              key={pipeline}
              className={cn(
                'relative rounded-lg border-2 transition-all duration-300 cursor-pointer hover:shadow-md transform hover:scale-[1.02]',
                {
                  [config.borderColor]: isActive,
                  'border-card-border': !isActive,
                  [config.bgColor]: isActive,
                  'bg-background-secondary': !isActive && !isAvailable,
                  'bg-card-background': !isActive && isAvailable,
                  'opacity-60': !isAvailable,
                  'ring-2 ring-primary/20': isLoading,
                  'animate-pulse': isLoading,
                }
              )}
              onClick={() => handleSwitchPipeline(pipeline)}
            >
              <div className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3 flex-1">
                    <div className={cn(
                      'p-2 rounded-lg flex-shrink-0',
                      isActive ? config.bgColor : 'bg-background-tertiary'
                    )}>
                      <Icon className={cn(
                        'h-5 w-5',
                        isActive ? config.color : 'text-foreground-muted'
                      )} />
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className={cn(
                          'font-medium text-sm',
                          isActive ? 'text-foreground' : 'text-foreground-secondary'
                        )}>
                          {config.name}
                        </h4>
                        <span className={cn(
                          'text-xs px-2 py-0.5 rounded-full font-medium',
                          isActive ? config.badgeColor : 'bg-background-tertiary text-foreground-muted border border-card-border'
                        )}>
                          {config.badge}
                        </span>
                      </div>
                      
                      {showLabels && (
                        <p className={cn(
                          'text-xs',
                          isActive ? 'text-foreground-secondary' : 'text-foreground-muted'
                        )}>
                          {config.description}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Status */}
                  <div className="flex flex-col items-end space-y-1">
                    {getStatusIcon(pipeline)}
                    <span className={cn(
                      'text-xs font-medium',
                      {
                        'text-green-400': status === 'active' && isActive,
                        'text-green-500': status === 'active' && !isActive,
                        'text-red-400': status === 'inactive',
                        'text-foreground-muted': status === 'unknown',
                      }
                    )}>
                      {getStatusText(pipeline)}
                    </span>
                  </div>
                </div>

                {/* Loading Indicator */}
                {isLoading && (
                  <div className="mt-3 pt-3 border-t border-card-border">
                    <div className="flex items-center space-x-2 text-xs text-foreground-secondary">
                      <div className="animate-spin h-3 w-3 border-2 border-background-tertiary border-t-primary rounded-full"></div>
                      <span>
                        {pipeline === activePipeline ? 'Basculement en cours...' : 'Activation...'}
                      </span>
                    </div>
                    <div className="mt-2 w-full bg-background-secondary rounded-full h-1 border border-card-border">
                      <div className="bg-primary h-1 rounded-full animate-pulse" style={{ width: '60%' }}></div>
                    </div>
                  </div>
                )}
              </div>

              {/* Active Indicator */}
              {isActive && (
                <div className={cn(
                  'absolute -top-1 -right-1 h-3 w-3 rounded-full',
                  status === 'active' ? 'bg-green-500' : 'bg-yellow-500'
                )}>
                  <div className={cn(
                    'h-3 w-3 rounded-full animate-ping absolute',
                    status === 'active' ? 'bg-green-500' : 'bg-yellow-500'
                  )}></div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Legend */}
      <div className="mt-4 pt-3 border-t border-card-border">
        <div className="flex items-center justify-between text-xs text-foreground-muted">
          <div className="flex items-center space-x-4">
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span>Disponible</span>
            </div>
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 bg-red-500 rounded-full"></div>
              <span>Indisponible</span>
            </div>
          </div>
          
          {availablePipelines.mistral.lastCheck && (
            <span>
              Vérifié: {new Date(availablePipelines.mistral.lastCheck).toLocaleTimeString()}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}