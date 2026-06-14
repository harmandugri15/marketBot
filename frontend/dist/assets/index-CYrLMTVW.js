(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const t of document.querySelectorAll('link[rel="modulepreload"]'))n(t);new MutationObserver(t=>{for(const o of t)if(o.type==="childList")for(const s of o.addedNodes)s.tagName==="LINK"&&s.rel==="modulepreload"&&n(s)}).observe(document,{childList:!0,subtree:!0});function r(t){const o={};return t.integrity&&(o.integrity=t.integrity),t.referrerPolicy&&(o.referrerPolicy=t.referrerPolicy),t.crossOrigin==="use-credentials"?o.credentials="include":t.crossOrigin==="anonymous"?o.credentials="omit":o.credentials="same-origin",o}function n(t){if(t.ep)return;t.ep=!0;const o=r(t);fetch(t.href,o)}})();const w="/api/v1";function T(){return localStorage.getItem("mb_token")}function H(){localStorage.removeItem("mb_token")}async function h(a,e,r=null){const n={"Content-Type":"application/json"},t=T();t&&(n.Authorization=`Bearer ${t}`);const o={method:a,headers:n};r&&(o.body=JSON.stringify(r));try{const s=await fetch(`${w}${e}`,o);if(s.status===401)throw H(),window.dispatchEvent(new Event("auth:expired")),new Error("Session expired — please log in again");if(!s.ok){const d=await s.json().catch(()=>({detail:s.statusText}));throw new Error(d.detail||"API error")}return s.status===204?null:s.json()}catch(s){if(s.name==="TypeError"&&s.message==="Failed to fetch"){const d=window.location.href;throw new Error(`Connection to Python backend blocked! 
        <br><br><b>Diagnostic Info:</b>
        <br>1. Target Backend URL: <code>${w}${e}</code>
        <br>2. Current Browser URL: <code>${d}</code>
        <br><br><b>Likely Causes:</b>
        <br>- The Python backend is not running.
        <br>- You opened the HTML file directly instead of using 'npm run dev'.
        <br>- CORS is blocking it because your browser URL doesn't match the allowed origins.`)}throw s}}const c=a=>h("GET",a),u=(a,e)=>h("POST",a,e),D=(a,e)=>h("PUT",a,e),U=a=>h("DELETE",a),x={login:(a,e)=>u("/auth/login",{username:a,password:e}),register:(a,e)=>u("/auth/register",{username:a,password:e}),me:()=>c("/auth/me")},_={signals:(a=50,e="")=>c(`/scanner/signals?limit=${a}${e?`&strategy=${e}`:""}`),run:(a="AUTO")=>u(`/scanner/run?strategy=${a}`),regime:()=>c("/scanner/regime")},y={list:(a,e)=>{let r="/trades?limit=200";return a&&(r+=`&mode=${a}`),e&&(r+=`&status=${e}`),c(r)},summary:()=>c("/trades/summary"),create:a=>u("/trades",a),close:(a,e)=>u(`/trades/${a}/close`,e),cancel:a=>U(`/trades/${a}`)},B={run:a=>u("/backtest/run",a),progress:()=>c("/backtest/progress"),results:(a=20)=>c(`/backtest/results?limit=${a}`),detail:a=>c(`/backtest/${a}`)},E={summary:()=>c("/forward-test/summary"),logs:(a=30)=>c(`/forward-test/logs?limit=${a}`),update:()=>u("/forward-test/update")},f={get:()=>c("/settings"),update:a=>D("/settings",a),enableLive:a=>u("/settings/live",a)};function C(a,e,r){const n=T(),t=`${w}${a}${n?`?token=${n}`:""}`,o=new EventSource(t);return o.onmessage=s=>e(JSON.parse(s.data)),o.onerror=()=>o.close(),o}async function V(a){try{const[e,r]=await Promise.all([y.summary(),E.summary()]),n=o=>"₹"+Number(o).toLocaleString("en-IN");let t=`
      <div class="grid-3">
        <div class="card">
          <div class="stat-label">Trading Mode</div>
          <div class="stat-value" style="color: ${e.trading_mode==="live"?"var(--danger-color)":"var(--primary-color)"}">
            ${e.trading_mode.toUpperCase()}
          </div>
        </div>
        
        <div class="card">
          <div class="stat-label">Realized P&L (${e.trading_mode})</div>
          <div class="stat-value ${e.realized_pnl>=0?"positive":"negative"}">
            ${n(e.realized_pnl)}
          </div>
        </div>
        
        <div class="card">
          <div class="stat-label">Win Rate</div>
          <div class="stat-value">${e.win_rate}%</div>
        </div>
      </div>

      <h3 class="mb-4 mt-4">Active Trades Overview</h3>
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <div>Open Trades: <strong>${e.open_trades}</strong></div>
          <a href="/trades" class="btn btn-primary" onclick="event.preventDefault(); window.history.pushState({}, '', '/trades'); window.dispatchEvent(new Event('popstate'));">View All Trades</a>
        </div>
      </div>
      
      <h3 class="mb-4 mt-4">Forward Testing Progress</h3>
      <div class="grid-3">
        <div class="card">
          <div class="stat-label">Days Logged</div>
          <div class="stat-value">${r.days_logged}</div>
        </div>
        <div class="card">
          <div class="stat-label">Cumulative Paper P&L</div>
          <div class="stat-value ${r.cumulative_pnl>=0?"positive":"negative"}">
            ${n(r.cumulative_pnl)}
          </div>
        </div>
        <div class="card">
          <div class="stat-label">Forward Win Rate</div>
          <div class="stat-value">${r.win_rate}%</div>
        </div>
      </div>
    `;a.innerHTML=t}catch(e){a.innerHTML=`<div class="card negative">Failed to load dashboard: ${e.message}</div>`}}let v=null;async function q(a){a.innerHTML=`
    <div class="flex justify-between items-center mb-4" style="gap: 1rem; flex-wrap: wrap;">
      <div>
        <h3 style="margin:0;">Screener</h3>
        <span id="regime-badge" class="badge">Checking Regime...</span>
      </div>

      <div class="flex gap-2 items-center">
        <label class="form-label" style="margin:0; white-space:nowrap;">Strategy:</label>
        <select id="scan-strat" class="form-control" style="width: auto; margin: 0; padding: 0.375rem 1.75rem 0.375rem 0.75rem;">
          <option value="VCP">VCP (Volatility Contraction)</option>
          <option value="HARMAN1_PULLBACK">Swing Pullback (HARMAN1_PULLBACK)</option>
          <option value="VWAP_RUNNER">Intraday VWAP Bounce (VWAP_RUNNER)</option>
        </select>
      </div>

      <button id="btn-run-scan" class="btn btn-primary">
        Run Strategy Scan Now
      </button>
    </div>

    <div
      id="scan-progress-container"
      class="card mb-4"
      style="display:none;"
    >
      <div class="flex justify-between items-center mb-2">
        <span class="stat-label">Scanning NSE Universe...</span>
        <span id="scan-pct" class="mono">0%</span>
      </div>

      <div
        style="
          background:var(--border-color);
          height:8px;
          border-radius:4px;
          overflow:hidden;
        "
      >
        <div
          id="scan-bar"
          style="
            height:100%;
            width:0%;
            background:var(--primary-color);
            transition:width .3s;
          "
        ></div>
      </div>

      <div
        id="scan-symbol"
        class="text-muted mt-2"
        style="font-size:0.875rem;"
      >
        Initializing...
      </div>
    </div>

    <div class="table-wrapper">
      <table id="signals-table">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Quality</th>
            <th>Entry</th>
            <th>Stop Loss</th>
            <th>Target</th>
            <th>Setup Details</th>
            <th>Action</th>
          </tr>
        </thead>

        <tbody id="signals-body">
          <tr>
            <td colspan="7" style="text-align:center;">
              Loading...
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  `;const e=document.getElementById("btn-run-scan"),r=document.getElementById("signals-body"),n=document.getElementById("regime-badge"),t=document.getElementById("scan-strat"),o=document.getElementById("scan-progress-container"),s=document.getElementById("scan-bar"),d=document.getElementById("scan-pct"),g=document.getElementById("scan-symbol");async function p(){try{const i=t.value,m=await _.signals(50,i);if(P(m.market_regime),!m.signals||m.signals.length===0){r.innerHTML=`
          <tr>
            <td colspan="7" style="text-align:center;padding:2rem;">
              No active signals today for this strategy.
            </td>
          </tr>
        `;return}r.innerHTML=m.signals.map(l=>`
            <tr>
              <td>
                <strong>${l.symbol}</strong>
              </td>

              <td>
                <div class="flex items-center gap-2">
                  <div
                    style="
                      flex:1;
                      height:6px;
                      background:rgba(255,255,255,0.1);
                      border-radius:3px;
                    "
                  >
                    <div
                      style="
                        height:100%;
                        width:${l.quality}%;
                        background:${l.quality>85?"var(--accent-color)":"var(--warning-color)"};
                        border-radius:3px;
                      "
                    ></div>
                  </div>

                  <span class="mono">${l.quality}</span>
                </div>
              </td>

              <td class="mono">
                ₹${Number(l.entry).toFixed(2)}
              </td>

              <td class="mono negative">
                ₹${Number(l.stop_loss).toFixed(2)}
              </td>

              <td class="mono positive">
                ₹${Number(l.target||0).toFixed(2)}
              </td>

              <td
                style="
                  font-size:0.875rem;
                  color:var(--text-muted);
                "
              >
                ${l.strategy==="VWAP_RUNNER"?"Intraday VWAP Bounce<br>No daily indicators":l.strategy==="HARMAN1_PULLBACK"?`RSI: ${l.rsi?Number(l.rsi).toFixed(1):"N/A"}<br>Pullback: ${l.pullback_pct?Number(l.pullback_pct).toFixed(1):"0.0"}%`:`PB: ${Number(l.pullback_pct||0).toFixed(1)}%<br>VR: ${Number(l.vol_ratio||0).toFixed(1)}x`}
              </td>

              <td>
                <button
                  class="btn btn-outline trade-btn"
                  data-symbol="${l.symbol}"
                  data-entry="${l.entry}"
                  data-stop="${l.stop_loss}"
                  data-target="${l.target||0}"
                  style="padding:.25rem .5rem;font-size:.75rem;"
                >
                  Trade
                </button>
              </td>
            </tr>
          `).join(""),N()}catch(i){r.innerHTML=`
        <tr>
          <td colspan="7" class="negative">
            Error loading signals: ${i.message}
          </td>
        </tr>
      `}}function P(i){if(i)switch(n.textContent=`Regime: ${i}`,i){case"BULL":n.className="badge badge-success";break;case"PANIC":n.className="badge badge-danger";break;default:n.className="badge badge-warning"}}function N(){document.querySelectorAll(".trade-btn").forEach(i=>{i.addEventListener("click",async()=>{const m=i.dataset.symbol,l=Number(i.dataset.entry),M=Number(i.dataset.stop),R=Number(i.dataset.target),F=t.value;try{if(!confirm(`Open trade for ${m} at ₹${l.toFixed(2)} ?`))return;await y.create({symbol:m,strategy:F,entry_price:l,stop_loss:M,target:R,quantity:1}),alert("Trade opened successfully.")}catch($){alert(`Failed to open trade: ${$.message}`)}})})}function L(){v&&(v.close(),v=null),o.style.display="block",e.disabled=!0,v=C("/scanner/progress",i=>{if(i.total&&i.total>0){const m=Math.round(i.current/i.total*100);d.textContent=`${m}%`,s.style.width=`${m}%`,g.textContent=`Scanning ${i.symbol||"..."}...`}if(i.done||i.error){if(v&&(v.close(),v=null),o.style.display="none",e.disabled=!1,i.error){alert(`Scan failed: ${i.error}`);return}p()}})}e.addEventListener("click",async()=>{try{const i=t.value;await _.run(i),L()}catch(i){i.message&&i.message.toLowerCase().includes("already running")?L():alert(i.message)}}),t.addEventListener("change",p),await p()}let b=null;async function z(a){a.innerHTML=`
    <div class="grid-3">
      <div class="card" style="grid-column: span 1;">
        <h3 class="mb-4">New Backtest</h3>
        <form id="bt-form">
          <div class="form-group">
            <label class="form-label">Strategy</label>
            <select id="bt-strat" class="form-control">
              <option value="VCP">VCP (Volatility Contraction)</option>
              <option value="HARMAN1_PULLBACK">Swing Pullback (HARMAN1_PULLBACK)</option>
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
  `;const e=async()=>{try{const r=await B.results(),n=document.getElementById("bt-results");if(!r.length){n.innerHTML='<tr><td colspan="7" style="text-align:center;">No backtests run yet.</td></tr>';return}n.innerHTML=r.map(t=>`
        <tr>
          <td>${new Date(t.run_date).toLocaleDateString()}</td>
          <td><span class="badge" style="background:var(--border-color); font-size:0.75rem;">${t.strategy}</span></td>
          <td style="font-size:0.875rem">${t.start_date} → ${t.end_date}</td>
          <td class="mono ${t.total_return_pct>=0?"positive":"negative"}">${t.total_return_pct}%</td>
          <td class="mono">${t.win_rate}%</td>
          <td class="mono negative">-${t.max_drawdown}%</td>
          <td class="mono">${t.total_trades}</td>
        </tr>
      `).join("")}catch(r){console.error(r)}};await e(),document.getElementById("bt-form").addEventListener("submit",async r=>{r.preventDefault();const n=document.getElementById("btn-run-bt"),t=document.getElementById("bt-prog");try{await B.run({strategy:document.getElementById("bt-strat").value,start_date:document.getElementById("bt-start").value,end_date:document.getElementById("bt-end").value,capital:parseFloat(document.getElementById("bt-cap").value)}),n.disabled=!0,t.style.display="block",b&&b.close(),b=C("/backtest/progress/stream",o=>{if(o.total>0){const s=Math.round(o.current/o.total*100);document.getElementById("bt-pct").textContent=`${s}%`,document.getElementById("bt-bar").style.width=`${s}%`,document.getElementById("bt-sym").textContent=`Testing ${o.symbol}...`}(o.done||o.error)&&(b.close(),n.disabled=!1,t.style.display="none",o.error?alert("Error: "+o.error):e())})}catch(o){o.message.includes("already running")?alert("A backtest is already in progress."):alert(o.message)}})}async function O(a){a.innerHTML=`
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
  `;const e=async()=>{try{const r=await E.logs(),n=document.getElementById("fwd-body");if(!r.length){n.innerHTML='<tr><td colspan="7" style="text-align:center;">No forward test data yet. Ensure daily scan is running.</td></tr>';return}n.innerHTML=r.map(t=>`
        <tr>
          <td><strong>${t.date}</strong></td>
          <td><span class="badge ${t.regime==="BULL"?"badge-success":t.regime==="PANIC"?"badge-danger":"badge-warning"}">${t.regime}</span></td>
          <td class="mono">${t.signals_count}</td>
          <td class="mono">${t.trades_entered}</td>
          <td class="mono">${t.trades_closed}</td>
          <td class="mono ${t.daily_pnl>0?"positive":t.daily_pnl<0?"negative":""}">₹${t.daily_pnl.toFixed(2)}</td>
          <td class="mono ${t.cumulative_pnl>=0?"positive":"negative"}"><strong>₹${t.cumulative_pnl.toFixed(2)}</strong></td>
        </tr>
      `).join("")}catch(r){document.getElementById("fwd-body").innerHTML=`<tr><td colspan="7" class="negative">Error: ${r.message}</td></tr>`}};await e(),document.getElementById("btn-update-fwd").addEventListener("click",async r=>{const n=r.target;n.disabled=!0,n.textContent="Updating...";try{const t=await E.update();alert(`Update complete. Closed ${t.closed} trades, P&L today: ₹${t.pnl_today}`),await e()}catch(t){alert(t.message)}finally{n.disabled=!1,n.textContent="Trigger End-of-Day Update"}})}async function j(a){a.innerHTML=`
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
  `;const e=async()=>{try{const r=document.getElementById("filter-mode").value,n=document.getElementById("filter-status").value,t=await y.list(r,n),o=document.getElementById("trades-body");if(!t.length){o.innerHTML='<tr><td colspan="7" style="text-align:center; padding: 2rem;">No trades found.</td></tr>';return}o.innerHTML=t.map(s=>{const d=s.status==="closed",g=d?`<span class="mono ${s.pnl>=0?"positive":"negative"}">₹${s.pnl.toFixed(2)} (${s.pnl_pct.toFixed(2)}%)</span>`:'<span class="text-muted">—</span>';let p="badge-info";return s.mode==="live"&&(p="badge-danger"),s.mode==="forward"&&(p="badge-warning"),`
          <tr>
            <td><strong>${s.symbol}</strong><br><span style="font-size:0.75rem" class="text-muted">${new Date(s.entry_date).toLocaleDateString()}</span></td>
            <td><span class="badge ${p}">${s.mode.toUpperCase()}</span></td>
            <td><span class="badge ${d?"":"badge-success"}">${s.status.toUpperCase()}</span></td>
            <td>
              <div class="mono">₹${s.entry_price.toFixed(2)}</div>
              <div class="text-muted" style="font-size:0.75rem">Qty: ${s.quantity}</div>
            </td>
            <td>
              ${d?`<div class="mono">₹${s.exit_price.toFixed(2)}</div><div class="text-muted" style="font-size:0.75rem">${s.exit_reason}</div>`:'<span class="text-muted">Open</span>'}
            </td>
            <td>${g}</td>
            <td>
              ${d?"":`<button class="btn btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="window.closeTrade(${s.id}, ${s.target||s.entry_price*1.1})">Close</button>`}
            </td>
          </tr>
        `}).join("")}catch(r){document.getElementById("trades-body").innerHTML=`<tr><td colspan="7" class="negative">Error: ${r.message}</td></tr>`}};await e(),document.getElementById("filter-mode").addEventListener("change",e),document.getElementById("filter-status").addEventListener("change",e),window.closeTrade=async(r,n)=>{const t=prompt("Enter exit price:",n.toFixed(2));if(!t)return;const o=parseFloat(t);if(isNaN(o))return alert("Invalid price");try{await y.close(r,{exit_price:o,exit_reason:"MANUAL"}),e()}catch(s){alert("Failed to close trade: "+s.message)}}}async function W(a){a.innerHTML=`
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
  `;try{const e=await f.get();document.getElementById("capital").value=e.capital,document.getElementById("risk_pct").value=e.risk_pct,document.getElementById("max_sl_pct").value=e.max_sl_pct,document.getElementById("min_quality").value=e.min_quality;const r=document.getElementById("opt-live");if(e.trading_mode==="live"){r.disabled=!1;const n=document.getElementById("btn-live");n.textContent="LIVE MODE ACTIVE",n.disabled=!0,n.style.opacity="0.5"}document.getElementById("trading_mode").value=e.trading_mode}catch(e){console.error("Failed to load settings:",e)}document.getElementById("settings-form").addEventListener("submit",async e=>{e.preventDefault();try{await f.update({trading_mode:document.getElementById("trading_mode").value,capital:parseFloat(document.getElementById("capital").value),risk_pct:parseFloat(document.getElementById("risk_pct").value),max_sl_pct:parseFloat(document.getElementById("max_sl_pct").value),min_quality:parseInt(document.getElementById("min_quality").value,10)}),alert("Parameters saved successfully! Reloading..."),window.location.reload()}catch(r){alert("Error saving parameters: "+r.message)}}),document.getElementById("live-form").addEventListener("submit",async e=>{if(e.preventDefault(),!document.getElementById("g_confirm").checked)return alert("You must check the confirmation box.");const r=document.getElementById("btn-live");r.textContent="Verifying with Groww...",r.disabled=!0;try{await f.enableLive({confirm:!0,groww_api_key:document.getElementById("g_api").value,groww_secret_key:document.getElementById("g_sec").value,groww_client_id:document.getElementById("g_cid").value}),alert("LIVE mode enabled successfully! Reloading..."),window.location.reload()}catch(n){alert("Failed to enable LIVE mode: "+n.message),r.textContent="Authenticate & Enable LIVE",r.disabled=!1}})}const S=document.getElementById("app"),I={"/":{title:"Dashboard",render:V},"/scanner":{title:"Scanner",render:q},"/backtest":{title:"Backtest Engine",render:z},"/forward-test":{title:"Forward Testing",render:O},"/trades":{title:"Trades & Portfolio",render:j},"/settings":{title:"Settings",render:W}};async function G(){try{const a=await x.me();K(a),k(window.location.pathname)}catch{A()}}function A(){S.innerHTML=`
    <div style="display:flex; height:100vh; align-items:center; justify-content:center; background:var(--bg-color);">
      <div class="card" style="width: 420px; padding: 2.5rem;">
        <h2 style="text-align:center; margin-bottom: 2rem;" class="text-gradient">MarketBot</h2>
        
        <div style="display:flex; margin-bottom: 1.5rem; border-bottom: 1px solid var(--border-color);">
          <button id="tab-login" style="flex:1; padding:0.75rem; background:none; border:none; color:var(--text-color); font-weight:600; cursor:pointer; border-bottom:2px solid var(--primary-color);">Login</button>
          <button id="tab-register" style="flex:1; padding:0.75rem; background:none; border:none; color:var(--text-muted); font-weight:600; cursor:pointer; border-bottom:2px solid transparent;">Register</button>
        </div>

        <form id="auth-form">
          <div class="form-group">
            <label class="form-label">Username</label>
            <input type="text" id="username" class="form-control" required minlength="3" placeholder="Enter username" />
          </div>
          <div class="form-group">
            <label class="form-label">Password</label>
            <input type="password" id="password" class="form-control" required minlength="6" placeholder="Enter password" />
          </div>
          <button type="submit" id="submit-btn" class="btn btn-primary" style="width:100%; margin-top: 1rem;">Login</button>
          <div id="auth-error" class="negative mt-4" style="text-align:center; font-size:0.875rem;"></div>
        </form>
      </div>
    </div>
  `;let a="login";const e=document.getElementById("tab-login"),r=document.getElementById("tab-register"),n=document.getElementById("submit-btn"),t=document.getElementById("auth-error");e.addEventListener("click",()=>{a="login",e.style.borderBottomColor="var(--primary-color)",e.style.color="var(--text-color)",r.style.borderBottomColor="transparent",r.style.color="var(--text-muted)",n.textContent="Login",t.textContent=""}),r.addEventListener("click",()=>{a="register",r.style.borderBottomColor="var(--primary-color)",r.style.color="var(--text-color)",e.style.borderBottomColor="transparent",e.style.color="var(--text-muted)",n.textContent="Register",t.textContent=""}),document.getElementById("auth-form").addEventListener("submit",async o=>{o.preventDefault();const s=document.getElementById("username").value,d=document.getElementById("password").value;try{if(a==="login"){t.textContent="Authenticating...";const g=await x.login(s,d);localStorage.setItem("mb_token",g.access_token),window.location.reload()}else t.textContent="Creating account...",await x.register(s,d),t.className="positive mt-4",t.style.textAlign="center",t.textContent="Account created successfully! Switching to Login...",setTimeout(()=>{e.click()},1500)}catch(g){t.className="negative mt-4",t.style.textAlign="center",t.textContent=g.message}})}function K(a){S.innerHTML=`
    <aside class="sidebar">
      <div class="sidebar-logo">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--primary-color)"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
        MarketBot
      </div>
      <nav id="nav-links">
        <a href="/" class="nav-link" data-route="/"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="9"></rect><rect x="14" y="3" width="7" height="5"></rect><rect x="14" y="12" width="7" height="9"></rect><rect x="3" y="16" width="7" height="5"></rect></svg> Dashboard</a>
        <a href="/scanner" class="nav-link" data-route="/scanner"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> Scanner</a>
        <a href="/trades" class="nav-link" data-route="/trades"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg> Trades</a>
        <a href="/forward-test" class="nav-link" data-route="/forward-test"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"></path><path d="M22 12A10 10 0 0 0 12 2v10z"></path></svg> Forward Test</a>
        <a href="/backtest" class="nav-link" data-route="/backtest"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg> Backtest</a>
        <a href="/settings" class="nav-link" data-route="/settings"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg> Settings</a>
      </nav>
      <div style="margin-top: auto;">
        <button id="logout-btn" class="btn btn-outline" style="width:100%;">Logout</button>
      </div>
    </aside>
    <main class="main-content">
      <header class="topbar">
        <h2 id="page-title" style="margin:0; font-size:1.25rem;">Dashboard</h2>
        <div class="flex items-center gap-4">
          <span class="badge ${a.trading_mode==="live"?"badge-danger":"badge-info"}">Mode: ${a.trading_mode.toUpperCase()}</span>
          <span style="font-size: 0.875rem; color: var(--text-muted);">${a.app}</span>
        </div>
      </header>
      <div id="page-container" class="page-container">
        <!-- Content gets injected here -->
      </div>
    </main>
  `,document.getElementById("logout-btn").addEventListener("click",()=>{localStorage.removeItem("mb_token"),window.location.reload()}),document.querySelectorAll(".nav-link").forEach(e=>{e.addEventListener("click",r=>{r.preventDefault(),k(r.currentTarget.getAttribute("data-route"))})})}function k(a){window.location.pathname!==a&&window.history.pushState({},"",a);const e=I[a]||I["/"];document.getElementById("page-title").textContent=e.title,document.querySelectorAll(".nav-link").forEach(t=>t.classList.remove("active"));const r=document.querySelector(`.nav-link[data-route="${a}"]`);r&&r.classList.add("active");const n=document.getElementById("page-container");n.innerHTML='<div style="text-align:center; padding: 2rem;">Loading...</div>',e.render(n).catch(t=>{n.innerHTML=`<div class="card negative">Error loading page: ${t.message}</div>`})}window.addEventListener("popstate",()=>{k(window.location.pathname)});window.addEventListener("auth:expired",()=>{A()});G();
