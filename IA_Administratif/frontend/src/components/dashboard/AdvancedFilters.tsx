'use client';

import { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Select } from '@/components/ui/Select';
import { Calendar, Filter, X, Search, Download, RotateCcw } from 'lucide-react';

export interface FilterOptions {
  dateRange: {
    start: string;
    end: string;
  };
  category: string;
  status: string;
  confidence: {
    min: number;
    max: number;
  };
  searchQuery: string;
  tags: string[];
}

interface AdvancedFiltersProps {
  onFilterChange: (filters: FilterOptions) => void;
  onExport?: (filters: FilterOptions) => void;
  onReset: () => void;
}

const CATEGORIES = [
  { value: 'all', label: 'Toutes les catégories' },
  { value: 'factures', label: 'Factures' },
  { value: 'contrats', label: 'Contrats' },
  { value: 'rib', label: 'RIB/IBAN' },
  { value: 'attestations', label: 'Attestations' },
  { value: 'cartes', label: 'Cartes d\'identité' },
  { value: 'autres', label: 'Autres' }
];

const STATUS_OPTIONS = [
  { value: 'all', label: 'Tous les statuts' },
  { value: 'processed', label: 'Traités' },
  { value: 'processing', label: 'En cours' },
  { value: 'error', label: 'Erreurs' },
  { value: 'pending', label: 'En attente' }
];

const PREDEFINED_RANGES = [
  { label: 'Aujourd\'hui', days: 0 },
  { label: '7 derniers jours', days: 7 },
  { label: '30 derniers jours', days: 30 },
  { label: '90 derniers jours', days: 90 },
  { label: 'Cette année', days: 365 }
];

