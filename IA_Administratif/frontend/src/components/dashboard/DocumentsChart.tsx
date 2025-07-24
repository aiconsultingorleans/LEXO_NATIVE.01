'use client';

import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { BarChart3, TrendingUp, PieChart as PieChartIcon } from 'lucide-react';

interface DocumentStats {
  date: string;
  count: number;
  processed: number;
  errors: number;
}

interface CategoryStats {
  category: string;
  count: number;
  color: string;
}

const COLORS = [
  '#3B82F6', // blue
  '#10B981', // green
  '#F59E0B', // yellow
  '#EF4444', // red
  '#8B5CF6', // purple
  '#06B6D4', // cyan
  '#F97316', // orange
  '#84CC16'  // lime
];

export function DocumentsChart() {
  const [chartType, setChartType] = useState<'bar' | 'line' | 'pie'>('bar');
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');
  const [data, setData] = useState<DocumentStats[]>([]);
  const [categoryData, setCategoryData] = useState<CategoryStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call for document statistics
    const generateMockData = () => {
      const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90;
      const mockData: DocumentStats[] = [];
      const mockCategories: CategoryStats[] = [
        { category: 'Factures', count: 45, color: COLORS[0] },
        { category: 'Contrats', count: 23, color: COLORS[1] },
        { category: 'RIB/IBAN', count: 18, color: COLORS[2] },
        { category: 'Attestations', count: 32, color: COLORS[3] },
        { category: 'Cartes', count: 12, color: COLORS[4] },
        { category: 'Autres', count: 8, color: COLORS[5] }
      ];

      for (let i = days - 1; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        
        mockData.push({
          date: date.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' }),
          count: Math.floor(Math.random() * 20) + 5,
          processed: Math.floor(Math.random() * 18) + 4,
          errors: Math.floor(Math.random() * 3)
        });
      }

      setData(mockData);
      setCategoryData(mockCategories);
      setLoading(false);
    };

    generateMockData();
  }, [timeRange]);

  const renderChart = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      );
    }

    switch (chartType) {
      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis 
                dataKey="date" 
                className="text-xs"
                tick={{ fill: 'currentColor', fontSize: 12 }}
              />
              <YAxis 
                className="text-xs"
                tick={{ fill: 'currentColor', fontSize: 12 }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'var(--card-background)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  color: 'var(--foreground)'
                }}
              />
              <Bar dataKey="processed" fill="#10B981" name="Traités" />
              <Bar dataKey="errors" fill="#EF4444" name="Erreurs" />
            </BarChart>
          </ResponsiveContainer>
        );
      
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
              <XAxis 
                dataKey="date" 
                className="text-xs"
                tick={{ fill: 'currentColor', fontSize: 12 }}
              />
              <YAxis 
                className="text-xs"
                tick={{ fill: 'currentColor', fontSize: 12 }}
              />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'var(--card-background)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  color: 'var(--foreground)'
                }}
              />
              <Line 
                type="monotone" 
                dataKey="count" 
                stroke="#3B82F6" 
                strokeWidth={2}
                name="Total documents"
              />
              <Line 
                type="monotone" 
                dataKey="processed" 
                stroke="#10B981" 
                strokeWidth={2}
                name="Traités"
              />
            </LineChart>
          </ResponsiveContainer>
        );
      
      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={categoryData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ category, percent }) => `${category} ${((percent || 0) * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="count"
              >
                {categoryData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'var(--card-background)',
                  border: '1px solid var(--border)',
                  borderRadius: '8px',
                  color: 'var(--foreground)'
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        );
      
      default:
        return null;
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-foreground">Statistiques des documents</h3>
        
        <div className="flex items-center space-x-2">
          {/* Chart Type Toggle */}
          <div className="flex bg-background-secondary rounded-lg p-1">
            <Button
              size="sm"
              variant={chartType === 'bar' ? 'primary' : 'ghost'}
              onClick={() => setChartType('bar')}
              className="h-8 px-3"
            >
              <BarChart3 className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={chartType === 'line' ? 'primary' : 'ghost'}
              onClick={() => setChartType('line')}
              className="h-8 px-3"
            >
              <TrendingUp className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant={chartType === 'pie' ? 'primary' : 'ghost'}
              onClick={() => setChartType('pie')}
              className="h-8 px-3"
            >
              <PieChartIcon className="w-4 h-4" />
            </Button>
          </div>

          {/* Time Range Toggle */}
          <div className="flex bg-background-secondary rounded-lg p-1">
            <Button
              size="sm"
              variant={timeRange === '7d' ? 'primary' : 'ghost'}
              onClick={() => setTimeRange('7d')}
              className="h-8 px-3 text-xs"
            >
              7j
            </Button>
            <Button
              size="sm"
              variant={timeRange === '30d' ? 'primary' : 'ghost'}
              onClick={() => setTimeRange('30d')}
              className="h-8 px-3 text-xs"
            >
              30j
            </Button>
            <Button
              size="sm"
              variant={timeRange === '90d' ? 'primary' : 'ghost'}
              onClick={() => setTimeRange('90d')}
              className="h-8 px-3 text-xs"
            >
              90j
            </Button>
          </div>
        </div>
      </div>

      {renderChart()}
    </Card>
  );
}

export default DocumentsChart;