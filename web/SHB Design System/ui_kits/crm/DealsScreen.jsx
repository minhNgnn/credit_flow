const stages = ['Discovery', 'Proposal', 'Negotiation', 'Closed won'];
const stageTone = { 'Discovery': 'info', 'Proposal': 'warning', 'Negotiation': 'accent', 'Closed won': 'success' };

function DealsScreen() {
  const { Card, Badge } = window.SHBDesignSystem_1dd17a;
  const { deals, formatCurrency } = window.CRMData;
  return (
    <div style={{ padding: 28, fontFamily: 'var(--font-body)' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16, alignItems: 'start' }}>
        {stages.map((stage) => {
          const items = deals.filter((d) => d.stage === stage);
          const total = items.reduce((s, d) => s + d.value, 0);
          return (
            <div key={stage} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{stage}</span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', fontFamily: 'var(--font-mono)' }}>{formatCurrency(total)}</span>
              </div>
              {items.map((d) => (
                <Card key={d.id} padding="var(--space-4)">
                  <div style={{ fontSize: 'var(--text-sm)', fontWeight: 500, marginBottom: 8 }}>{d.name}</div>
                  <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-base)', fontWeight: 600, color: 'var(--brand-primary)' }}>{formatCurrency(d.value)}</div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 10 }}>
                    <Badge tone={stageTone[d.stage]}>{d.owner}</Badge>
                    <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)' }}>{d.close}</span>
                  </div>
                </Card>
              ))}
              {items.length === 0 && (
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-tertiary)', padding: '8px 0' }}>No deals in this stage.</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
window.DealsScreen = DealsScreen;
