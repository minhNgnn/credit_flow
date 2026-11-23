import React from 'react';

export function IconButton({ icon, label, size = 'md', variant = 'ghost', onClick, disabled = false }) {
  const [hover, setHover] = React.useState(false);
  const dims = { sm: 28, md: 36, lg: 44 }[size];
  const variants = {
    ghost: { bg: 'transparent', hoverBg: 'var(--surface-sunken)', color: 'var(--text-secondary)' },
    solid: { bg: 'var(--brand-primary)', hoverBg: 'var(--brand-primary-hover)', color: '#fff' },
    outline: { bg: 'transparent', hoverBg: 'var(--surface-sunken)', color: 'var(--brand-primary)' },
  };
  const v = variants[variant] || variants.ghost;
  return (
    <button
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
      style={{
        width: dims, height: dims,
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        borderRadius: 'var(--radius-sm)',
        border: variant === 'outline' ? '1px solid var(--border-default)' : 'none',
        background: hover ? v.hoverBg : v.bg,
        color: v.color,
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        transition: 'background var(--duration-fast) var(--ease-standard)',
      }}
    >
      {icon}
    </button>
  );
}
