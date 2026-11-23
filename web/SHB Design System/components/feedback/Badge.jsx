import React from 'react';

const toneStyles = {
  neutral: { bg: 'var(--surface-sunken)', fg: 'var(--text-secondary)' },
  success: { bg: 'var(--status-success-bg)', fg: 'var(--status-success-fg)' },
  warning: { bg: 'var(--status-warning-bg)', fg: 'var(--status-warning-fg)' },
  danger:  { bg: 'var(--status-danger-bg)', fg: 'var(--status-danger-fg)' },
  info:    { bg: 'var(--status-info-bg)', fg: 'var(--status-info-fg)' },
  accent:  { bg: 'var(--color-orange-100)', fg: 'var(--color-orange-800)' },
};

export function Badge({ children, tone = 'neutral' }) {
  const t = toneStyles[tone] || toneStyles.neutral;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center',
      padding: '3px 10px',
      borderRadius: 'var(--radius-full)',
      fontSize: 'var(--text-xs)',
      fontWeight: 600,
      fontFamily: 'var(--font-body)',
      background: t.bg,
      color: t.fg,
      lineHeight: 1.4,
    }}>
      {children}
    </span>
  );
}
