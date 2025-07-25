'use client';

import { useState } from 'react';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FormField } from '@/components/ui/FormField';
import { Select } from '@/components/ui/Select';
import { Search, Filter, FileText, Calendar, Tag } from 'lucide-react';

export default function SearchPage() {
  return (
    <AuthGuard requireAuth={true}>
      <SearchContent />
    </AuthGuard>
  );
}

function SearchContent() {
  const [query, setQuery] = useState('');
  const [searchType, setSearchType] = useState('semantic');
  const [category, setCategory] = useState('all');
  const [isSearching, setIsSearching] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  const handleSearch = async () => {
    setIsSearching(true);
    try {
      // Simuler une recherche
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Résultats simulés
      setResults([
        {
          id: 1,
          filename: 'facture_edf_janvier_2025.pdf',
          category: 'facture',
          relevanceScore: 0.95,
          snippet: 'Facture d\'électricité pour la période de janvier 2025, montant total: 145.67€',
          date: '2025-01-15',
          entities: ['EDF', '145.67€', 'janvier 2025']
        },
        {
          id: 2,
          filename: 'attestation_pole_emploi.pdf',
          category: 'attestation',
          relevanceScore: 0.87,
          snippet: 'Attestation de situation vis-à-vis de l\'emploi délivrée par Pôle Emploi',
          date: '2025-01-20',
          entities: ['Pôle Emploi', 'attestation']
        }
      ]);
    } catch (error) {
      console.error('Search failed:', error);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <MainLayout>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Recherche RAG</h1>
          <p className="text-foreground-secondary mt-2">
            Recherchez dans vos documents avec intelligence artificielle
          </p>
        </div>

        {/* Search Form */}
        <Card className="p-6">
          <div className="space-y-6">
            <div className="flex gap-4">
              <div className="flex-1">
                <FormField
                  label="Recherche sémantique"
                  value={query}
                  onChange={setQuery}
                  placeholder="Ex: Factures d'électricité de janvier, ou documents avec montant supérieur à 100€"
                />
              </div>
              <div className="flex items-end">
                <Button 
                  onClick={handleSearch}
                  disabled={!query.trim() || isSearching}
                  className="px-8"
                >
                  {isSearching ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                  ) : (
                    <Search className="h-4 w-4 mr-2" />
                  )}
                  Rechercher
                </Button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Select
                label="Type de recherche"
                value={searchType}
                onChange={setSearchType}
                options={[
                  { value: 'semantic', label: 'Sémantique (IA)' },
                  { value: 'keyword', label: 'Mots-clés' },
                  { value: 'fulltext', label: 'Texte intégral' }
                ]}
              />
              <Select
                label="Catégorie"
                value={category}
                onChange={setCategory}
                options={[
                  { value: 'all', label: 'Toutes les catégories' },
                  { value: 'facture', label: 'Factures' },
                  { value: 'impot', label: 'Impôts' },
                  { value: 'rib', label: 'RIB' },
                  { value: 'attestation', label: 'Attestations' },
                  { value: 'contrat', label: 'Contrats' }
                ]}
              />
            </div>
          </div>
        </Card>

        {/* Search Results */}
        {results.length > 0 && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold text-foreground">
                Résultats de recherche ({results.length})
              </h3>
              <Button variant="outline" size="sm">
                <Filter className="h-4 w-4 mr-2" />
                Filtrer
              </Button>
            </div>

            <div className="space-y-4">
              {results.map((result) => (
                <div key={result.id} className="border border-card-border rounded-lg p-6 hover:shadow-md transition-shadow">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <FileText className="h-5 w-5 text-foreground-muted" />
                      <h4 className="font-medium text-foreground">{result.filename}</h4>
                      <span className="px-2 py-1 text-xs font-medium rounded-full bg-primary/10 text-primary">
                        {result.category}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-success font-medium">
                        {Math.round(result.relevanceScore * 100)}% pertinence
                      </span>
                    </div>
                  </div>

                  <p className="text-foreground-secondary mb-4 line-clamp-2">
                    {result.snippet}
                  </p>

                  <div className="flex items-center gap-6 text-sm text-foreground-muted">
                    <div className="flex items-center gap-1">
                      <Calendar className="h-4 w-4" />
                      <span>{new Date(result.date).toLocaleDateString('fr-FR')}</span>
                    </div>
                    {result.entities.length > 0 && (
                      <div className="flex items-center gap-2">
                        <Tag className="h-4 w-4" />
                        <div className="flex gap-1">
                          {result.entities.slice(0, 3).map((entity: string, idx: number) => (
                            <span key={idx} className="px-2 py-1 bg-background-tertiary text-foreground-muted text-xs rounded">
                              {entity}
                            </span>
                          ))}
                          {result.entities.length > 3 && (
                            <span className="text-xs text-foreground-muted">
                              +{result.entities.length - 3} autres
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Help Section */}
        <Card className="p-6 bg-primary/5 border-primary/20">
          <h3 className="text-lg font-semibold text-foreground mb-4">Exemples de recherches</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="font-medium text-foreground mb-2">Recherche par contenu :</h4>
              <ul className="space-y-1 text-foreground-secondary">
                <li>• "factures d'électricité de janvier"</li>
                <li>• "documents avec montant supérieur à 100€"</li>
                <li>• "attestations de Pôle Emploi"</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-foreground mb-2">Recherche par entités :</h4>
              <ul className="space-y-1 text-foreground-secondary">
                <li>• "EDF" (fournisseur)</li>
                <li>• "2025" (année)</li>
                <li>• "IBAN" (type de document)</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </MainLayout>
  );
}