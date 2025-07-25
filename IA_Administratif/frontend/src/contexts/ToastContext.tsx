'use client';

import React, { createContext, useContext, useState, useCallback } from 'react';
import { Toast, ToastType, ToastContainer } from '@/components/ui/Toast';

interface ToastContextType {
  toast: (toast: Omit<Toast, 'id'>) => void;
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  warning: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
  remove: (id: string) => void;
  clear: () => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const generateId = () => Math.random().toString(36).substring(2, 9);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = generateId();
    const newToast: Toast = { id, ...toast };
    
    setToasts(prev => [...prev, newToast]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(toast => toast.id !== id));
  }, []);

  const clearToasts = useCallback(() => {
    setToasts([]);
  }, []);

  const success = useCallback((title: string, description?: string) => {
    addToast({ type: 'success', title, description });
  }, [addToast]);

  const error = useCallback((title: string, description?: string) => {
    addToast({ type: 'error', title, description, duration: 7000 });
  }, [addToast]);

  const warning = useCallback((title: string, description?: string) => {
    addToast({ type: 'warning', title, description, duration: 6000 });
  }, [addToast]);

  const info = useCallback((title: string, description?: string) => {
    addToast({ type: 'info', title, description });
  }, [addToast]);

  const value: ToastContextType = {
    toast: addToast,
    success,
    error,
    warning,
    info,
    remove: removeToast,
    clear: clearToasts,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}