import React from 'react';

export function Tooltip({ children, label, side = 'top' }) {
  const [show, setShow] = React.useState(false);
  const pos = {
    top: { bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: 6 },
    bottom: { top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: 6 },
  }[side] || {};
  return (
    <span
      style={{ position: 'relative', display: 'inline-flex' }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <span style={{
          position: 'absolute', ...pos,
          background: 'var(--surface-inverse)',
          color: '#fff',
          fontSize: 'var(--text-xs)',
          fontFamily: 'var(--font-body)',
          padding: '5px 10px',
          borderRadius: 'var(--radius-xs)',
          whiteSpace: 'nowrap',
          boxShadow: 'var(--shadow-sm)',
          zIndex: 10,
        }}>
          {label}
        </span>
      )}
    </span>
  );
}
