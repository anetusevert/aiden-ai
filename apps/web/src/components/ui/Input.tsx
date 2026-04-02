import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  optional?: boolean;
}

export function Input({
  label,
  hint,
  error,
  optional = false,
  className = '',
  id,
  ...props
}: InputProps) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, '-');
  const inputClasses = ['form-input', error ? 'error' : '', className]
    .filter(Boolean)
    .join(' ');

  if (!label) {
    return <input id={inputId} className={inputClasses} {...props} />;
  }

  return (
    <div className="form-group">
      <label htmlFor={inputId} className="form-label">
        {label}
        {optional && <span className="form-label-optional">(optional)</span>}
      </label>
      <input id={inputId} className={inputClasses} {...props} />
      {hint && !error && <span className="form-hint">{hint}</span>}
      {error && <span className="form-hint text-error">{error}</span>}
    </div>
  );
}

export interface FormGroupProps {
  label?: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  htmlFor?: string;
  children: React.ReactNode;
}

export function FormGroup({
  label,
  hint,
  error,
  optional = false,
  htmlFor,
  children,
}: FormGroupProps) {
  return (
    <div className="form-group">
      {label && (
        <label htmlFor={htmlFor} className="form-label">
          {label}
          {optional && <span className="form-label-optional">(optional)</span>}
        </label>
      )}
      {children}
      {hint && !error && <span className="form-hint">{hint}</span>}
      {error && <span className="form-hint text-error">{error}</span>}
    </div>
  );
}
