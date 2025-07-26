import { useState, useEffect, useRef } from 'react';

export interface ProgressPhase {
  name: string;
  targetProgress: number;
  duration: number;
  text: string;
  color: string;
}

export interface UseProgressAnimationOptions {
  isActive: boolean;
  estimatedDuration?: number;
  onComplete?: () => void;
  onPhaseChange?: (phase: ProgressPhase) => void;
}

export interface ProgressState {
  progress: number;
  phase: ProgressPhase;
  text: string;
  isCompleted: boolean;
}

const DEFAULT_PHASES: ProgressPhase[] = [
  {
    name: 'upload',
    targetProgress: 15,
    duration: 2000,
    text: '📤 Upload du fichier...',
    color: 'from-blue-400 to-blue-600'
  },
  {
    name: 'ocr',
    targetProgress: 45,
    duration: 3000,
    text: '🔍 Extraction du texte (OCR)...',
    color: 'from-purple-400 to-purple-600'
  },
  {
    name: 'ai_analysis',
    targetProgress: 85,
    duration: 3500,
    text: '🤖 Analyse IA en cours...',
    color: 'from-violet-400 to-violet-600'
  },
  {
    name: 'finalization',
    targetProgress: 100,
    duration: 1500,
    text: '✅ Classification terminée',
    color: 'from-green-400 to-green-600'
  }
];

export const useProgressAnimation = (options: UseProgressAnimationOptions): ProgressState => {
  const { isActive, onComplete, onPhaseChange } = options;
  
  const [progress, setProgress] = useState(0);
  const [currentPhaseIndex, setCurrentPhaseIndex] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);
  
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const phaseStartTimeRef = useRef<number | null>(null);

  const currentPhase = DEFAULT_PHASES[currentPhaseIndex] || DEFAULT_PHASES[0];

  useEffect(() => {
    if (!isActive) {
      // Reset state when not active
      setProgress(0);
      setCurrentPhaseIndex(0);
      setIsCompleted(false);
      startTimeRef.current = null;
      phaseStartTimeRef.current = null;
      
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    // Start animation
    startTimeRef.current = Date.now();
    phaseStartTimeRef.current = Date.now();
    
    intervalRef.current = setInterval(() => {
      const now = Date.now();
      const phaseElapsed = now - (phaseStartTimeRef.current || now);
      
      const phase = DEFAULT_PHASES[currentPhaseIndex];
      if (!phase) return;

      // Calculate progress within current phase
      const phaseProgress = Math.min(phaseElapsed / phase.duration, 1);
      
      // Easing function for smooth animation (ease-out)
      const easedProgress = 1 - Math.pow(1 - phaseProgress, 3);
      
      // Calculate actual progress value
      const previousProgress = currentPhaseIndex > 0 
        ? DEFAULT_PHASES[currentPhaseIndex - 1].targetProgress 
        : 0;
      
      const progressRange = phase.targetProgress - previousProgress;
      const newProgress = previousProgress + (progressRange * easedProgress);
      
      setProgress(Math.round(newProgress));

      // Check if current phase is completed
      if (phaseProgress >= 1) {
        if (currentPhaseIndex < DEFAULT_PHASES.length - 1) {
          // Move to next phase
          setCurrentPhaseIndex(prev => prev + 1);
          phaseStartTimeRef.current = now;
          
          if (onPhaseChange) {
            onPhaseChange(DEFAULT_PHASES[currentPhaseIndex + 1]);
          }
        } else {
          // All phases completed
          setProgress(100);
          setIsCompleted(true);
          
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
          
          if (onComplete) {
            onComplete();
          }
        }
      }
    }, 50); // Update every 50ms for smooth animation

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [isActive, currentPhaseIndex, onComplete, onPhaseChange]);

  return {
    progress,
    phase: currentPhase,
    text: currentPhase.text,
    isCompleted
  };
};

export const getProgressColorClass = (phase: ProgressPhase): string => {
  return `bg-gradient-to-r ${phase.color}`;
};

export const getProgressTextColor = (phase: ProgressPhase): string => {
  const colorMap: Record<string, string> = {
    'from-blue-400 to-blue-600': 'text-blue-300',
    'from-purple-400 to-purple-600': 'text-purple-300', 
    'from-violet-400 to-violet-600': 'text-violet-300',
    'from-green-400 to-green-600': 'text-green-300'
  };
  
  return colorMap[phase.color] || 'text-blue-300';
};