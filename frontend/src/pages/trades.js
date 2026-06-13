import { trades } from '../api.js';

export async function renderTrades(container) {
  container.innerHTML = `
    <div class="flex items-center gap-4 mb-4">
      <select id="filter-mode" class="form-control" style="width: 200px; display:inline-block; margin-bottom:0;">
        <option value="">All Modes</option>
        <option value="paper">Paper</option>
        <option value="forward">Forward Test</option>
        <option value="live">LIVE</option>
      </select>
      
      <select id="filter-status" class="form-control" style="width: 200px; display:inline-block; margin-bottom:0;">
        <option value="">All Statuses</option>
        <option value="open">Open</option>
        <option value="closed">Closed</option>
      </select>
    </div>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Mode</th>
            <th>Status</th>
            <th>Entry</th>
            <th>Exit / LTP</th>
            <th>P&L</th>
            <th>Action</th>
          </tr>
        </thead>
        <tbody id="trades-body">
          <tr><td colspan="7" style="text-align:center;">Loading...</td></tr>
        </tbody>
      </table>
    </div>
  `;

  const loadData = async () => {
    try {
      const mode = document.getElementById('filter-mode').value;
      const status = document.getElementById('filter-status').value;
      
      const data = await trades.list(mode, status);
      const tbody = document.getElementById('trades-body');
      
      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 2rem;">No trades found.</td></tr>';
        return;
      }

      tbody.innerHTML = data.map(t => {
        const isClosed = t.status === 'closed';
        const pnlStr = isClosed 
          ? `<span class="mono ${t.pnl >= 0 ? 'positive' : 'negative'}">₹${t.pnl.toFixed(2)} (${t.pnl_pct.toFixed(2)}%)</span>`
          : '<span class="text-muted">—</span>';
          
        let modeBadge = 'badge-info';
        if (t.mode === 'live') modeBadge = 'badge-danger';
        if (t.mode === 'forward') modeBadge = 'badge-warning';

        return `
          <tr>
            <td><strong>${t.symbol}</strong><br><span style="font-size:0.75rem" class="text-muted">${new Date(t.entry_date).toLocaleDateString()}</span></td>
            <td><span class="badge ${modeBadge}">${t.mode.toUpperCase()}</span></td>
            <td><span class="badge ${isClosed ? '' : 'badge-success'}">${t.status.toUpperCase()}</span></td>
            <td>
              <div class="mono">₹${t.entry_price.toFixed(2)}</div>
              <div class="text-muted" style="font-size:0.75rem">Qty: ${t.quantity}</div>
            </td>
            <td>
              ${isClosed ? `<div class="mono">₹${t.exit_price.toFixed(2)}</div><div class="text-muted" style="font-size:0.75rem">${t.exit_reason}</div>` : '<span class="text-muted">Open</span>'}
            </td>
            <td>${pnlStr}</td>
            <td>
              ${!isClosed ? `<button class="btn btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="window.closeTrade(${t.id}, ${t.target || t.entry_price * 1.1})">Close</button>` : ''}
            </td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      document.getElementById('trades-body').innerHTML = `<tr><td colspan="7" class="negative">Error: ${err.message}</td></tr>`;
    }
  };

  await loadData();

  document.getElementById('filter-mode').addEventListener('change', loadData);
  document.getElementById('filter-status').addEventListener('change', loadData);

  window.closeTrade = async (id, fallbackPrice) => {
    const priceStr = prompt("Enter exit price:", fallbackPrice.toFixed(2));
    if (!priceStr) return;
    const exitPrice = parseFloat(priceStr);
    if (isNaN(exitPrice)) return alert("Invalid price");

    try {
      await trades.close(id, { exit_price: exitPrice, exit_reason: "MANUAL" });
      loadData();
    } catch (e) {
      alert("Failed to close trade: " + e.message);
    }
  };
}
