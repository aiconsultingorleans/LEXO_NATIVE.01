'use client';

import React from 'react';
import { useProgressAnimation, getProgressColorClass, getProgressTextColor, type UseProgressAnimationOptions } from '@/hooks/useProgressAnimation';

interface AnimatedProgressBarProps extends UseProgressAnimationOptions {
  fileName?: string;
  className?: string;
  showText?: boolean;
  showPercentage?: boolean;
  size?: 'sm' | 'md' | 'lg' | 'xl';
}

export const AnimatedProgressBar: React.FC<AnimatedProgressBarProps> = ({
  isActive,
  estimatedDuration,
  onComplete,
  onPhaseChange,
  fileName,
  className = '',
  showText = true,
  showPercentage = true,
  size = 'md'
}) => {
  const { progress, phase, text, isCompleted } = useProgressAnimation({
    isActive,
    estimatedDuration,
    onComplete,
    onPhaseChange
  });

  const sizeClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
    xl: 'h-5'
  };

  const textSizeClasses = {
    sm: 'text-xs',
    md: 'text-xs',
    lg: 'text-sm',
    xl: 'text-sm'
  };

  if (!isActive && progress === 0) {
    return null;
  }

  return (
    <div className={`space-y-1 ${className}`}>
      {/* Text and percentage */}
      {(showText || showPercentage) && (
        <div className="flex items-center justify-between">
          {showText && (
            <div className={`${textSizeClasses[size]} ${getProgressTextColor(phase)} font-medium flex items-center space-x-1`}>
              <span>{text}</span>
              {fileName && (
                <span className="text-gray-300 truncate max-w-32">
                  - {fileName}
                </span>
              )}
            </div>
          )}
          {showPercentage && (
            <span className={`${textSizeClasses[size]} font-medium text-gray-200`}>
              {progress}%
            </span>
          )}
        </div>
      )}

      {/* Progress bar */}
      <div className={`relative w-full bg-gray-700 border border-gray-600 rounded-full ${sizeClasses[size]} overflow-hidden`}>
        <div
          className={`${sizeClasses[size]} rounded-full transition-all duration-500 ease-out relative overflow-hidden ${getProgressColorClass(phase)}`}
          style={{ width: `${progress}%` }}
        >
          {/* Shine animation effect */}
          {isActive && !isCompleted && (
            <div 
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/50 to-transparent animate-shine"
              style={{
                animation: 'shine 2s infinite linear'
              }}
            />
          )}
        </div>
      </div>

      {/* Completion indicator */}
      {isCompleted && (
        <div className="flex items-center space-x-1 text-green-600">
          <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
          <span className={`${textSizeClasses[size]} font-medium`}>
            Traitement terminé
          </span>
        </div>
      )}
    </div>
  );
};

// Add custom CSS for shine animation
export const ProgressBarStyles = () => (
  <style jsx global>{`
    @keyframes shine {
      0% {
        transform: translateX(-100%);
      }
      100% {
        transform: translateX(300%);
      }
    }
    
    .animate-shine {
      animation: shine 2s infinite linear;
    }
  `}</style>
);