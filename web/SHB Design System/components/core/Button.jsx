import React from 'react';

const sizeStyles = {
  sm: { padding: '6px 12px', fontSize: 'var(--text-sm)', height: '32px' },
  md: { padding: '9px 16px', fontSize: 'var(--text-base)', height: '40px' },
  lg: { padding: '12px 20px', fontSize: 'var(--text-lg)', height: '48px' },
};

const variantStyles = {
  primary: {
    background: 'var(--brand-primary)',
    color: 'var(--text-on-brand)',
    border: '1px solid var(--brand-primary)',
  },
  accent: {
    background: 'var(--brand-accent)',
    color: 'var(--text-on-accent)',
    border: '1px solid var(--brand-accent)',
  },
  secondary: {
    background: 'var(--surface-card)',
    color: 'var(--text-primary)',
    border: '1px solid var(--border-default)',
  },
  ghost: {
    background: 'transparent',
    color: 'var(--brand-primary)',
    border: '1px solid transparent',
  },
  danger: {
    background: 'var(--color-danger-600)',
    color: '#fff',
    border: '1px solid var(--color-danger-600)',
  },
};

const hoverBg = {
  primary: 'var(--brand-primary-hover)',
  accent: 'var(--brand-accent-hover)',
  secondary: 'var(--surface-sunken)',
  ghost: 'var(--surface-sunken)',
  danger: 'var(--color-danger-700)',
};

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  disabled = false,
  icon = null,
  onClick,
  type = 'button',
}) {
  const [hover, setHover] = React.useState(false);
  const [active, setActive] = React.useState(false);
  const v = variantStyles[variant] || variantStyles.primary;
  const s = sizeStyles[size] || sizeStyles.md;

  const style = {
    fontFamily: 'var(--font-body)',
    fontWeight: 600,
    borderRadius: 'var(--radius-sm)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    transition: 'background var(--duration-fast) var(--ease-standard), transform var(--duration-fast) var(--ease-standard), opacity var(--duration-fast)',
    opacity: disabled ? 0.45 : 1,
    ...s,
    ...v,
    background: disabled ? v.background : (hover ? hoverBg[variant] : v.background),
    transform: active && !disabled ? 'scale(0.98)' : 'scale(1)',
  };

  return (
    <button
      type={type}
      disabled={disabled}
      style={style}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => { setHover(false); setActive(false); }}
      onMouseDown={() => setActive(true)}
      onMouseUp={() => setActive(false)}
    >
      {icon}
      {children}
    </button>
  );
}
