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
            <select class="form-control" disabled>
              <option>VCP (Volatility Contraction)</option>
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
                <th>Period</th>
                <th>Return</th>
                <th>Win Rate</th>
                <th>Drawdown</th>
                <th>Trades</th>
              </tr>
            </thead>
            <tbody id="bt-results">
              <tr><td colspan="6" style="text-align:center;">Loading...</td></tr>
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
        tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;">No backtests run yet.</td></tr>';
        return;
      }

      tbody.innerHTML = data.map(r => `
        <tr>
          <td>${new Date(r.run_date).toLocaleDateString()}</td>
          <td style="font-size:0.875rem">${r.start_date} → ${r.end_date}</td>
          <td class="mono ${r.total_return_pct >= 0 ? 'positive' : 'negative'}">${r.total_return_pct}%</td>
          <td class="mono">${r.win_rate}%</td>
          <td class="mono negative">-${r.max_drawdown}%</td>
          <td class="mono">${r.total_trades}</td>
        </tr>
      `).join('');
    } catch (e) {
      console.error(e);
    }
  };

  await loadResults();

  document.getElementById('bt-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = document.getElementById('btn-run-bt');
    const prog = document.getElementById('bt-prog');
    
    try {
      await backtest.run({
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
