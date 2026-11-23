import React from 'react';

export function Card({ children, padding = 'var(--space-6)', style = {} }) {
  return (
    <div
      style={{
        background: 'var(--surface-card)',
        borderRadius: 'var(--radius-md)',
        boxShadow: 'var(--shadow-sm)',
        border: '1px solid var(--border-subtle)',
        padding,
        ...style,
      }}
    >
      {children}
    </div>
  );
}
