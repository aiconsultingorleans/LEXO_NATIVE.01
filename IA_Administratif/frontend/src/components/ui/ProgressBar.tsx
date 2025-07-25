'use client';

import React from 'react';
import { Clock, CheckCircle, FileText } from 'lucide-react';

interface ProgressBarProps {
  current: number;
  total: number;
  timeRemaining?: string;
  timeElapsed?: string;
  completionTime?: string;
  isCompleted?: boolean;
  currentFileName?: string;
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  current,
  total,
  timeRemaining,
  timeElapsed,
  completionTime,
  isCompleted = false,
  currentFileName,
  className = ''
}) => {
  const percentage = total > 0 ? Math.round((current / total) * 100) : 0;
  const isActive = current < total && !isCompleted;

  // Formatage du temps
  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  return (
    <div className={`space-y-3 ${className}`}>
      {/* Texte d'état */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center space-x-2">
          {isCompleted ? (
            <>
              <CheckCircle className="h-4 w-4 text-green-500" />
              <span className="text-green-600 font-medium">
                Documents analysés en {completionTime}
              </span>
            </>
          ) : (
            <>
              <FileText className="h-4 w-4 text-blue-500" />
              <span className="text-gray-700">
                {isActive ? 'Analyse en cours...' : 'En attente...'}
              </span>
            </>
          )}
        </div>
        
        <div className="text-gray-600">
          {current}/{total} fichiers
        </div>
      </div>

      {/* Barre de progression */}
      <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
        <div 
          className={`h-full transition-all duration-500 ease-out ${
            isCompleted 
              ? 'bg-green-500' 
              : isActive 
                ? 'bg-blue-500' 
                : 'bg-gray-400'
          }`}
          style={{ width: `${percentage}%` }}
        >
          {/* Animation pour la barre active */}
          {isActive && (
            <div className="h-full w-full bg-gradient-to-r from-transparent via-white via-white to-transparent opacity-30 animate-pulse" />
          )}
        </div>
      </div>

      {/* Informations détaillées */}
      <div className="flex items-center justify-between text-xs text-gray-500">
        <div className="flex items-center space-x-4">
          {/* Progression en pourcentage */}
          <span className="font-medium">{percentage}%</span>
          
          {/* Temps écoulé */}
          {timeElapsed && (
            <div className="flex items-center space-x-1">
              <Clock className="h-3 w-3" />
              <span>Écoulé: {timeElapsed}</span>
            </div>
          )}
        </div>

        {/* Temps restant */}
        {timeRemaining && !isCompleted && (
          <div className="flex items-center space-x-1">
            <Clock className="h-3 w-3" />
            <span>Restant: {timeRemaining}</span>
          </div>
        )}
      </div>

      {/* Fichier en cours de traitement */}
      {currentFileName && !isCompleted && (
        <div className="flex items-center space-x-2 text-xs text-gray-600 bg-gray-50 p-2 rounded-md">
          <FileText className="h-3 w-3 text-blue-500" />
          <span className="truncate">
            Traitement: <span className="font-medium">{currentFileName}</span>
          </span>
        </div>
      )}
    </div>
  );
};

// Composant wrapper pour l'utilisation dans le dashboard
interface BatchProgressDisplayProps {
  batchProgress: {
    isActive: boolean;
    current: number;
    total: number;
    startTime: number | null;
    currentFile?: string;
    completionTime?: string;
  };
}

export const BatchProgressDisplay: React.FC<BatchProgressDisplayProps> = ({ batchProgress }) => {
  const { isActive, current, total, startTime, currentFile, completionTime } = batchProgress;
  
  // Calcul du temps écoulé et estimation
  const [timeElapsed, setTimeElapsed] = React.useState<string>('');
  const [timeRemaining, setTimeRemaining] = React.useState<string>('');

  React.useEffect(() => {
    if (!isActive || !startTime) return;

    const interval = setInterval(() => {
      const now = Date.now();
      const elapsedSeconds = (now - startTime) / 1000;
      
      // Temps écoulé
      setTimeElapsed(formatTime(elapsedSeconds));
      
      // Estimation temps restant (basé sur vitesse actuelle)
      if (current > 0) {
        const avgTimePerFile = elapsedSeconds / current;
        const remainingFiles = total - current;
        const estimatedRemainingSeconds = avgTimePerFile * remainingFiles;
        setTimeRemaining(formatTime(estimatedRemainingSeconds));
      } else {
        // Estimation initiale : 8 secondes par document (performance moyenne observée)
        const estimatedRemainingSeconds = total * 8;
        setTimeRemaining(formatTime(estimatedRemainingSeconds));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isActive, startTime, current, total]);

  const formatTime = (seconds: number): string => {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  // Ne pas afficher si pas de traitement
  if (!isActive && !completionTime) return null;

  return (
    <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
      <ProgressBar
        current={current}
        total={total}
        timeElapsed={timeElapsed}
        timeRemaining={timeRemaining}
        completionTime={completionTime}
        isCompleted={!!completionTime}
        currentFileName={currentFile}
      />
    </div>
  );
};