import React from 'react';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
  optional?: boolean;
  options: SelectOption[];
  placeholder?: string;
}

export function Select({
  label,
  hint,
  error,
  optional = false,
  options,
  placeholder,
  className = '',
  id,
  ...props
}: SelectProps) {
  const selectId = id || label?.toLowerCase().replace(/\s+/g, '-');
  const selectClasses = ['form-select', error ? 'error' : '', className]
    .filter(Boolean)
    .join(' ');

  const selectElement = (
    <select id={selectId} className={selectClasses} {...props}>
      {placeholder && (
        <option value="" disabled>
          {placeholder}
        </option>
      )}
      {options.map(option => (
        <option
          key={option.value}
          value={option.value}
          disabled={option.disabled}
        >
          {option.label}
        </option>
      ))}
    </select>
  );

  if (!label) {
    return selectElement;
  }

  return (
    <div className="form-group">
      <label htmlFor={selectId} className="form-label">
        {label}
        {optional && <span className="form-label-optional">(optional)</span>}
      </label>
      {selectElement}
      {hint && !error && <span className="form-hint">{hint}</span>}
      {error && <span className="form-hint text-error">{error}</span>}
    </div>
  );
}
