if (!window.CRMData) {
const customers = [
  { id: 'c1', name: 'Acme Holdings', segment: 'Commercial', rm: 'J. Tran', status: 'Active', balance: 4820340, lastContact: 'Jul 8, 2026' },
  { id: 'c2', name: 'Nolan & Reyes LLP', segment: 'Private', rm: 'M. Alvarez', status: 'Active', balance: 1240500, lastContact: 'Jul 10, 2026' },
  { id: 'c3', name: 'Green Harbor Foods', segment: 'Commercial', rm: 'J. Tran', status: 'Pending review', balance: 892100, lastContact: 'Jul 3, 2026' },
  { id: 'c4', name: 'Priya Shah', segment: 'Private', rm: 'S. Okafor', status: 'Active', balance: 318420, lastContact: 'Jun 29, 2026' },
  { id: 'c5', name: 'Delta Freight Co.', segment: 'Commercial', rm: 'M. Alvarez', status: 'At risk', balance: 2103900, lastContact: 'Jun 22, 2026' },
];

const deals = [
  { id: 'd1', name: 'Acme Holdings — Term loan renewal', stage: 'Proposal', value: 1200000, owner: 'J. Tran', close: 'Jul 30, 2026' },
  { id: 'd2', name: 'Green Harbor — Working capital line', stage: 'Discovery', value: 450000, owner: 'J. Tran', close: 'Aug 12, 2026' },
  { id: 'd3', name: 'Nolan & Reyes — Wealth management', stage: 'Negotiation', value: 780000, owner: 'M. Alvarez', close: 'Jul 18, 2026' },
  { id: 'd4', name: 'Delta Freight — Equipment financing', stage: 'Discovery', value: 2100000, owner: 'M. Alvarez', close: 'Sep 1, 2026' },
  { id: 'd5', name: 'Priya Shah — Mortgage refinance', stage: 'Closed won', value: 620000, owner: 'S. Okafor', close: 'Jun 30, 2026' },
];

const activity = [
  { id: 'a1', text: 'Statement sent to Acme Holdings', time: '2h ago', tone: 'success' },
  { id: 'a2', text: 'Deal "Wealth management" moved to Negotiation', time: '5h ago', tone: 'info' },
  { id: 'a3', text: 'Green Harbor Foods flagged for review', time: 'Yesterday', tone: 'warning' },
  { id: 'a4', text: 'Payment failed for Delta Freight Co.', time: 'Jul 9, 2026', tone: 'danger' },
];

function formatCurrency(n) {
  return '$' + n.toLocaleString('en-US', { maximumFractionDigits: 0 });
}

window.CRMData = { customers, deals, activity, formatCurrency };
}
