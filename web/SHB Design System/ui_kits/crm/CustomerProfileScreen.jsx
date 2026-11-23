function CustomerProfileScreen({ customer, onBack }) {
  const { Card, Badge, Tabs, Button } = window.SHBDesignSystem_1dd17a;
  const { deals, formatCurrency } = window.CRMData;
  const [tab, setTab] = React.useState('overview');
  const customerDeals = deals.filter((d) => d.name.startsWith(customer.name.split(' ')[0]));

  return (
    <div style={{ padding: 28, fontFamily: 'var(--font-body)', display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div>
        <button onClick={onBack} style={{ background: 'none', border: 'none', color: 'var(--text-link)', cursor: 'pointer', fontSize: 'var(--text-sm)', padding: 0, marginBottom: 12 }}>
          ← Back to dashboard
        </button>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-3xl)', fontWeight: 700 }}>{customer.name}</div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginTop: 4 }}>{customer.segment} · RM {customer.rm} · Last contact {customer.lastContact}</div>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <Button variant="secondary">Log activity</Button>
            <Button variant="primary">Send statement</Button>
          </div>
        </div>
      </div>

      <Tabs tabs={[{ value: 'overview', label: 'Overview' }, { value: 'deals', label: 'Deals' }, { value: 'documents', label: 'Documents' }]} value={tab} onChange={setTab} />

      {tab === 'overview' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 16 }}>
          <Card>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Total balance</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-2xl)', fontWeight: 700, marginTop: 6 }}>{formatCurrency(customer.balance)}</div>
          </Card>
          <Card>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Status</div>
            <div style={{ marginTop: 8 }}><Badge tone={customer.status === 'Active' ? 'success' : customer.status === 'At risk' ? 'danger' : 'warning'}>{customer.status}</Badge></div>
          </Card>
          <Card>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Relationship manager</div>
            <div style={{ fontSize: 'var(--text-base)', fontWeight: 600, marginTop: 6 }}>{customer.rm}</div>
          </Card>
        </div>
      )}

      {tab === 'deals' && (
        <Card padding="0">
          {customerDeals.length === 0 && <div style={{ padding: 20, color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>No deals yet for this customer.</div>}
          {customerDeals.map((d) => (
            <div key={d.id} style={{ padding: '14px 20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ fontSize: 'var(--text-sm)' }}>{d.name}</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)' }}>{formatCurrency(d.value)}</span>
            </div>
          ))}
        </Card>
      )}

      {tab === 'documents' && (
        <Card><div style={{ color: 'var(--text-tertiary)', fontSize: 'var(--text-sm)' }}>No documents on file yet.</div></Card>
      )}
    </div>
  );
}
window.CustomerProfileScreen = CustomerProfileScreen;
