const statusTone = { 'Active': 'success', 'Pending review': 'warning', 'At risk': 'danger' };

function DashboardScreen({ onOpenCustomer }) {
  const { Card, Badge } = window.SHBDesignSystem_1dd17a;
  const { customers, deals, activity, formatCurrency } = window.CRMData;
  const totalAUM = customers.reduce((s, c) => s + c.balance, 0);
  const openDeals = deals.filter(d => d.stage !== 'Closed won');
  const pipelineValue = openDeals.reduce((s, d) => s + d.value, 0);

  return (
    <div style={{ padding: 28, display: 'flex', flexDirection: 'column', gap: 20, fontFamily: 'var(--font-body)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
        <Card>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Assets under management</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-3xl)', fontWeight: 700, marginTop: 6 }}>{formatCurrency(totalAUM)}</div>
        </Card>
        <Card>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Open pipeline value</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-3xl)', fontWeight: 700, marginTop: 6, color: 'var(--brand-primary)' }}>{formatCurrency(pipelineValue)}</div>
        </Card>
        <Card>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>Customers</div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 'var(--text-3xl)', fontWeight: 700, marginTop: 6 }}>{customers.length}</div>
        </Card>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 16, alignItems: 'start' }}>
        <Card padding="0" style={{ overflow: 'hidden' }}>
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', fontWeight: 600 }}>Customers</div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 'var(--text-sm)' }}>
            <thead>
              <tr style={{ textAlign: 'left', color: 'var(--text-tertiary)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                <th style={{ padding: '10px 20px' }}>Name</th>
                <th style={{ padding: '10px 12px' }}>Segment</th>
                <th style={{ padding: '10px 12px' }}>Status</th>
                <th style={{ padding: '10px 20px', textAlign: 'right' }}>Balance</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.id} onClick={() => onOpenCustomer && onOpenCustomer(c)} style={{ borderTop: '1px solid var(--border-subtle)', cursor: 'pointer' }}>
                  <td style={{ padding: '12px 20px', fontWeight: 500 }}>{c.name}</td>
                  <td style={{ padding: '12px 12px', color: 'var(--text-secondary)' }}>{c.segment}</td>
                  <td style={{ padding: '12px 12px' }}><Badge tone={statusTone[c.status] || 'neutral'}>{c.status}</Badge></td>
                  <td style={{ padding: '12px 20px', textAlign: 'right', fontFamily: 'var(--font-mono)' }}>{formatCurrency(c.balance)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card padding="0">
          <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border-subtle)', fontWeight: 600 }}>Recent activity</div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            {activity.map((a) => (
              <div key={a.id} style={{ padding: '14px 20px', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexDirection: 'column', gap: 4 }}>
                <div style={{ fontSize: 'var(--text-sm)' }}>{a.text}</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>{a.time}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
window.DashboardScreen = DashboardScreen;
