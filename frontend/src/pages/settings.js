import { settings } from '../api.js';

export async function renderSettings(container) {
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
          </div>
          <button type="submit" class="btn btn-primary mt-4">Save Parameters</button>
        </form>
      </div>

      <!-- Live Mode Guard -->
      <div class="card" style="border-color: var(--danger-color);">
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
    const data = await settings.get();
    document.getElementById('capital').value = data.capital;
    document.getElementById('risk_pct').value = data.risk_pct;
    document.getElementById('max_sl_pct').value = data.max_sl_pct;
    document.getElementById('min_quality').value = data.min_quality;
    
    if (data.trading_mode === 'live') {
      const btn = document.getElementById('btn-live');
      btn.textContent = 'LIVE MODE ACTIVE';
      btn.disabled = true;
      btn.style.opacity = '0.5';
    }
  } catch (err) {
    console.error("Failed to load settings:", err);
  }

  // Handle standard settings save
  document.getElementById('settings-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
      await settings.update({
        capital: parseFloat(document.getElementById('capital').value),
        risk_pct: parseFloat(document.getElementById('risk_pct').value),
        max_sl_pct: parseFloat(document.getElementById('max_sl_pct').value),
        min_quality: parseInt(document.getElementById('min_quality').value, 10),
      });
      alert('Parameters saved successfully!');
    } catch (err) {
      alert('Error saving parameters: ' + err.message);
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
