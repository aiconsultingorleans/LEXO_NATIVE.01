import Link from 'next/link';
import { Button } from '@/components/ui/Button';

export default function AccessDeniedPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full text-center">
        <div className="mb-8">
          <div className="mx-auto w-24 h-24 bg-red-100 rounded-full flex items-center justify-center mb-6">
            <svg
              className="w-12 h-12 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          
          <h1 className="text-4xl font-bold text-gray-900 mb-4">403</h1>
          <h2 className="text-2xl font-semibold text-gray-700 mb-4">
            Accès refusé
          </h2>
          <p className="text-gray-600 mb-8">
            Vous n&apos;avez pas les permissions nécessaires pour accéder à cette page.
            Veuillez contacter un administrateur si vous pensez qu&apos;il s&apos;agit d&apos;une erreur.
          </p>
        </div>

        <div className="space-y-4">
          <Link href="/dashboard">
            <Button className="w-full">
              Retour au dashboard
            </Button>
          </Link>
          
          <Link href="/auth/logout">
            <Button variant="outline" className="w-full">
              Se déconnecter
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}