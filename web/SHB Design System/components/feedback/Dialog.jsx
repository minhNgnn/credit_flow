import React from 'react';

export function Dialog({ open, title, children, onClose, footer }) {
  if (!open) return null;
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'var(--surface-overlay)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100,
    }} onClick={onClose}>
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-lg)', width: 420, maxWidth: '90vw',
          fontFamily: 'var(--font-body)',
        }}
      >
        <div style={{ padding: '20px 24px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 'var(--text-xl)' }}>{title}</div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: 'var(--text-tertiary)' }}>×</button>
        </div>
        <div style={{ padding: 24, color: 'var(--text-primary)', fontSize: 'var(--text-base)' }}>{children}</div>
        {footer && <div style={{ padding: '16px 24px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'flex-end', gap: 10 }}>{footer}</div>}
      </div>
    </div>
  );
}
