import React from 'react';

export function Input({
  label,
  placeholder,
  value,
  onChange,
  type = 'text',
  disabled = false,
  error,
  hint,
  size = 'md',
}) {
  const [focused, setFocused] = React.useState(false);
  const heights = { sm: 32, md: 40, lg: 48 };
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontFamily: 'var(--font-body)', width: '100%' }}>
      {label && <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{label}</span>}
      <input
        type={type}
        value={value}
        placeholder={placeholder}
        disabled={disabled}
        onChange={onChange}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          height: heights[size],
          padding: '0 12px',
          borderRadius: 'var(--radius-sm)',
          border: `1px solid ${error ? 'var(--color-danger-600)' : focused ? 'var(--border-focus)' : 'var(--border-default)'}`,
          boxShadow: focused ? (error ? 'var(--shadow-focus-accent)' : 'var(--shadow-focus)') : 'none',
          fontSize: 'var(--text-base)',
          fontFamily: 'var(--font-body)',
          color: 'var(--text-primary)',
          background: disabled ? 'var(--surface-sunken)' : 'var(--surface-card)',
          outline: 'none',
          transition: 'border-color var(--duration-fast) var(--ease-standard), box-shadow var(--duration-fast) var(--ease-standard)',
        }}
      />
      {error ? (
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-danger-700)' }}>{error}</span>
      ) : hint ? (
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>{hint}</span>
      ) : null}
    </label>
  );
}
