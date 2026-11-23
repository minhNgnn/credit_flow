import React from 'react';

export function Tabs({ tabs = [], value, onChange }) {
  return (
    <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--border-subtle)', fontFamily: 'var(--font-body)' }}>
      {tabs.map((t) => {
        const active = t.value === value;
        return (
          <button
            key={t.value}
            onClick={() => onChange && onChange(t.value)}
            style={{
              padding: '10px 16px',
              background: 'transparent',
              border: 'none',
              borderBottom: `2px solid ${active ? 'var(--brand-accent)' : 'transparent'}`,
              color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontWeight: active ? 600 : 500,
              fontSize: 'var(--text-sm)',
              cursor: 'pointer',
              transition: 'color var(--duration-fast) var(--ease-standard), border-color var(--duration-fast) var(--ease-standard)',
            }}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}
