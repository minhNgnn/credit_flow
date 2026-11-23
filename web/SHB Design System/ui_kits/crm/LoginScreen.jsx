function LoginScreen({ onLogin }) {
  const { Input, Button } = window.SHBDesignSystem_1dd17a;
  return (
    <div style={{
      minHeight: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--surface-inverse)', fontFamily: 'var(--font-body)',
    }}>
      <div style={{ background: 'var(--surface-card)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-lg)', padding: 40, width: 360, display: 'flex', flexDirection: 'column', gap: 20 }}>
        <img src="../../assets/logo/shb-logo.png" alt="SHB" style={{ height: 32, alignSelf: 'flex-start' }} />
        <div>
          <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 'var(--text-2xl)' }}>Sign in</div>
          <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginTop: 4 }}>Access your relationship management workspace.</div>
        </div>
        <Input label="Work email" placeholder="you@shbbank.com" />
        <Input label="Password" type="password" placeholder="••••••••" />
        <Button variant="primary" size="lg" onClick={onLogin} style={{ width: '100%' }}>Sign in</Button>
        <div style={{ textAlign: 'center', fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>Protected by SHB's secure access policy.</div>
      </div>
    </div>
  );
}
window.LoginScreen = LoginScreen;
