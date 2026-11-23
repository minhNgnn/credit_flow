function Sidebar({ active = 'dashboard', onNavigate }) {
  const items = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'customers', label: 'Customers' },
    { key: 'deals', label: 'Deals' },
    { key: 'accounts', label: 'Accounts' },
    { key: 'reports', label: 'Reports' },
  ];
  return (
    <div style={{
      width: 220, background: 'var(--surface-card)', color: 'var(--text-primary)',
      display: 'flex', flexDirection: 'column', padding: '20px 12px', gap: 4,
      fontFamily: 'var(--font-body)', flexShrink: 0,
      borderRight: '1px solid var(--border-subtle)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 10px', marginBottom: 24 }}>
        <img src="../../assets/logo/shb-logo.png" alt="SHB" style={{ height: 24 }} />
      </div>
      {items.map((it) => {
        const isActive = it.key === active;
        return (
          <div
            key={it.key}
            onClick={() => onNavigate && onNavigate(it.key)}
            style={{
              padding: '10px 14px', borderRadius: 'var(--radius-sm)', cursor: 'pointer',
              fontSize: 'var(--text-sm)', fontWeight: isActive ? 600 : 500,
              background: isActive ? 'var(--surface-accent-soft)' : 'transparent',
              color: isActive ? 'var(--brand-primary)' : 'var(--text-secondary)',
              borderLeft: isActive ? '3px solid var(--brand-primary)' : '3px solid transparent',
              transition: 'background var(--duration-fast) var(--ease-standard)',
            }}
          >
            {it.label}
          </div>
        );
      })}
    </div>
  );
}
window.Sidebar = Sidebar;
