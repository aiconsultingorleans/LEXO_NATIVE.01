'use client';

import { useEffect, Suspense } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Card, CardContent } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { loginSchema, LoginFormData } from '@/lib/validation/auth';
import { useAuth } from '@/hooks/useAuth';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isLoading, error, clearError, isAuthenticated } = useAuth();
  
  const reason = searchParams.get('reason');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  // Rediriger si déjà authentifié
  useEffect(() => {
    if (isAuthenticated) {
      router.push('/dashboard');
    }
  }, [isAuthenticated, router]);

  const onSubmit = async (data: LoginFormData) => {
    clearError();
    try {
      await login(data.email, data.password);
      router.push('/dashboard');
    } catch {
      // L'erreur est gérée dans le store
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Logo et titre moderne */}
        <div className="text-center">
          <div className="mx-auto w-16 h-16 bg-gradient-to-br from-primary to-primary-dark rounded-xl shadow-lg flex items-center justify-center mb-6">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-2">
            Connexion à LEXO v1
          </h2>
          <p className="text-foreground-secondary">
            Gérez vos documents administratifs intelligemment
          </p>
        </div>
        
        <Card className="shadow-2xl">
          <CardContent className="space-y-6">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {/* Message de déconnexion selon la raison */}
              {reason === 'session_expired' && (
                <div className="p-4 rounded-lg bg-warning/10 border border-warning/20 backdrop-blur-sm">
                  <div className="flex items-center gap-2">
                    <svg className="h-5 w-5 text-warning" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <p className="text-sm text-warning font-medium">Votre session a expiré. Veuillez vous reconnecter.</p>
                  </div>
                </div>
              )}
              
              {reason === 'invalid_token' && (
                <div className="p-4 rounded-lg bg-warning/10 border border-warning/20 backdrop-blur-sm">
                  <div className="flex items-center gap-2">
                    <svg className="h-5 w-5 text-warning" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <p className="text-sm text-warning font-medium">Votre authentification n&apos;est plus valide. Veuillez vous reconnecter.</p>
                  </div>
                </div>
              )}

              {error && (
                <div className="p-4 rounded-lg bg-error/10 border border-error/20 backdrop-blur-sm">
                  <div className="flex items-center gap-2">
                    <svg className="h-5 w-5 text-error" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    <p className="text-sm text-error font-medium">{error}</p>
                  </div>
                </div>
              )}

              <Input
                label="Email"
                type="email"
                placeholder="votre@email.com"
                autoComplete="email"
                error={errors.email?.message}
                {...register('email')}
              />

              <Input
                label="Mot de passe"
                type="password"
                placeholder="••••••••"
                autoComplete="current-password"
                error={errors.password?.message}
                {...register('password')}
              />

              <Button
                type="submit"
                className="w-full h-12 text-base font-semibold"
                loading={isLoading}
              >
                Se connecter
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-border" />
              </div>
              <div className="relative flex justify-center">
                <span className="px-4 bg-card-background text-sm text-foreground-muted">
                  Nouveau sur LEXO ?
                </span>
              </div>
            </div>

            <div className="text-center">
              <Link
                href="/auth/register"
                className="inline-flex items-center gap-2 text-sm text-primary hover:text-primary-hover font-medium transition-colors"
              >
                Créer un compte
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
                </svg>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center text-xs text-foreground-muted">
          <p>© 2025 LEXO v1. Assistant IA pour professions libérales.</p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    }>
      <LoginForm />
    </Suspense>
  );
}