import { forwardTest, trades } from '../api.js';

export async function renderForwardTest(container) {
  container.innerHTML = `
    <div class="flex justify-between items-center mb-4">
      <h3>Forward Test Daily Logs</h3>
      <button id="btn-update-fwd" class="btn btn-outline">Trigger End-of-Day Update</button>
    </div>
    
    <div class="card mb-4" style="background: rgba(59, 130, 246, 0.1); border-color: rgba(59, 130, 246, 0.3);">
      <p style="margin:0; font-size: 0.9rem; color: var(--text-muted);">
        <strong style="color:var(--primary-color)">What is this?</strong> Forward testing logs the daily scanner signals and tracks them 
        using live market data as if you had taken the trades, without risking real capital. 
        Analyze these logs for 4-8 weeks before enabling LIVE mode.
      </p>
    </div>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Date</th>
            <th>Market Regime</th>
            <th>Signals Found</th>
            <th>Paper Trades</th>
            <th>Closed Today</th>
            <th>Daily P&L</th>
            <th>Cumulative P&L</th>
          </tr>
        </thead>
        <tbody id="fwd-body">
          <tr><td colspan="7" style="text-align:center;">Loading...</td></tr>
        </tbody>
      </table>
    </div>

    <div class="mt-8 mb-4">
      <h3>Bot Executions (Auto-Trades)</h3>
      <p style="font-size: 0.9rem; color: var(--text-muted);">
        These are the trades autonomously executed and managed by the Auto-Trading Bot based on your settings.
      </p>
    </div>
    
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Strategy</th>
            <th>Mode</th>
            <th>Status</th>
            <th>Entry</th>
            <th>Current / Exit</th>
            <th>P&L</th>
          </tr>
        </thead>
        <tbody id="bot-trades-body">
          <tr><td colspan="7" style="text-align:center;">Loading...</td></tr>
        </tbody>
      </table>
    </div>
  `;

  const loadData = async () => {
    try {
      const logs = await forwardTest.logs();
      const tbody = document.getElementById('fwd-body');
      
      if (!logs.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No forward test data yet. Ensure daily scan is running.</td></tr>';
        return;
      }

      tbody.innerHTML = logs.map(l => `
        <tr>
          <td><strong>${l.date}</strong></td>
          <td><span class="badge ${l.regime === 'BULL' ? 'badge-success' : (l.regime === 'PANIC' ? 'badge-danger' : 'badge-warning')}">${l.regime}</span></td>
          <td class="mono">${l.signals_count}</td>
          <td class="mono">${l.trades_entered}</td>
          <td class="mono">${l.trades_closed}</td>
          <td class="mono ${l.daily_pnl > 0 ? 'positive' : (l.daily_pnl < 0 ? 'negative' : '')}">₹${l.daily_pnl.toFixed(2)}</td>
          <td class="mono ${l.cumulative_pnl >= 0 ? 'positive' : 'negative'}"><strong>₹${l.cumulative_pnl.toFixed(2)}</strong></td>
        </tr>
      `).join('');
    } catch (err) {
      document.getElementById('fwd-body').innerHTML = `<tr><td colspan="7" class="negative">Error: ${err.message}</td></tr>`;
    }

    try {
      // Fetch all trades, filter out SANDBOX trades
      const allTrades = await trades.list();
      const botTrades = allTrades.filter(t => t.strategy !== 'SANDBOX');
      const tbody = document.getElementById('bot-trades-body');

      if (!botTrades.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No automated trades executed yet.</td></tr>';
        return;
      }

      tbody.innerHTML = botTrades.map(t => {
        const pnlStr = t.pnl !== null 
          ? `<span class="${t.pnl >= 0 ? 'positive' : 'negative'}">₹${t.pnl} (${t.pnl_pct}%)</span>` 
          : `<span class="text-muted">Open</span>`;
        
        return `
          <tr>
            <td><strong>${t.symbol}</strong></td>
            <td><span class="badge" style="background:#e0e7ff; color:#4361ee;">${t.strategy}</span></td>
            <td><span class="badge ${t.mode === 'live' ? 'badge-danger' : 'badge-warning'}">${t.mode.toUpperCase()}</span></td>
            <td>
              <span class="badge ${t.status === 'open' ? 'badge-success' : 'badge-neutral'}">${t.status}</span>
            </td>
            <td class="mono">₹${t.entry_price}</td>
            <td class="mono">${t.exit_price ? '₹'+t.exit_price : '—'}</td>
            <td>${pnlStr}</td>
          </tr>
        `;
      }).join('');
    } catch (err) {
      document.getElementById('bot-trades-body').innerHTML = `<tr><td colspan="7" class="negative">Error loading trades: ${err.message}</td></tr>`;
    }
  };

  await loadData();

  document.getElementById('btn-update-fwd').addEventListener('click', async (e) => {
    const btn = e.target;
    btn.disabled = true;
    btn.textContent = 'Updating...';
    try {
      const res = await forwardTest.update();
      alert(`Update complete. Closed ${res.closed} trades, P&L today: ₹${res.pnl_today}`);
      await loadData();
    } catch (err) {
      alert(err.message);
    } finally {
      btn.disabled = false;
      btn.textContent = 'Trigger End-of-Day Update';
    }
  });
}
