'use client';

import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { TrendingUp, TrendingDown, Minus, Activity } from 'lucide-react';

interface KPIData {
  label: string;
  value: number;
  previousValue: number;
  format: 'number' | 'percentage' | 'duration' | 'currency';
  icon: React.ComponentType<any>;
  color: 'blue' | 'green' | 'yellow' | 'red' | 'purple';
}

interface KPIWidgetProps {
  kpis: KPIData[];
  refreshInterval?: number;
}

export function KPIWidget({ kpis, refreshInterval = 30000 }: KPIWidgetProps) {
  const [data, setData] = useState<KPIData[]>(kpis);
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  useEffect(() => {
    const updateKPIs = () => {
      // Simulate real-time updates
      setData(prevData => 
        prevData.map(kpi => ({
          ...kpi,
          previousValue: kpi.value,
          value: kpi.value + (Math.random() - 0.5) * (kpi.value * 0.1) // ±10% variation
        }))
      );
      setLastUpdate(new Date());
    };

    const interval = setInterval(updateKPIs, refreshInterval);
    return () => clearInterval(interval);
  }, [refreshInterval]);

  const formatValue = (value: number, format: KPIData['format']) => {
    switch (format) {
      case 'percentage':
        return `${value.toFixed(1)}%`;
      case 'duration':
        return `${value.toFixed(1)}s`;
      case 'currency':
        return `${value.toFixed(2)}€`;
      default:
        return Math.round(value).toString();
    }
  };

  const getColorClasses = (color: KPIData['color']) => {
    const colors = {
      blue: {
        bg: 'bg-blue-500/10',
        text: 'text-blue-500',
        trend: 'text-blue-600'
      },
      green: {
        bg: 'bg-green-500/10',
        text: 'text-green-500',
        trend: 'text-green-600'
      },
      yellow: {
        bg: 'bg-yellow-500/10',
        text: 'text-yellow-500',
        trend: 'text-yellow-600'
      },
      red: {
        bg: 'bg-red-500/10',
        text: 'text-red-500',
        trend: 'text-red-600'
      },
      purple: {
        bg: 'bg-purple-500/10',
        text: 'text-purple-500',
        trend: 'text-purple-600'
      }
    };
    return colors[color];
  };

  const getTrendData = (current: number, previous: number) => {
    const change = current - previous;
    const percentChange = previous !== 0 ? (change / previous) * 100 : 0;
    
    let icon = Minus;
    let direction: 'up' | 'down' | 'stable' = 'stable';
    
    if (Math.abs(percentChange) > 0.1) {
      if (percentChange > 0) {
        icon = TrendingUp;
        direction = 'up';
      } else {
        icon = TrendingDown;
        direction = 'down';
      }
    }

    return { change, percentChange, icon, direction };
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {data.map((kpi, index) => {
        const colors = getColorClasses(kpi.color);
        const trend = getTrendData(kpi.value, kpi.previousValue);
        const Icon = kpi.icon;
        const TrendIcon = trend.icon;

        return (
          <Card key={index} className="p-6 hover:shadow-lg transition-shadow duration-200">
            <div className="flex items-center justify-between mb-4">
              <div className={`p-3 rounded-xl ${colors.bg}`}>
                <Icon className={`h-6 w-6 ${colors.text}`} />
              </div>
              <div className="flex items-center space-x-1">
                <Activity className="h-3 w-3 text-green-500" />
                <span className="text-xs text-green-500">Live</span>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-medium text-foreground-secondary">{kpi.label}</p>
              <div className="flex items-end justify-between">
                <p className="text-2xl font-bold text-foreground">
                  {formatValue(kpi.value, kpi.format)}
                </p>
                
                {Math.abs(trend.percentChange) > 0.1 && (
                  <div className={`flex items-center space-x-1 ${
                    trend.direction === 'up' ? 'text-green-600' : 
                    trend.direction === 'down' ? 'text-red-600' : 
                    'text-gray-500'
                  }`}>
                    <TrendIcon className="h-3 w-3" />
                    <span className="text-xs font-medium">
                      {Math.abs(trend.percentChange).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
            </div>

            <div className="mt-4 pt-3 border-t border-border-light">
              <p className="text-xs text-foreground-muted">
                Mis à jour il y a {Math.floor((Date.now() - lastUpdate.getTime()) / 1000)}s
              </p>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

export default KPIWidget;