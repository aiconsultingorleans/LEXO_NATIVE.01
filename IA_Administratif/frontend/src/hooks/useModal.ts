'use client';

import { useState, useCallback } from 'react';

export function useModal(initialState = false) {
  const [isOpen, setIsOpen] = useState(initialState);

  const openModal = useCallback(() => {
    setIsOpen(true);
  }, []);

  const closeModal = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggleModal = useCallback(() => {
    setIsOpen(prev => !prev);
  }, []);

  return {
    isOpen,
    openModal,
    closeModal,
    toggleModal,
    setIsOpen
  };
}

export function useConfirmDialog() {
  const [state, setState] = useState<{
    isOpen: boolean;
    title: string;
    description: string;
    onConfirm: () => void;
    variant?: 'danger' | 'warning' | 'info';
    confirmText?: string;
    cancelText?: string;
  }>({
    isOpen: false,
    title: '',
    description: '',
    onConfirm: () => {}
  });

  const confirm = useCallback((options: {
    title: string;
    description: string;
    onConfirm: () => void;
    variant?: 'danger' | 'warning' | 'info';
    confirmText?: string;
    cancelText?: string;
  }) => {
    setState({
      isOpen: true,
      ...options
    });
  }, []);

  const close = useCallback(() => {
    setState(prev => ({ ...prev, isOpen: false }));
  }, []);

  return {
    ...state,
    confirm,
    close
  };
}