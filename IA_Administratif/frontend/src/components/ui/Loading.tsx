'use client';

import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
  text?: string;
}

const sizeClasses = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
  xl: 'h-12 w-12'
};

export function LoadingSpinner({ size = 'md', className = '', text }: LoadingSpinnerProps) {
  return (
    <div className={`flex items-center justify-center gap-2 ${className}`}>
      <Loader2 className={`animate-spin text-primary ${sizeClasses[size]}`} />
      {text && <span className="text-sm text-gray-600">{text}</span>}
    </div>
  );
}

interface LoadingOverlayProps {
  isLoading: boolean;
  text?: string;
  children: React.ReactNode;
}

export function LoadingOverlay({ isLoading, text = 'Chargement...', children }: LoadingOverlayProps) {
  return (
    <div className="relative">
      {children}
      {isLoading && (
        <div className="absolute inset-0 bg-white/80 backdrop-blur-sm flex items-center justify-center z-10">
          <LoadingSpinner size="lg" text={text} />
        </div>
      )}
    </div>
  );
}

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
}

export function Skeleton({ className = '', width, height }: SkeletonProps) {
  return (
    <div 
      className={`animate-pulse bg-gray-200 rounded ${className}`}
      style={{
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
      }}
    />
  );
}

export function DocumentSkeleton() {
  return (
    <div className="bg-white p-6 rounded-xl shadow-lg border border-gray-200">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-3">
            <Skeleton width={24} height={24} />
            <Skeleton width={200} height={20} />
            <Skeleton width={80} height={24} className="rounded-full" />
            <Skeleton width={100} height={16} />
          </div>

          <div className="flex flex-wrap gap-4 text-sm text-gray-600 mb-3">
            <Skeleton width={120} height={16} />
            <Skeleton width={140} height={16} />
            <Skeleton width={80} height={16} />
          </div>

          <div className="flex flex-wrap gap-2 mb-3">
            <Skeleton width={60} height={20} className="rounded" />
            <Skeleton width={80} height={20} className="rounded" />
            <Skeleton width={70} height={20} className="rounded" />
          </div>

          <Skeleton width="100%" height={32} />
        </div>

        <div className="flex items-center gap-2 ml-4">
          <Skeleton width={36} height={36} className="rounded" />
          <Skeleton width={36} height={36} className="rounded" />
        </div>
      </div>
    </div>
  );
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-8">
      {/* Hero Section Skeleton */}
      <div className="text-center bg-gray-100 p-8 rounded-2xl border">
        <Skeleton width={80} height={80} className="mx-auto rounded-2xl mb-6" />
        <Skeleton width={250} height={32} className="mx-auto mb-4" />
        <Skeleton width={400} height={20} className="mx-auto mb-8" />
        <div className="flex justify-center space-x-4">
          <Skeleton width={180} height={44} className="rounded" />
          <Skeleton width={160} height={44} className="rounded" />
        </div>
      </div>

      {/* Stats Cards Skeleton */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-white p-6 rounded-xl shadow-lg border">
            <div className="flex items-center">
              <Skeleton width={48} height={48} className="rounded-xl" />
              <div className="ml-4 flex-1">
                <Skeleton width={120} height={16} className="mb-2" />
                <Skeleton width={60} height={24} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Documents List Skeleton */}
      <div className="bg-white p-6 rounded-xl shadow-lg border">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <DocumentSkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}