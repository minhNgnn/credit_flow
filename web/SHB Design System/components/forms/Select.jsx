import React from 'react';

export function Select({ label, value, onChange, options = [], disabled = false, hint }) {
  const [focused, setFocused] = React.useState(false);
  return (
    <label style={{ display: 'flex', flexDirection: 'column', gap: 6, fontFamily: 'var(--font-body)', width: '100%' }}>
      {label && <span style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{label}</span>}
      <select
        value={value}
        onChange={onChange}
        disabled={disabled}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        style={{
          height: 40,
          padding: '0 12px',
          borderRadius: 'var(--radius-sm)',
          border: `1px solid ${focused ? 'var(--border-focus)' : 'var(--border-default)'}`,
          boxShadow: focused ? 'var(--shadow-focus)' : 'none',
          fontSize: 'var(--text-base)',
          fontFamily: 'var(--font-body)',
          color: 'var(--text-primary)',
          background: disabled ? 'var(--surface-sunken)' : 'var(--surface-card)',
          outline: 'none',
        }}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
      {hint && <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>{hint}</span>}
    </label>
  );
}
