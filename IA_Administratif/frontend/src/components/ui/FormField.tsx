'use client';

import React from 'react';
import { Input } from './Input';
import { AlertCircle } from 'lucide-react';

interface FormFieldProps {
  label: string;
  name: string;
  type?: string;
  placeholder?: string;
  value?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  description?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onBlur?: (e: React.FocusEvent<HTMLInputElement>) => void;
}

export function FormField({
  label,
  name,
  type = 'text',
  placeholder,
  value,
  error,
  required = false,
  disabled = false,
  className = '',
  description,
  onChange,
  onBlur,
  ...props
}: FormFieldProps) {
  return (
    <div className={`space-y-2 ${className}`}>
      <label 
        htmlFor={name}
        className="block text-sm font-medium text-gray-700"
      >
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {description && (
        <p className="text-sm text-gray-500">{description}</p>
      )}

      <Input
        id={name}
        name={name}
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        disabled={disabled}
        className={error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
        {...props}
      />

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

interface TextAreaFieldProps {
  label: string;
  name: string;
  placeholder?: string;
  value?: string;
  error?: string;
  required?: boolean;
  disabled?: boolean;
  rows?: number;
  className?: string;
  description?: string;
  onChange?: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onBlur?: (e: React.FocusEvent<HTMLTextAreaElement>) => void;
}

export function TextAreaField({
  label,
  name,
  placeholder,
  value,
  error,
  required = false,
  disabled = false,
  rows = 3,
  className = '',
  description,
  onChange,
  onBlur,
  ...props
}: TextAreaFieldProps) {
  return (
    <div className={`space-y-2 ${className}`}>
      <label 
        htmlFor={name}
        className="block text-sm font-medium text-gray-700"
      >
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {description && (
        <p className="text-sm text-gray-500">{description}</p>
      )}

      <textarea
        id={name}
        name={name}
        rows={rows}
        placeholder={placeholder}
        value={value}
        onChange={onChange}
        onBlur={onBlur}
        disabled={disabled}
        className={`
          block w-full rounded-md border-gray-300 shadow-sm
          focus:border-primary focus:ring-primary
          disabled:bg-gray-50 disabled:text-gray-500
          ${error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
        `}
        {...props}
      />

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}