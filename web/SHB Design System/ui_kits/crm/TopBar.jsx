function TopBar({ title, rmName = 'J. Tran' }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      padding: '18px 28px', borderBottom: '1px solid var(--border-subtle)',
      background: 'var(--surface-card)', fontFamily: 'var(--font-body)',
    }}>
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 'var(--text-2xl)', color: 'var(--text-primary)' }}>{title}</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{
          width: 34, height: 34, borderRadius: '50%', background: 'var(--color-navy-100)',
          color: 'var(--brand-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: 13,
        }}>{rmName.split(' ').map(s => s[0]).join('')}</div>
        <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{rmName}</span>
      </div>
    </div>
  );
}
window.TopBar = TopBar;