export function AdvancedFilters({ onFilterChange, onExport, onReset }: AdvancedFiltersProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [filters, setFilters] = useState<FilterOptions>({
    dateRange: {
      start: '',
      end: ''
    },
    category: 'all',
    status: 'all',
    confidence: {
      min: 0,
      max: 100
    },
    searchQuery: '',
    tags: []
  });

  const updateFilter = (key: keyof FilterOptions, value: any) => {
    const newFilters = { ...filters, [key]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const updateDateRange = (key: 'start' | 'end', value: string) => {
    const newDateRange = { ...filters.dateRange, [key]: value };
    updateFilter('dateRange', newDateRange);
  };

  const updateConfidenceRange = (key: 'min' | 'max', value: number) => {
    const newConfidence = { ...filters.confidence, [key]: value };
    updateFilter('confidence', newConfidence);
  };

  const setQuickDateRange = (days: number) => {
    const end = new Date();
    const start = new Date();
    
    if (days === 0) {
      // Today only
      start.setHours(0, 0, 0, 0);
    } else {
      start.setDate(start.getDate() - days);
    }

    const newDateRange = {
      start: start.toISOString().split('T')[0],
      end: end.toISOString().split('T')[0]
    };
    
    updateFilter('dateRange', newDateRange);
  };

  const resetFilters = () => {
    const defaultFilters: FilterOptions = {
      dateRange: { start: '', end: '' },
      category: 'all',
      status: 'all',
      confidence: { min: 0, max: 100 },
      searchQuery: '',
      tags: []
    };
    setFilters(defaultFilters);
    onReset();
  };

  const handleExport = () => {
    if (onExport) {
      onExport(filters);
    }
  };

  const activeFiltersCount = Object.values(filters).filter((value) => {
    if (typeof value === 'string') return value !== '' && value !== 'all';
    if (typeof value === 'object' && value !== null) {
      if ('start' in value) return value.start !== '' || value.end !== '';
      if ('min' in value) return value.min > 0 || value.max < 100;
      if (Array.isArray(value)) return value.length > 0;
    }
    return false;
  }).length;

  return (
    <Card className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-2">
          <Filter className="w-5 h-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">Filtres avancés</h3>
          {activeFiltersCount > 0 && (
            <span className="bg-primary text-white text-xs px-2 py-1 rounded-full">
              {activeFiltersCount}
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {onExport && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              className="flex items-center space-x-1"
            >
              <Download className="w-4 h-4" />
              <span>Exporter</span>
            </Button>
          )}
          
          <Button
            variant="outline"
            size="sm"
            onClick={resetFilters}
            className="flex items-center space-x-1"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset</span>
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? 'Réduire' : 'Développer'}
          </Button>
        </div>
      </div>

      {/* Quick Search */}
      <div className="mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-foreground-secondary" />
          <Input
            type="text"
            placeholder="Rechercher par nom de fichier, contenu..."
            value={filters.searchQuery}
            onChange={(e) => updateFilter('searchQuery', e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Quick Date Range Buttons */}
      <div className="flex flex-wrap gap-2 mb-4">
        {PREDEFINED_RANGES.map((range) => (
          <Button
            key={range.label}
            variant="outline"
            size="sm"
            onClick={() => setQuickDateRange(range.days)}
            className="text-xs"
          >
            {range.label}
          </Button>
        ))}
      </div>

      {/* Expanded Filters */}
      {isExpanded && (
        <div className="space-y-6">
          {/* Date Range */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground-secondary mb-2">
                Date de début
              </label>
              <Input
                type="date"
                value={filters.dateRange.start}
                onChange={(e) => updateDateRange('start', e.target.value)}
                className="w-full"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground-secondary mb-2">
                Date de fin
              </label>
              <Input
                type="date"
                value={filters.dateRange.end}
                onChange={(e) => updateDateRange('end', e.target.value)}
                className="w-full"
              />
            </div>
          </div>

          {/* Category and Status */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-foreground-secondary mb-2">
                Catégorie
              </label>
              <Select
                value={filters.category}
                onValueChange={(value) => updateFilter('category', value)}
                options={CATEGORIES}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground-secondary mb-2">
                Statut
              </label>
              <Select
                value={filters.status}
                onValueChange={(value) => updateFilter('status', value)}
                options={STATUS_OPTIONS}
              />
            </div>
          </div>

          {/* Confidence Range */}
          <div>
            <label className="block text-sm font-medium text-foreground-secondary mb-2">
              Niveau de confiance OCR: {filters.confidence.min}% - {filters.confidence.max}%
            </label>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={filters.confidence.min}
                  onChange={(e) => updateConfidenceRange('min', parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="text-xs text-foreground-secondary mt-1">Minimum: {filters.confidence.min}%</div>
              </div>
              <div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={filters.confidence.max}
                  onChange={(e) => updateConfidenceRange('max', parseInt(e.target.value))}
                  className="w-full"
                />
                <div className="text-xs text-foreground-secondary mt-1">Maximum: {filters.confidence.max}%</div>
              </div>
            </div>
          </div>

          {/* Applied Filters Summary */}
          {activeFiltersCount > 0 && (
            <div className="bg-background-secondary p-4 rounded-lg">
              <h4 className="text-sm font-medium text-foreground mb-2">Filtres appliqués:</h4>
              <div className="flex flex-wrap gap-2">
                {filters.searchQuery && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                    Recherche: "{filters.searchQuery}"
                    <button
                      onClick={() => updateFilter('searchQuery', '')}
                      className="ml-1 hover:bg-primary/20 rounded-full p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
                
                {filters.category !== 'all' && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                    {CATEGORIES.find(c => c.value === filters.category)?.label}
                    <button
                      onClick={() => updateFilter('category', 'all')}
                      className="ml-1 hover:bg-primary/20 rounded-full p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
                
                {filters.status !== 'all' && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                    {STATUS_OPTIONS.find(s => s.value === filters.status)?.label}
                    <button
                      onClick={() => updateFilter('status', 'all')}
                      className="ml-1 hover:bg-primary/20 rounded-full p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
                
                {(filters.dateRange.start || filters.dateRange.end) && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs bg-primary/10 text-primary">
                    {filters.dateRange.start} - {filters.dateRange.end}
                    <button
                      onClick={() => updateFilter('dateRange', { start: '', end: '' })}
                      className="ml-1 hover:bg-primary/20 rounded-full p-0.5"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default AdvancedFilters;