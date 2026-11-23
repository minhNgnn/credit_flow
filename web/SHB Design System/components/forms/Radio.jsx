import React from 'react';

export function Radio({ label, checked, onChange, disabled = false, name }) {
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1, fontFamily: 'var(--font-body)' }}>
      <span
        onClick={() => !disabled && onChange && onChange()}
        style={{
          width: 18, height: 18, borderRadius: '50%',
          border: `1.5px solid ${checked ? 'var(--brand-primary)' : 'var(--border-strong)'}`,
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}
      >
        {checked && <span style={{ width: 9, height: 9, borderRadius: '50%', background: 'var(--brand-primary)' }} />}
      </span>
      {label && <span style={{ fontSize: 'var(--text-base)', color: 'var(--text-primary)' }}>{label}</span>}
    </label>
  );
}
