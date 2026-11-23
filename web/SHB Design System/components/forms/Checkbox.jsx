import React from 'react';

export function Checkbox({ label, checked, onChange, disabled = false }) {
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 8, cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1, fontFamily: 'var(--font-body)' }}>
      <span
        onClick={() => !disabled && onChange && onChange(!checked)}
        style={{
          width: 18, height: 18,
          borderRadius: 'var(--radius-xs)',
          border: `1.5px solid ${checked ? 'var(--brand-primary)' : 'var(--border-strong)'}`,
          background: checked ? 'var(--brand-primary)' : 'var(--surface-card)',
          display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
          transition: 'background var(--duration-fast) var(--ease-standard), border-color var(--duration-fast) var(--ease-standard)',
          flexShrink: 0,
        }}
      >
        {checked && (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        )}
      </span>
      {label && <span style={{ fontSize: 'var(--text-base)', color: 'var(--text-primary)' }}>{label}</span>}
    </label>
  );
}
