(function(){const a=document.createElement("link").relList;if(a&&a.supports&&a.supports("modulepreload"))return;for(const t of document.querySelectorAll('link[rel="modulepreload"]'))n(t);new MutationObserver(t=>{for(const s of t)if(s.type==="childList")for(const o of s.addedNodes)o.tagName==="LINK"&&o.rel==="modulepreload"&&n(o)}).observe(document,{childList:!0,subtree:!0});function r(t){const s={};return t.integrity&&(s.integrity=t.integrity),t.referrerPolicy&&(s.referrerPolicy=t.referrerPolicy),t.crossOrigin==="use-credentials"?s.credentials="include":t.crossOrigin==="anonymous"?s.credentials="omit":s.credentials="same-origin",s}function n(t){if(t.ep)return;t.ep=!0;const s=r(t);fetch(t.href,s)}})();const f="/api/v1";function B(){return localStorage.getItem("mb_token")}function F(){localStorage.removeItem("mb_token")}async function y(e,a,r=null){const n={"Content-Type":"application/json"},t=B();t&&(n.Authorization=`Bearer ${t}`);const s={method:e,headers:n};r&&(s.body=JSON.stringify(r));try{const o=await fetch(`${f}${a}`,s);if(o.status===401)throw F(),window.dispatchEvent(new Event("auth:expired")),new Error("Session expired — please log in again");if(!o.ok){const c=await o.json().catch(()=>({detail:o.statusText}));throw new Error(c.detail||"API error")}return o.status===204?null:o.json()}catch(o){if(o.name==="TypeError"&&o.message==="Failed to fetch"){const c=window.location.href;throw new Error(`Connection to Python backend blocked! 
        <br><br><b>Diagnostic Info:</b>
        <br>1. Target Backend URL: <code>${f}${a}</code>
        <br>2. Current Browser URL: <code>${c}</code>
        <br><br><b>Likely Causes:</b>
        <br>- The Python backend is not running.
        <br>- You opened the HTML file directly instead of using 'npm run dev'.
        <br>- CORS is blocking it because your browser URL doesn't match the allowed origins.`)}throw o}}const d=e=>y("GET",e),u=(e,a)=>y("POST",e,a),A=(e,a)=>y("PUT",e,a),D=e=>y("DELETE",e),N={login:(e,a)=>u("/auth/login",{username:e,password:a}),me:()=>d("/auth/me")},L={signals:(e=50)=>d(`/scanner/signals?limit=${e}`),run:(e="AUTO")=>u(`/scanner/run?strategy=${e}`),regime:()=>d("/scanner/regime")},b={list:(e,a)=>{let r="/trades?limit=200";return e&&(r+=`&mode=${e}`),a&&(r+=`&status=${a}`),d(r)},summary:()=>d("/trades/summary"),create:e=>u("/trades",e),close:(e,a)=>u(`/trades/${e}/close`,a),cancel:e=>D(`/trades/${e}`)},_={run:e=>u("/backtest/run",e),progress:()=>d("/backtest/progress"),results:(e=20)=>d(`/backtest/results?limit=${e}`),detail:e=>d(`/backtest/${e}`)},w={summary:()=>d("/forward-test/summary"),logs:(e=30)=>d(`/forward-test/logs?limit=${e}`),update:()=>u("/forward-test/update")},h={get:()=>d("/settings"),update:e=>A("/settings",e),enableLive:e=>u("/settings/live",e)};function T(e,a,r){const n=B(),t=`${f}${e}${n?`?token=${n}`:""}`,s=new EventSource(t);return s.onmessage=o=>a(JSON.parse(o.data)),s.onerror=()=>s.close(),s}async function H(e){try{const[a,r]=await Promise.all([b.summary(),w.summary()]),n=s=>"₹"+Number(s).toLocaleString("en-IN");let t=`
      <div class="grid-3">
        <div class="card">
          <div class="stat-label">Trading Mode</div>
          <div class="stat-value" style="color: ${a.trading_mode==="live"?"var(--danger-color)":"var(--primary-color)"}">
            ${a.trading_mode.toUpperCase()}
          </div>
        </div>
        
        <div class="card">
          <div class="stat-label">Realized P&L (${a.trading_mode})</div>
          <div class="stat-value ${a.realized_pnl>=0?"positive":"negative"}">
            ${n(a.realized_pnl)}
          </div>
        </div>
        
        <div class="card">
          <div class="stat-label">Win Rate</div>
          <div class="stat-value">${a.win_rate}%</div>
        </div>
      </div>

      <h3 class="mb-4 mt-4">Active Trades Overview</h3>
      <div class="card">
        <div class="flex justify-between items-center mb-4">
          <div>Open Trades: <strong>${a.open_trades}</strong></div>
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
    `;e.innerHTML=t}catch(a){e.innerHTML=`<div class="card negative">Failed to load dashboard: ${a.message}</div>`}}let m=null;async function q(e){e.innerHTML=`
    <div class="flex justify-between items-center mb-4">
      <div>
        <h3 style="margin:0;">VCP Screener</h3>
        <span id="regime-badge" class="badge">Checking Regime...</span>
      </div>

      <button id="btn-run-scan" class="btn btn-primary">
        Run Daily Scan Now
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
  `;const a=document.getElementById("btn-run-scan"),r=document.getElementById("signals-body"),n=document.getElementById("regime-badge"),t=document.getElementById("scan-progress-container"),s=document.getElementById("scan-bar"),o=document.getElementById("scan-pct"),c=document.getElementById("scan-symbol");async function p(){try{const i=await L.signals();if(g(i.market_regime),!i.signals||i.signals.length===0){r.innerHTML=`
          <tr>
            <td colspan="7" style="text-align:center;padding:2rem;">
              No active signals today.
            </td>
          </tr>
        `;return}r.innerHTML=i.signals.map(l=>`
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
                PB: ${Number(l.pullback_pct||0).toFixed(1)}%
                <br>
                VR: ${Number(l.vol_ratio||0).toFixed(1)}x
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
          `).join(""),C()}catch(i){r.innerHTML=`
        <tr>
          <td colspan="7" class="negative">
            Error loading signals: ${i.message}
          </td>
        </tr>
      `}}function g(i){if(i)switch(n.textContent=`Regime: ${i}`,i){case"BULL":n.className="badge badge-success";break;case"PANIC":n.className="badge badge-danger";break;default:n.className="badge badge-warning"}}function C(){document.querySelectorAll(".trade-btn").forEach(i=>{i.addEventListener("click",async()=>{const l=i.dataset.symbol,k=Number(i.dataset.entry),M=Number(i.dataset.stop),P=Number(i.dataset.target);try{if(!confirm(`Open trade for ${l} at ₹${k.toFixed(2)} ?`))return;await b.create({symbol:l,strategy:"VCP",entry_price:k,stop_loss:M,target:P,quantity:1}),alert("Trade opened successfully.")}catch($){alert(`Failed to open trade: ${$.message}`)}})})}function x(){m&&(m.close(),m=null),t.style.display="block",a.disabled=!0,m=T("/scanner/progress",i=>{if(i.total&&i.total>0){const l=Math.round(i.current/i.total*100);o.textContent=`${l}%`,s.style.width=`${l}%`,c.textContent=`Scanning ${i.symbol||"..."}...`}if(i.done||i.error){if(m&&(m.close(),m=null),t.style.display="none",a.disabled=!1,i.error){alert(`Scan failed: ${i.error}`);return}p()}})}a.addEventListener("click",async()=>{try{await L.run(),x()}catch(i){i.message&&i.message.toLowerCase().includes("already running")?x():alert(i.message)}}),await p()}let v=null;async function z(e){e.innerHTML=`
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
  `;const a=async()=>{try{const r=await _.results(),n=document.getElementById("bt-results");if(!r.length){n.innerHTML='<tr><td colspan="6" style="text-align:center;">No backtests run yet.</td></tr>';return}n.innerHTML=r.map(t=>`
        <tr>
          <td>${new Date(t.run_date).toLocaleDateString()}</td>
          <td style="font-size:0.875rem">${t.start_date} → ${t.end_date}</td>
          <td class="mono ${t.total_return_pct>=0?"positive":"negative"}">${t.total_return_pct}%</td>
          <td class="mono">${t.win_rate}%</td>
          <td class="mono negative">-${t.max_drawdown}%</td>
          <td class="mono">${t.total_trades}</td>
        </tr>
      `).join("")}catch(r){console.error(r)}};await a(),document.getElementById("bt-form").addEventListener("submit",async r=>{r.preventDefault();const n=document.getElementById("btn-run-bt"),t=document.getElementById("bt-prog");try{await _.run({start_date:document.getElementById("bt-start").value,end_date:document.getElementById("bt-end").value,capital:parseFloat(document.getElementById("bt-cap").value)}),n.disabled=!0,t.style.display="block",v&&v.close(),v=T("/backtest/progress/stream",s=>{if(s.total>0){const o=Math.round(s.current/s.total*100);document.getElementById("bt-pct").textContent=`${o}%`,document.getElementById("bt-bar").style.width=`${o}%`,document.getElementById("bt-sym").textContent=`Testing ${s.symbol}...`}(s.done||s.error)&&(v.close(),n.disabled=!1,t.style.display="none",s.error?alert("Error: "+s.error):a())})}catch(s){s.message.includes("already running")?alert("A backtest is already in progress."):alert(s.message)}})}async function R(e){e.innerHTML=`
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
  `;const a=async()=>{try{const r=await w.logs(),n=document.getElementById("fwd-body");if(!r.length){n.innerHTML='<tr><td colspan="7" style="text-align:center;">No forward test data yet. Ensure daily scan is running.</td></tr>';return}n.innerHTML=r.map(t=>`
        <tr>
          <td><strong>${t.date}</strong></td>
          <td><span class="badge ${t.regime==="BULL"?"badge-success":t.regime==="PANIC"?"badge-danger":"badge-warning"}">${t.regime}</span></td>
          <td class="mono">${t.signals_count}</td>
          <td class="mono">${t.trades_entered}</td>
          <td class="mono">${t.trades_closed}</td>
          <td class="mono ${t.daily_pnl>0?"positive":t.daily_pnl<0?"negative":""}">₹${t.daily_pnl.toFixed(2)}</td>
          <td class="mono ${t.cumulative_pnl>=0?"positive":"negative"}"><strong>₹${t.cumulative_pnl.toFixed(2)}</strong></td>
        </tr>
      `).join("")}catch(r){document.getElementById("fwd-body").innerHTML=`<tr><td colspan="7" class="negative">Error: ${r.message}</td></tr>`}};await a(),document.getElementById("btn-update-fwd").addEventListener("click",async r=>{const n=r.target;n.disabled=!0,n.textContent="Updating...";try{const t=await w.update();alert(`Update complete. Closed ${t.closed} trades, P&L today: ₹${t.pnl_today}`),await a()}catch(t){alert(t.message)}finally{n.disabled=!1,n.textContent="Trigger End-of-Day Update"}})}async function U(e){e.innerHTML=`
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
  `;const a=async()=>{try{const r=document.getElementById("filter-mode").value,n=document.getElementById("filter-status").value,t=await b.list(r,n),s=document.getElementById("trades-body");if(!t.length){s.innerHTML='<tr><td colspan="7" style="text-align:center; padding: 2rem;">No trades found.</td></tr>';return}s.innerHTML=t.map(o=>{const c=o.status==="closed",p=c?`<span class="mono ${o.pnl>=0?"positive":"negative"}">₹${o.pnl.toFixed(2)} (${o.pnl_pct.toFixed(2)}%)</span>`:'<span class="text-muted">—</span>';let g="badge-info";return o.mode==="live"&&(g="badge-danger"),o.mode==="forward"&&(g="badge-warning"),`
          <tr>
            <td><strong>${o.symbol}</strong><br><span style="font-size:0.75rem" class="text-muted">${new Date(o.entry_date).toLocaleDateString()}</span></td>
            <td><span class="badge ${g}">${o.mode.toUpperCase()}</span></td>
            <td><span class="badge ${c?"":"badge-success"}">${o.status.toUpperCase()}</span></td>
            <td>
              <div class="mono">₹${o.entry_price.toFixed(2)}</div>
              <div class="text-muted" style="font-size:0.75rem">Qty: ${o.quantity}</div>
            </td>
            <td>
              ${c?`<div class="mono">₹${o.exit_price.toFixed(2)}</div><div class="text-muted" style="font-size:0.75rem">${o.exit_reason}</div>`:'<span class="text-muted">Open</span>'}
            </td>
            <td>${p}</td>
            <td>
              ${c?"":`<button class="btn btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="window.closeTrade(${o.id}, ${o.target||o.entry_price*1.1})">Close</button>`}
            </td>
          </tr>
        `}).join("")}catch(r){document.getElementById("trades-body").innerHTML=`<tr><td colspan="7" class="negative">Error: ${r.message}</td></tr>`}};await a(),document.getElementById("filter-mode").addEventListener("change",a),document.getElementById("filter-status").addEventListener("change",a),window.closeTrade=async(r,n)=>{const t=prompt("Enter exit price:",n.toFixed(2));if(!t)return;const s=parseFloat(t);if(isNaN(s))return alert("Invalid price");try{await b.close(r,{exit_price:s,exit_reason:"MANUAL"}),a()}catch(o){alert("Failed to close trade: "+o.message)}}}async function V(e){e.innerHTML=`
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
  `;try{const a=await h.get();if(document.getElementById("capital").value=a.capital,document.getElementById("risk_pct").value=a.risk_pct,document.getElementById("max_sl_pct").value=a.max_sl_pct,document.getElementById("min_quality").value=a.min_quality,a.trading_mode==="live"){const r=document.getElementById("btn-live");r.textContent="LIVE MODE ACTIVE",r.disabled=!0,r.style.opacity="0.5"}}catch(a){console.error("Failed to load settings:",a)}document.getElementById("settings-form").addEventListener("submit",async a=>{a.preventDefault();try{await h.update({capital:parseFloat(document.getElementById("capital").value),risk_pct:parseFloat(document.getElementById("risk_pct").value),max_sl_pct:parseFloat(document.getElementById("max_sl_pct").value),min_quality:parseInt(document.getElementById("min_quality").value,10)}),alert("Parameters saved successfully!")}catch(r){alert("Error saving parameters: "+r.message)}}),document.getElementById("live-form").addEventListener("submit",async a=>{if(a.preventDefault(),!document.getElementById("g_confirm").checked)return alert("You must check the confirmation box.");const r=document.getElementById("btn-live");r.textContent="Verifying with Groww...",r.disabled=!0;try{await h.enableLive({confirm:!0,groww_api_key:document.getElementById("g_api").value,groww_secret_key:document.getElementById("g_sec").value,groww_client_id:document.getElementById("g_cid").value}),alert("LIVE mode enabled successfully! Reloading..."),window.location.reload()}catch(n){alert("Failed to enable LIVE mode: "+n.message),r.textContent="Authenticate & Enable LIVE",r.disabled=!1}})}const S=document.getElementById("app"),I={"/":{title:"Dashboard",render:H},"/scanner":{title:"Scanner",render:q},"/backtest":{title:"Backtest Engine",render:z},"/forward-test":{title:"Forward Testing",render:R},"/trades":{title:"Trades & Portfolio",render:U},"/settings":{title:"Settings",render:V}};async function O(){G({app:"MarketBot",trading_mode:"paper"}),E(window.location.pathname)}function j(){S.innerHTML=`
    <div style="display:flex; height:100vh; align-items:center; justify-content:center; background:var(--bg-color);">
      <div class="card" style="width: 400px;">
        <h2 style="text-align:center; margin-bottom: 1.5rem;" class="text-gradient">MarketBot Login</h2>
        <form id="login-form">
          <div class="form-group">
            <label class="form-label">Username</label>
            <input type="text" id="username" class="form-control" required value="admin" />
          </div>
          <div class="form-group">
            <label class="form-label">Password</label>
            <input type="password" id="password" class="form-control" required />
          </div>
          <button type="submit" class="btn btn-primary" style="width:100%;">Login</button>
          <div id="login-error" class="negative mt-4" style="text-align:center; font-size:0.875rem;"></div>
        </form>
      </div>
    </div>
  `,document.getElementById("login-form").addEventListener("submit",async e=>{e.preventDefault();const a=document.getElementById("username").value,r=document.getElementById("password").value,n=document.getElementById("login-error");try{n.textContent="Authenticating...";const t=await N.login(a,r);localStorage.setItem("mb_token",t.access_token),window.location.reload()}catch(t){n.textContent=t.message}})}function G(e){S.innerHTML=`
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
          <span class="badge ${e.trading_mode==="live"?"badge-danger":"badge-info"}">Mode: ${e.trading_mode.toUpperCase()}</span>
          <span style="font-size: 0.875rem; color: var(--text-muted);">${e.app}</span>
        </div>
      </header>
      <div id="page-container" class="page-container">
        <!-- Content gets injected here -->
      </div>
    </main>
  `,document.getElementById("logout-btn").addEventListener("click",()=>{localStorage.removeItem("mb_token"),window.location.reload()}),document.querySelectorAll(".nav-link").forEach(a=>{a.addEventListener("click",r=>{r.preventDefault(),E(r.currentTarget.getAttribute("data-route"))})})}function E(e){window.location.pathname!==e&&window.history.pushState({},"",e);const a=I[e]||I["/"];document.getElementById("page-title").textContent=a.title,document.querySelectorAll(".nav-link").forEach(t=>t.classList.remove("active"));const r=document.querySelector(`.nav-link[data-route="${e}"]`);r&&r.classList.add("active");const n=document.getElementById("page-container");n.innerHTML='<div style="text-align:center; padding: 2rem;">Loading...</div>',a.render(n).catch(t=>{n.innerHTML=`<div class="card negative">Error loading page: ${t.message}</div>`})}window.addEventListener("popstate",()=>{E(window.location.pathname)});window.addEventListener("auth:expired",()=>{j()});O();
