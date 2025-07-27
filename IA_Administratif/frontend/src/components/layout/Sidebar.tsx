'use client';

import { 
  Home, 
  FileText, 
  Upload, 
  Search, 
  BarChart3, 
  Settings,
  MessageSquare 
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { FolderTreeView } from '@/components/FolderTreeView';

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: Home },
  { name: 'Tous les documents', href: '/documents', icon: FileText },
  { name: 'Upload', href: '/upload', icon: Upload },
  { name: 'Chat Mistral', href: '/chat', icon: MessageSquare },
  { name: 'Recherche RAG', href: '/search', icon: Search },
];


const bottomNavigation = [
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Paramètres', href: '/settings', icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 bg-background-secondary border-r border-card-border min-h-screen fixed left-0 top-16 z-40">
      <nav className="p-4 h-full overflow-y-auto">
        {/* Navigation principale */}
        <div className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  'flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200 group',
                  isActive
                    ? 'bg-primary/10 text-primary border border-primary/20'
                    : 'text-foreground-secondary hover:bg-hover-background hover:text-foreground'
                )}
              >
                <item.icon className={cn(
                  "mr-3 h-5 w-5 transition-colors",
                  isActive ? "text-primary" : "text-foreground-muted group-hover:text-foreground"
                )} />
                {item.name}
              </Link>
            );
          })}
        </div>

        {/* Structure des dossiers OCR */}
        <div className="mt-8">
          <FolderTreeView />
        </div>

        {/* Navigation du bas */}
        <div className="mt-8 pt-6 border-t border-card-border">
          <div className="space-y-1">
            {bottomNavigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  className={cn(
                    'flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-all duration-200 group',
                    isActive
                      ? 'bg-primary/10 text-primary border border-primary/20'
                      : 'text-foreground-secondary hover:bg-hover-background hover:text-foreground'
                  )}
                >
                  <item.icon className={cn(
                    "mr-3 h-5 w-5 transition-colors",
                    isActive ? "text-primary" : "text-foreground-muted group-hover:text-foreground"
                  )} />
                  {item.name}
                </Link>
              );
            })}
          </div>
        </div>
      </nav>
    </aside>
  );
}