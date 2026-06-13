import { trades, forwardTest } from '../api.js';

export async function renderDashboard(container) {
  try {
    const [portfolio, fwd] = await Promise.all([
      trades.summary(),
      forwardTest.summary()
    ]);

    const formatCurr = (v) => '₹' + Number(v).toLocaleString('en-IN');
    
    let html = `
      <div class="grid-3">
        <div class="card">
          <div class="stat-label">Trading Mode</div>
          <div class="stat-value" style="color: ${portfolio.trading_mode === 'live' ? 'var(--danger-color)' : 'var(--primary-color)'}">
            ${portfolio.trading_mode.toUpperCase()}
          </div>
        </div>
        
        <div class="card">
          <div class="stat-label">Realized P&L (${portfolio.trading_mode})</div>
          <div class="stat-value ${portfolio.realized_pnl >= 0 ? 'positive' : 'negative'}">
            ${formatCurr(portfolio.realized_pnl)}
          </div>
        </div>
        
        <div class="card">
          <div class="stat-label">Win Rate</div>
          <div class="stat-value">${portfolio.win_rate}%</div>
        </div>
      </div>

      <h3 class="mb-4 mt-4">Active Trades Overview</h3>
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <div>Open Trades: <strong>${portfolio.open_trades}</strong></div>
          <a href="/trades" class="btn btn-primary" onclick="event.preventDefault(); window.history.pushState({}, '', '/trades'); window.dispatchEvent(new Event('popstate'));">View All Trades</a>
        </div>
      </div>
      
      <h3 class="mb-4 mt-4">Forward Testing Progress</h3>
      <div class="grid-3">
        <div class="card">
          <div class="stat-label">Days Logged</div>
          <div class="stat-value">${fwd.days_logged}</div>
        </div>
        <div class="card">
          <div class="stat-label">Cumulative Paper P&L</div>
          <div class="stat-value ${fwd.cumulative_pnl >= 0 ? 'positive' : 'negative'}">
            ${formatCurr(fwd.cumulative_pnl)}
          </div>
        </div>
        <div class="card">
          <div class="stat-label">Forward Win Rate</div>
          <div class="stat-value">${fwd.win_rate}%</div>
        </div>
      </div>
    `;
    
    container.innerHTML = html;
  } catch (err) {
    container.innerHTML = `<div class="card negative">Failed to load dashboard: ${err.message}</div>`;
  }
}
