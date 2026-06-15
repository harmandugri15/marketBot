import { settings } from '../api.js';

export async function renderSettings(container) {
  let data = {};
  try {
    data = await settings.get();
  } catch (e) {
    console.error("Failed to load settings:", e);
  }

  container.innerHTML = `
    <div class="grid-3">
      <!-- Strategy Settings -->
      <div class="card" style="grid-column: span 2;">
        <h3 class="mb-4">Trading Parameters</h3>
        <form id="settings-form">
          <div class="grid-3" style="grid-template-columns: 1fr 1fr;">
            <div class="form-group">
              <label class="form-label">Capital Allocated (₹)</label>
              <input type="number" id="capital" class="form-control" required />
            </div>
            <div class="form-group">
              <label class="form-label">Risk per Trade (%)</label>
              <input type="number" step="0.1" id="risk_pct" class="form-control" required />
            </div>
            <div class="form-group">
              <label class="form-label">Max Stop Loss (%)</label>
              <input type="number" step="0.1" id="max_sl_pct" class="form-control" required />
            </div>
            <div class="form-group">
              <label class="form-label">Min Setup Quality (0-100)</label>
              <input type="number" id="min_quality" class="form-control" required />
            </div>
            <div class="form-group">
              <label class="form-label">Trading Mode</label>
              <select id="trading_mode" class="form-control" required>
                <option value="paper">Paper Trading (Simulated Fills)</option>
                <option value="forward">Forward Testing (Logs only, no real money)</option>
                <option value="live" id="opt-live" disabled>Live Trading (Active)</option>
              </select>
            </div>
          </div>
          <button type="submit" class="btn btn-primary mt-4">Save Parameters</button>
        </form>
      </div>
 
      <!-- Auto Trading Bot -->
      <div class="card" style="grid-column: span 3;">
        <h2 class="card-title">Automated Trading Bot</h2>
        <p class="text-muted" style="margin-bottom:1rem;">Allow MarketBot to autonomously scan the market, calculate position sizing, and execute trades according to your preferred strategy. The bot will automatically exit positions when targets or stop-losses are hit.</p>
        <div class="grid-2">
          <div class="form-group">
            <label class="form-label">Enable Auto-Trading</label>
            <select id="auto-enabled" class="form-control">
              <option value="false" ${!data.auto_trading_enabled ? 'selected' : ''}>Disabled</option>
              <option value="true" ${data.auto_trading_enabled ? 'selected' : ''}>Enabled (Active)</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Bot Strategy</label>
            <select id="auto-strategy" class="form-control">
              <option value="VCP" ${data.auto_trading_strategy === 'VCP' ? 'selected' : ''}>Volatility Contraction (VCP)</option>
              <option value="HARMAN1_PULLBACK" ${data.auto_trading_strategy === 'HARMAN1_PULLBACK' ? 'selected' : ''}>Harman Pullback</option>
              <option value="GOOGLE_SWING" ${data.auto_trading_strategy === 'GOOGLE_SWING' ? 'selected' : ''}>Google Swing (EMA/RSI/ATR)</option>
            </select>
          </div>
        </div>
        <button id="save-auto-btn" class="btn btn-primary" style="margin-top: 1rem;">Save Bot Settings</button>
      </div>

      <!-- Live Mode Guard -->
      <div class="card" style="grid-column: span 3; border-color: var(--danger-color);">
        <h3 class="mb-4" style="color: var(--danger-color)">LIVE Execution</h3>
        <p style="font-size: 0.875rem; color: var(--text-muted); margin-bottom: 1.5rem;">
          To switch from paper/forward testing to real money execution, you must provide valid Groww API credentials. 
          The system will verify the connection before unlocking live mode.
        </p>
        
        <form id="live-form">
          <div class="form-group">
            <label class="form-label">Groww API Key</label>
            <input type="password" id="g_api" class="form-control" />
          </div>
          <div class="form-group">
            <label class="form-label">Groww Secret</label>
            <input type="password" id="g_sec" class="form-control" />
          </div>
          <div class="form-group">
            <label class="form-label">Groww Client ID</label>
            <input type="text" id="g_cid" class="form-control" />
          </div>
          <div class="form-group" style="display:flex; align-items:center; gap: 0.5rem; margin-top: 1rem;">
            <input type="checkbox" id="g_confirm" />
            <label for="g_confirm" style="font-size: 0.875rem;">I understand that real money will be at risk.</label>
          </div>
          
          <button type="submit" id="btn-live" class="btn" style="width: 100%; background: var(--danger-color); color: white; margin-top: 1rem;">
            Authenticate & Enable LIVE
          </button>
        </form>
      </div>
    </div>
  `;
 
  // Load current settings
  try {
    document.getElementById('capital').value = data.capital || 200000;
    document.getElementById('risk_pct').value = data.risk_pct || 1.0;
    document.getElementById('max_sl_pct').value = data.max_sl_pct || 12.0;
    document.getElementById('min_quality').value = data.min_quality || 85;
    
    const optLive = document.getElementById('opt-live');
    if (data.trading_mode === 'live') {
      optLive.disabled = false;
      const btn = document.getElementById('btn-live');
      btn.textContent = 'LIVE MODE ACTIVE';
      btn.disabled = true;
      btn.style.opacity = '0.5';
    }
    document.getElementById('trading_mode').value = data.trading_mode;
  } catch (err) {
    console.error("Failed to load settings:", err);
  }
 
  // Handle standard settings save
  document.getElementById('settings-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await settings.update({
        trading_mode: document.getElementById('trading_mode').value,
        capital: parseFloat(document.getElementById('capital').value),
        risk_pct: parseFloat(document.getElementById('risk_pct').value),
        max_sl_pct: parseFloat(document.getElementById('max_sl_pct').value),
        min_quality: parseInt(document.getElementById('min_quality').value, 10),
      });
      alert('Parameters saved successfully! Reloading...');
      window.location.reload();
    } catch (err) {
      alert('Error saving parameters: ' + err.message);
    }
  });

  document.getElementById('save-auto-btn').addEventListener('click', async () => {
    const isEnabled = document.getElementById('auto-enabled').value === 'true';
    const strat = document.getElementById('auto-strategy').value;

    try {
      await settings.update({
        auto_trading_enabled: isEnabled,
        auto_trading_strategy: strat
      });
      alert('Auto-Trading Bot settings updated!');
    } catch (e) {
      alert('Error updating bot settings: ' + e.message);
    }
  });

  // Handle LIVE mode unlock
  document.getElementById('live-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!document.getElementById('g_confirm').checked) {
      return alert('You must check the confirmation box.');
    }

    const btn = document.getElementById('btn-live');
    btn.textContent = 'Verifying with Groww...';
    btn.disabled = true;

    try {
      await settings.enableLive({
        confirm: true,
        groww_api_key: document.getElementById('g_api').value,
        groww_secret_key: document.getElementById('g_sec').value,
        groww_client_id: document.getElementById('g_cid').value
      });
      alert('LIVE mode enabled successfully! Reloading...');
      window.location.reload();
    } catch (err) {
      alert('Failed to enable LIVE mode: ' + err.message);
      btn.textContent = 'Authenticate & Enable LIVE';
      btn.disabled = false;
    }
  });
}
