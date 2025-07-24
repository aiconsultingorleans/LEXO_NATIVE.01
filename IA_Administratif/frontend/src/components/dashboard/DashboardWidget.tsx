'use client';

import { ReactNode } from 'react';
import { Card } from '@/components/ui/Card';
import { MoreHorizontal, Maximize2, X } from 'lucide-react';

export interface DashboardWidgetProps {
  id: string;
  title: string;
  children: ReactNode;
  size?: 'small' | 'medium' | 'large';
  onResize?: (size: 'small' | 'medium' | 'large') => void;
  onRemove?: () => void;
  className?: string;
  actions?: ReactNode;
}

export function DashboardWidget({
  id,
  title,
  children,
  size = 'medium',
  onResize,
  onRemove,
  className = '',
  actions
}: DashboardWidgetProps) {
  const sizeClasses = {
    small: 'col-span-1 row-span-1',
    medium: 'col-span-2 row-span-1',
    large: 'col-span-2 row-span-2'
  };

  return (
    <Card className={`relative ${sizeClasses[size]} ${className}`}>
      <div className="flex items-center justify-between p-4 border-b border-border-light">
        <h3 className="text-lg font-semibold text-foreground">{title}</h3>
        <div className="flex items-center space-x-2">
          {actions}
          <div className="relative group">
            <button className="p-1 rounded-md hover:bg-hover-background transition-colors">
              <MoreHorizontal className="w-4 h-4 text-foreground-secondary" />
            </button>
            
            {/* Dropdown Menu */}
            <div className="absolute right-0 top-8 bg-card-background border border-border rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-10 min-w-[150px]">
              <div className="py-1">
                {onResize && (
                  <>
                    <button
                      onClick={() => onResize('small')}
                      className="w-full px-3 py-2 text-left text-sm text-foreground-secondary hover:bg-hover-background hover:text-foreground transition-colors"
                    >
                      Petit
                    </button>
                    <button
                      onClick={() => onResize('medium')}
                      className="w-full px-3 py-2 text-left text-sm text-foreground-secondary hover:bg-hover-background hover:text-foreground transition-colors"
                    >
                      Moyen
                    </button>
                    <button
                      onClick={() => onResize('large')}
                      className="w-full px-3 py-2 text-left text-sm text-foreground-secondary hover:bg-hover-background hover:text-foreground transition-colors"
                    >
                      Grand
                    </button>
                    <hr className="my-1 border-border-light" />
                  </>
                )}
                {onRemove && (
                  <button
                    onClick={onRemove}
                    className="w-full px-3 py-2 text-left text-sm text-error hover:bg-error/10 transition-colors flex items-center"
                  >
                    <X className="w-3 h-3 mr-2" />
                    Supprimer
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="p-4 h-full">
        {children}
      </div>
    </Card>
  );
}

export default DashboardWidget;