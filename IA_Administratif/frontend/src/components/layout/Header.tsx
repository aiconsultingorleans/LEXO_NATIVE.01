'use client';

import { Bell, Search, Settings, User } from 'lucide-react';
import { Button } from '@/components/ui/Button';

export function Header() {
  return (
    <header className="bg-background-secondary border-b border-card-border h-16 flex items-center justify-between px-6 backdrop-blur-sm bg-background-secondary/80 sticky top-0 z-50">
      <div className="flex items-center space-x-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-primary to-primary-dark rounded-lg flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div>
            <h1 className="text-lg font-bold text-foreground">LEXO v1</h1>
          </div>
        </div>
        <div className="h-6 w-px bg-border mx-2"></div>
        <span className="text-sm text-foreground-muted">Assistant IA Administratif</span>
      </div>

      <div className="flex-1 max-w-lg mx-8">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-foreground-muted h-4 w-4" />
          <input
            type="text"
            placeholder="Rechercher dans vos documents..."
            className="w-full pl-12 pr-4 py-2.5 bg-background-tertiary border border-border rounded-lg text-foreground placeholder:text-foreground-muted focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all duration-200"
          />
        </div>
      </div>

      <div className="flex items-center space-x-1">
        <Button variant="ghost" size="sm" className="hover:bg-hover-background">
          <Bell className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" className="hover:bg-hover-background">
          <Settings className="h-4 w-4" />
        </Button>
        <Button variant="ghost" size="sm" className="hover:bg-hover-background">
          <User className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}