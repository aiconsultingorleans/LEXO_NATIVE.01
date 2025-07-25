'use client';

import React from 'react';
import { ChevronDown, AlertCircle } from 'lucide-react';

interface Option {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps {
  label?: string;
  name?: string;
  placeholder?: string;
  value?: string;
  options: Option[];
  error?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
  description?: string;
  onChange?: (value: string) => void;
}

export function Select({
  label,
  name,
  placeholder = 'Sélectionnez une option',
  value,
  options,
  error,
  required = false,
  disabled = false,
  className = '',
  description,
  onChange
}: SelectProps) {
  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onChange?.(e.target.value);
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {label && (
        <label 
          htmlFor={name}
          className="block text-sm font-medium text-gray-700"
        >
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      
      {description && (
        <p className="text-sm text-gray-500">{description}</p>
      )}

      <div className="relative">
        <select
          id={name}
          name={name}
          value={value}
          onChange={handleChange}
          disabled={disabled}
          className={`
            block w-full rounded-md border-gray-300 shadow-sm pl-3 pr-10 py-2
            focus:border-primary focus:ring-primary
            disabled:bg-gray-50 disabled:text-gray-500
            appearance-none bg-white
            ${error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
          `}
        >
          <option value="">{placeholder}</option>
          {options.map((option) => (
            <option
              key={option.value}
              value={option.value}
              disabled={option.disabled}
            >
              {option.label}
            </option>
          ))}
        </select>
        
        <div className="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
          <ChevronDown className="h-5 w-5 text-gray-400" />
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

interface SelectFieldProps extends SelectProps {
  label: string;
}

export function SelectField(props: SelectFieldProps) {
  return <Select {...props} />;
}