'use client';

import { useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/contexts/ToastContext';
import AuthGuard from '@/components/auth/AuthGuard';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { FormField } from '@/components/ui/FormField';
import { Select } from '@/components/ui/Select';
import { 
  User, 
  Bell, 
  Shield, 
  HardDrive,
  Palette,
  Download,
  Trash2,
  Save,
  Eye,
  EyeOff
} from 'lucide-react';

export default function SettingsPage() {
  return (
    <AuthGuard requireAuth={true}>
      <SettingsContent />
    </AuthGuard>
  );
}

function SettingsContent() {
  const { user, getUserFullName } = useAuth();
  const toast = useToast();
  const [showPassword, setShowPassword] = useState(false);
  const [settings, setSettings] = useState({
    // Profil utilisateur
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    email: user?.email || '',
    
    // Préférences
    language: 'fr',
    theme: 'system',
    dateFormat: 'dd/mm/yyyy',
    
    // Notifications
    emailNotifications: true,
    ocrCompleteNotification: true,
    errorNotifications: true,
    weeklyReport: false,
    
    // OCR Settings
    ocrEngine: 'hybrid',
    confidenceThreshold: 70,
    autoClassification: true,
    keepOriginalFiles: true,
    
    // Sécurité
    sessionTimeout: 30,
    twoFactorAuth: false,
    apiAccess: false
  });

  const handleSave = async () => {
    try {
      // Simuler la sauvegarde
      await new Promise(resolve => setTimeout(resolve, 1000));
      toast.success('Paramètres sauvegardés', 'Vos préférences ont été mises à jour');
    } catch (error) {
      toast.error('Erreur', 'Impossible de sauvegarder les paramètres');
    }
  };

  const handleExportData = () => {
    toast.info('Export en cours', 'Votre export de données sera disponible sous peu');
  };

  const handleDeleteAccount = () => {
    toast.error('Fonction indisponible', 'La suppression de compte n\'est pas encore implémentée');
  };

  return (
    <MainLayout>
      <div className="space-y-8 max-w-4xl">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">Paramètres</h1>
          <p className="text-foreground-secondary mt-2">
            Gérez vos préférences et paramètres de compte
          </p>
        </div>

        {/* Profil utilisateur */}
        <Card className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-primary/10 rounded-xl">
              <User className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Profil utilisateur</h2>
              <p className="text-sm text-foreground-secondary">Informations personnelles et compte</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <FormField
              label="Prénom"
              value={settings.firstName}
              onChange={(value) => setSettings(prev => ({ ...prev, firstName: value }))}
              placeholder="Votre prénom"
            />
            <FormField
              label="Nom"
              value={settings.lastName}
              onChange={(value) => setSettings(prev => ({ ...prev, lastName: value }))}
              placeholder="Votre nom"
            />
            <FormField
              label="Email"
              type="email"
              value={settings.email}
              onChange={(value) => setSettings(prev => ({ ...prev, email: value }))}
              placeholder="votre@email.com"
            />
            <div className="relative">
              <FormField
                label="Nouveau mot de passe"
                type={showPassword ? "text" : "password"}
                placeholder="••••••••"
              />
              <button
                type="button"
                className="absolute right-3 top-9 text-foreground-muted hover:text-foreground"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
        </Card>

        {/* Préférences */}
        <Card className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-purple-500/10 rounded-xl">
              <Palette className="h-6 w-6 text-purple-500" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Préférences</h2>
              <p className="text-sm text-foreground-secondary">Interface et affichage</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <Select
              label="Langue"
              value={settings.language}
              onChange={(value) => setSettings(prev => ({ ...prev, language: value }))}
              options={[
                { value: 'fr', label: 'Français' },
                { value: 'en', label: 'English' },
                { value: 'es', label: 'Español' }
              ]}
            />
            <Select
              label="Thème"
              value={settings.theme}
              onChange={(value) => setSettings(prev => ({ ...prev, theme: value }))}
              options={[
                { value: 'light', label: 'Clair' },
                { value: 'dark', label: 'Sombre' },
                { value: 'system', label: 'Système' }
              ]}
            />
            <Select
              label="Format de date"
              value={settings.dateFormat}
              onChange={(value) => setSettings(prev => ({ ...prev, dateFormat: value }))}
              options={[
                { value: 'dd/mm/yyyy', label: 'DD/MM/YYYY' },
                { value: 'mm/dd/yyyy', label: 'MM/DD/YYYY' },
                { value: 'yyyy-mm-dd', label: 'YYYY-MM-DD' }
              ]}
            />
          </div>
        </Card>

        {/* Notifications */}
        <Card className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-yellow-500/10 rounded-xl">
              <Bell className="h-6 w-6 text-yellow-500" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Notifications</h2>
              <p className="text-sm text-foreground-secondary">Préférences de notifications</p>
            </div>
          </div>

          <div className="space-y-4">
            {[
              { key: 'emailNotifications', label: 'Notifications par email', description: 'Recevoir des notifications par email' },
              { key: 'ocrCompleteNotification', label: 'OCR terminé', description: 'Notification quand l\'OCR est terminé' },
              { key: 'errorNotifications', label: 'Notifications d\'erreur', description: 'Alertes en cas d\'erreur de traitement' },
              { key: 'weeklyReport', label: 'Rapport hebdomadaire', description: 'Résumé hebdomadaire de l\'activité' }
            ].map((notification) => (
              <div key={notification.key} className="flex items-center justify-between py-3 border-b border-card-border last:border-0">
                <div>
                  <p className="font-medium text-foreground">{notification.label}</p>
                  <p className="text-sm text-foreground-secondary">{notification.description}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={settings[notification.key as keyof typeof settings] as boolean}
                    onChange={(e) => setSettings(prev => ({ ...prev, [notification.key]: e.target.checked }))}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            ))}
          </div>
        </Card>

        {/* Paramètres OCR */}
        <Card className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-blue-500/10 rounded-xl">
              <HardDrive className="h-6 w-6 text-blue-500" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Paramètres OCR</h2>
              <p className="text-sm text-foreground-secondary">Configuration du moteur OCR</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <Select
              label="Moteur OCR"
              value={settings.ocrEngine}
              onChange={(value) => setSettings(prev => ({ ...prev, ocrEngine: value }))}
              options={[
                { value: 'tesseract', label: 'Tesseract (Rapide)' },
                { value: 'trocr', label: 'TrOCR (Précis)' },
                { value: 'hybrid', label: 'Hybride (Recommandé)' }
              ]}
            />
            <FormField
              label="Seuil de confiance (%)"
              type="number"
              value={settings.confidenceThreshold.toString()}
              onChange={(value) => setSettings(prev => ({ ...prev, confidenceThreshold: parseInt(value) || 70 }))}
              min="0"
              max="100"
            />
          </div>

          <div className="space-y-4">
            {[
              { key: 'autoClassification', label: 'Classification automatique', description: 'Classer automatiquement les documents' },
              { key: 'keepOriginalFiles', label: 'Conserver les fichiers originaux', description: 'Garder une copie des fichiers uploadés' }
            ].map((setting) => (
              <div key={setting.key} className="flex items-center justify-between py-3 border-b border-card-border last:border-0">
                <div>
                  <p className="font-medium text-foreground">{setting.label}</p>
                  <p className="text-sm text-foreground-secondary">{setting.description}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={settings[setting.key as keyof typeof settings] as boolean}
                    onChange={(e) => setSettings(prev => ({ ...prev, [setting.key]: e.target.checked }))}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            ))}
          </div>
        </Card>

        {/* Sécurité */}
        <Card className="p-6">
          <div className="flex items-center gap-4 mb-6">
            <div className="p-3 bg-green-500/10 rounded-xl">
              <Shield className="h-6 w-6 text-green-500" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-foreground">Sécurité</h2>
              <p className="text-sm text-foreground-secondary">Paramètres de sécurité et confidentialité</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <Select
              label="Délai de session (minutes)"
              value={settings.sessionTimeout.toString()}
              onChange={(value) => setSettings(prev => ({ ...prev, sessionTimeout: parseInt(value) }))}
              options={[
                { value: '15', label: '15 minutes' },
                { value: '30', label: '30 minutes' },
                { value: '60', label: '1 heure' },
                { value: '480', label: '8 heures' }
              ]}
            />
          </div>

          <div className="space-y-4 mb-6">
            {[
              { key: 'twoFactorAuth', label: 'Authentification à deux facteurs', description: 'Sécurité renforcée avec 2FA' },
              { key: 'apiAccess', label: 'Accès API', description: 'Autoriser l\'accès via API' }
            ].map((setting) => (
              <div key={setting.key} className="flex items-center justify-between py-3 border-b border-card-border last:border-0">
                <div>
                  <p className="font-medium text-foreground">{setting.label}</p>
                  <p className="text-sm text-foreground-secondary">{setting.description}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    className="sr-only peer"
                    checked={settings[setting.key as keyof typeof settings] as boolean}
                    onChange={(e) => setSettings(prev => ({ ...prev, [setting.key]: e.target.checked }))}
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
                </label>
              </div>
            ))}
          </div>
        </Card>

        {/* Actions */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold text-foreground mb-4">Actions</h2>
          <div className="flex flex-wrap gap-4">
            <Button onClick={handleSave} className="flex-1 sm:flex-none">
              <Save className="h-4 w-4 mr-2" />
              Sauvegarder
            </Button>
            <Button variant="outline" onClick={handleExportData}>
              <Download className="h-4 w-4 mr-2" />
              Exporter mes données
            </Button>
            <Button variant="outline" onClick={handleDeleteAccount} className="text-error hover:bg-error/10">
              <Trash2 className="h-4 w-4 mr-2" />
              Supprimer le compte
            </Button>
          </div>
        </Card>
      </div>
    </MainLayout>
  );
}