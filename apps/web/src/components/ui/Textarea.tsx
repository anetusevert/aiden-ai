import React from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
  optional?: boolean;
}

export function Textarea({
  label,
  hint,
  error,
  optional = false,
  className = '',
  id,
  ...props
}: TextareaProps) {
  const textareaId = id || label?.toLowerCase().replace(/\s+/g, '-');
  const textareaClasses = ['form-textarea', error ? 'error' : '', className]
    .filter(Boolean)
    .join(' ');

  if (!label) {
    return <textarea id={textareaId} className={textareaClasses} {...props} />;
  }

  return (
    <div className="form-group">
      <label htmlFor={textareaId} className="form-label">
        {label}
        {optional && <span className="form-label-optional">(optional)</span>}
      </label>
      <textarea id={textareaId} className={textareaClasses} {...props} />
      {hint && !error && <span className="form-hint">{hint}</span>}
      {error && <span className="form-hint text-error">{error}</span>}
    </div>
  );
}
