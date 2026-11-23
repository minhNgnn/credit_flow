import React from 'react';

const toneStyles = {
  neutral: { bg: 'var(--surface-inverse)', fg: '#fff' },
  success: { bg: 'var(--status-success-bg)', fg: 'var(--status-success-fg)' },
  warning: { bg: 'var(--status-warning-bg)', fg: 'var(--status-warning-fg)' },
  danger:  { bg: 'var(--status-danger-bg)', fg: 'var(--status-danger-fg)' },
};

export function Toast({ children, tone = 'neutral', onDismiss }) {
  const t = toneStyles[tone] || toneStyles.neutral;
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 12,
      background: t.bg, color: t.fg,
      padding: '12px 16px',
      borderRadius: 'var(--radius-md)',
      boxShadow: 'var(--shadow-lg)',
      fontFamily: 'var(--font-body)',
      fontSize: 'var(--text-sm)',
      fontWeight: 500,
      minWidth: 260,
    }}>
      <span style={{ flex: 1 }}>{children}</span>
      {onDismiss && (
        <button onClick={onDismiss} style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', opacity: 0.7, fontSize: 16 }}>×</button>
      )}
    </div>
  );
}
