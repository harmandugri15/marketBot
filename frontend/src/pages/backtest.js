import { backtest, createSSE } from '../api.js';

let sse = null;

export async function renderBacktest(container) {
  container.innerHTML = `
    <div class="grid-3">
      <div class="card" style="grid-column: span 1;">
        <h3 class="mb-4">New Backtest</h3>
        <form id="bt-form">
          <div class="form-group">
            <label class="form-label">Strategy</label>
            <select id="bt-strat" class="form-control">
              <option value="VCP">VCP (Volatility Contraction)</option>
              <option value="HARMAN1_PULLBACK">Swing Pullback (HARMAN1_PULLBACK)</option>
              <option value="GOOGLE_SWING">Google Swing (EMA/RSI/ATR)</option>
              <option value="VWAP_RUNNER">Intraday VWAP Bounce (VWAP_RUNNER)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Start Date</label>
            <input type="date" id="bt-start" class="form-control" value="2023-01-01" required />
          </div>
          <div class="form-group">
            <label class="form-label">End Date</label>
            <input type="date" id="bt-end" class="form-control" value="2024-01-01" required />
          </div>
          <div class="form-group">
            <label class="form-label">Capital (₹)</label>
            <input type="number" id="bt-cap" class="form-control" value="200000" min="10000" required />
          </div>
          <button type="submit" id="btn-run-bt" class="btn btn-primary" style="width:100%">Run Simulation</button>
        </form>

        <div id="bt-prog" class="mt-4" style="display:none;">
          <div class="flex justify-between mb-2">
            <span class="stat-label">Progress</span>
            <span id="bt-pct" class="mono">0%</span>
          </div>
          <div style="background:var(--border-color); height:6px; border-radius:3px; overflow:hidden;">
            <div id="bt-bar" style="height:100%; width:0%; background:var(--primary-color); transition:width 0.3s;"></div>
          </div>
          <div id="bt-sym" class="text-muted mt-2" style="font-size:0.75rem;">Initializing...</div>
        </div>
      </div>

      <div class="card" style="grid-column: span 2;">
        <h3 class="mb-4">Recent Results</h3>
        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Run Date</th>
                <th>Strategy</th>
                <th>Period</th>
                <th>Return</th>
                <th>Win Rate</th>
                <th>Drawdown</th>
                <th>Trades</th>
              </tr>
            </thead>
            <tbody id="bt-results">
              <tr><td colspan="7" style="text-align:center;">Loading...</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  `;

  const loadResults = async () => {
    try {
      const data = await backtest.results();
      const tbody = document.getElementById('bt-results');
      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;">No backtests run yet.</td></tr>';
        return;
      }

      tbody.innerHTML = data.map(r => `
        <tr class="clickable-row" data-id="${r.id}" style="cursor:pointer;">
          <td>${new Date(r.run_date).toLocaleDateString()}</td>
          <td><span class="badge" style="background:var(--border-color); font-size:0.75rem;">${r.strategy}</span></td>
          <td style="font-size:0.875rem">${r.start_date} → ${r.end_date}</td>
          <td class="mono ${r.total_return_pct >= 0 ? 'positive' : 'negative'}">${r.total_return_pct}%</td>
          <td class="mono">${r.win_rate}%</td>
          <td class="mono negative">-${r.max_drawdown}%</td>
          <td class="mono">${r.total_trades}</td>
        </tr>
      `).join('');

      document.querySelectorAll('.clickable-row').forEach(row => {
        row.addEventListener('click', async () => {
          const id = row.getAttribute('data-id');
          await showBacktestDetails(id);
        });
      });
    } catch (e) {
      console.error(e);
    }
  };

  async function showBacktestDetails(id) {
    try {
      const r = await backtest.detail(id);
      
      let modal = document.getElementById('bt-detail-modal');
      if (!modal) {
        modal = document.createElement('div');
        modal.id = 'bt-detail-modal';
        document.body.appendChild(modal);
      }
      
      modal.style.position = 'fixed';
      modal.style.top = '0';
      modal.style.left = '0';
      modal.style.width = '100vw';
      modal.style.height = '100vh';
      modal.style.background = 'rgba(11, 15, 25, 0.85)';
      modal.style.backdropFilter = 'blur(8px)';
      modal.style.zIndex = '1000';
      modal.style.display = 'flex';
      modal.style.justifyContent = 'center';
      modal.style.alignItems = 'center';
      modal.style.padding = '2rem';
      
      const tradesHtml = (r.trade_log || []).map((t, idx) => {
        const pnl = t.pnl || 0;
        const pct = t.pnl_pct || 0;
        const entryPrice = t.entry || t.entry_price || 0;
        const exitPrice = t.exit || t.exit_price || 0;
        const qty = t.qty || t.shares || 0;
        
        return `
          <tr>
            <td style="color:var(--text-muted)">${idx + 1}</td>
            <td style="font-weight:600;">${t.symbol}</td>
            <td><span class="badge" style="background:var(--border-color);">${t.strategy || '—'}</span></td>
            <td>${t.entry_date || '—'}</td>
            <td>${t.exit_date || '—'}</td>
            <td class="mono">₹${entryPrice.toLocaleString('en-IN')}</td>
            <td class="mono">${exitPrice ? `₹${exitPrice.toLocaleString('en-IN')}` : '—'}</td>
            <td class="mono">${qty}</td>
            <td class="mono ${pnl >= 0 ? 'positive' : 'negative'}">${pnl >= 0 ? '+' : ''}₹${Math.abs(pnl).toLocaleString('en-IN')}</td>
            <td class="mono ${pct >= 0 ? 'positive' : 'negative'}">${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%</td>
            <td><span class="badge" style="background:rgba(255,255,255,0.05); color:var(--text-muted);">${t.exit_reason || '—'}</span></td>
          </tr>
        `;
      }).join('');

      modal.innerHTML = `
        <div class="card" style="width: 90%; max-width: 1200px; max-height: 85vh; overflow-y: auto; display: flex; flex-direction: column; gap: 1.5rem; position: relative; border: 1px solid var(--border-color); background: var(--bg-color);">
          <button id="close-modal-btn" style="position: absolute; top: 1.5rem; right: 1.5rem; background: transparent; color: var(--text-muted); font-size: 1.5rem; width: 32px; height: 32px; border-radius: 50%; display: flex; justify-content: center; align-items: center; border: 1px solid var(--border-color); cursor: pointer;">
            &times;
          </button>
          
          <div>
            <h2>Backtest Details</h2>
            <p class="text-muted" style="font-size: 0.875rem;">Strategy: <strong>${r.strategy}</strong> | Tested Period: <strong>${r.start_date} → ${r.end_date}</strong></p>
          </div>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem;">
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Total Return</div>
              <div class="stat-value ${r.total_return_pct >= 0 ? 'positive' : 'negative'}">${r.total_return_pct >= 0 ? '+' : ''}${r.total_return_pct}%</div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Win Rate</div>
              <div class="stat-value">${r.win_rate}%</div>
              <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">${r.winning_trades}W / ${r.losing_trades}L</div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Profit Factor</div>
              <div class="stat-value">${r.profit_factor}</div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Max Drawdown</div>
              <div class="stat-value negative">-${r.max_drawdown}%</div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Avg Win / Loss</div>
              <div style="font-size: 1.1rem; font-weight: 700; margin-top: 0.5rem; font-family: var(--font-mono);">
                <span class="positive">+${r.avg_gain_pct}%</span> / <span class="negative">-${r.avg_loss_pct}%</span>
              </div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Ending Capital</div>
              <div class="stat-value" style="font-size: 1.5rem; margin-top: 0.75rem;">₹${r.final_capital.toLocaleString('en-IN')}</div>
            </div>
          </div>

          <div>
            <h3 class="mb-3">Executed Trades (${r.total_trades} total)</h3>
            <div class="table-wrapper" style="max-height: 400px; overflow-y: auto;">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Symbol</th>
                    <th>Strategy</th>
                    <th>Entry Date</th>
                    <th>Exit Date</th>
                    <th>Entry Price</th>
                    <th>Exit Price</th>
                    <th>Qty</th>
                    <th>PnL</th>
                    <th>Gain %</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  ${tradesHtml || '<tr><td colspan="11" style="text-align:center;">No trades were executed.</td></tr>'}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;
      
      document.getElementById('close-modal-btn').onclick = () => {
        modal.remove();
      };
      
      modal.onclick = (e) => {
        if (e.target === modal) {
          modal.remove();
        }
      };
    } catch (err) {
      alert('Failed to load backtest details: ' + err.message);
    }
  }

  await loadResults();

  document.getElementById('bt-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-run-bt');
    const prog = document.getElementById('bt-prog');
    
    try {
      await backtest.run({
        strategy: document.getElementById('bt-strat').value,
        start_date: document.getElementById('bt-start').value,
        end_date: document.getElementById('bt-end').value,
        capital: parseFloat(document.getElementById('bt-cap').value)
      });

      btn.disabled = true;
      prog.style.display = 'block';

      if (sse) sse.close();
      sse = createSSE('/backtest/progress/stream', (data) => {
        if (data.total > 0) {
          const pct = Math.round((data.current / data.total) * 100);
          document.getElementById('bt-pct').textContent = `${pct}%`;

          document.getElementById('bt-bar').style.width = `${pct}%`;
          document.getElementById('bt-sym').textContent = `Testing ${data.symbol}...`;
        }
        if (data.done || data.error) {
          sse.close();
          btn.disabled = false;
          prog.style.display = 'none';
          if (data.error) alert('Error: ' + data.error);
          else loadResults();
        }
      });
    } catch (err) {
      if (err.message.includes('already running')) {
        alert('A backtest is already in progress.');
      } else {
        alert(err.message);
      }
    }
  });
}
