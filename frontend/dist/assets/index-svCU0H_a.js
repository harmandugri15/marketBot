(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const t of document.querySelectorAll('link[rel="modulepreload"]'))o(t);new MutationObserver(t=>{for(const a of t)if(a.type==="childList")for(const n of a.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&o(n)}).observe(document,{childList:!0,subtree:!0});function s(t){const a={};return t.integrity&&(a.integrity=t.integrity),t.referrerPolicy&&(a.referrerPolicy=t.referrerPolicy),t.crossOrigin==="use-credentials"?a.credentials="include":t.crossOrigin==="anonymous"?a.credentials="omit":a.credentials="same-origin",a}function o(t){if(t.ep)return;t.ep=!0;const a=s(t);fetch(t.href,a)}})();const k="/api/v1";function C(){return localStorage.getItem("mb_token")}function D(){localStorage.removeItem("mb_token")}async function w(r,e,s=null){const o={"Content-Type":"application/json"},t=C();t&&(o.Authorization=`Bearer ${t}`);const a={method:r,headers:o};s&&(a.body=JSON.stringify(s));try{const n=await fetch(`${k}${e}`,a);if(n.status===401)throw D(),window.dispatchEvent(new Event("auth:expired")),new Error("Session expired — please log in again");if(!n.ok){const i=await n.json().catch(()=>({detail:n.statusText}));throw new Error(i.detail||"API error")}return n.status===204?null:n.json()}catch(n){if(n.name==="TypeError"&&n.message==="Failed to fetch"){const i=window.location.href;throw new Error(`Connection to Python backend blocked! 
        <br><br><b>Diagnostic Info:</b>
        <br>1. Target Backend URL: <code>${k}${e}</code>
        <br>2. Current Browser URL: <code>${i}</code>
        <br><br><b>Likely Causes:</b>
        <br>- The Python backend is not running.
        <br>- You opened the HTML file directly instead of using 'npm run dev'.
        <br>- CORS is blocking it because your browser URL doesn't match the allowed origins.`)}throw n}}const m=r=>w("GET",r),p=(r,e)=>w("POST",r,e),H=(r,e)=>w("PUT",r,e),z=r=>w("DELETE",r),_={login:(r,e)=>p("/auth/login",{username:r,password:e}),register:(r,e)=>p("/auth/register",{username:r,password:e}),me:()=>m("/auth/me")},S={signals:(r=50,e="")=>m(`/scanner/signals?limit=${r}${e?`&strategy=${e}`:""}`),run:(r="AUTO")=>p(`/scanner/run?strategy=${r}`),regime:()=>m("/scanner/regime")},f={list:(r,e)=>{let s="/trades?limit=200";return r&&(s+=`&mode=${r}`),e&&(s+=`&status=${e}`),m(s)},summary:()=>m("/trades/summary"),create:r=>p("/trades",r),close:(r,e)=>p(`/trades/${r}/close`,e),cancel:r=>z(`/trades/${r}`)},E={run:r=>p("/backtest/run",r),progress:()=>m("/backtest/progress"),results:(r=20)=>m(`/backtest/results?limit=${r}`),detail:r=>m(`/backtest/${r}`)},L={summary:()=>m("/forward-test/summary"),logs:(r=30)=>m(`/forward-test/logs?limit=${r}`),update:()=>p("/forward-test/update")},$={get:()=>m("/settings"),update:r=>H("/settings",r),enableLive:r=>p("/settings/live",r)};function A(r,e,s){const o=C(),t=`${k}${r}${o?`?token=${o}`:""}`,a=new EventSource(t);return a.onmessage=n=>e(JSON.parse(n.data)),a.onerror=()=>a.close(),a}async function q(r){try{const[e,s]=await Promise.all([f.summary(),L.summary()]),o=a=>"₹"+Number(a).toLocaleString("en-IN");let t=`
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
            ${o(e.realized_pnl)}
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
          <div class="stat-value">${s.days_logged}</div>
        </div>
        <div class="card">
          <div class="stat-label">Cumulative Paper P&L</div>
          <div class="stat-value ${s.cumulative_pnl>=0?"positive":"negative"}">
            ${o(s.cumulative_pnl)}
          </div>
        </div>
        <div class="card">
          <div class="stat-label">Forward Win Rate</div>
          <div class="stat-value">${s.win_rate}%</div>
        </div>
      </div>
    `;r.innerHTML=t}catch(e){r.innerHTML=`<div class="card negative">Failed to load dashboard: ${e.message}</div>`}}let v=null;async function U(r){r.innerHTML=`
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
  `;const e=document.getElementById("btn-run-scan"),s=document.getElementById("signals-body"),o=document.getElementById("regime-badge"),t=document.getElementById("scan-strat"),a=document.getElementById("scan-progress-container"),n=document.getElementById("scan-bar"),i=document.getElementById("scan-pct"),g=document.getElementById("scan-symbol");async function c(){try{const l=t.value,u=await S.signals(50,l);if(y(u.market_regime),!u.signals||u.signals.length===0){s.innerHTML=`
          <tr>
            <td colspan="7" style="text-align:center;padding:2rem;">
              No active signals today for this strategy.
            </td>
          </tr>
        `;return}s.innerHTML=u.signals.map(d=>`
            <tr>
              <td>
                <strong>${d.symbol}</strong>
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
                        width:${d.quality}%;
                        background:${d.quality>85?"var(--accent-color)":"var(--warning-color)"};
                        border-radius:3px;
                      "
                    ></div>
                  </div>

                  <span class="mono">${d.quality}</span>
                </div>
              </td>

              <td class="mono">
                ₹${Number(d.entry).toFixed(2)}
              </td>

              <td class="mono negative">
                ₹${Number(d.stop_loss).toFixed(2)}
              </td>

              <td class="mono positive">
                ₹${Number(d.target||0).toFixed(2)}
              </td>

              <td
                style="
                  font-size:0.875rem;
                  color:var(--text-muted);
                "
              >
                ${d.strategy==="VWAP_RUNNER"?"Intraday VWAP Bounce<br>No daily indicators":d.strategy==="HARMAN1_PULLBACK"?`RSI: ${d.rsi?Number(d.rsi).toFixed(1):"N/A"}<br>Pullback: ${d.pullback_pct?Number(d.pullback_pct).toFixed(1):"0.0"}%`:`PB: ${Number(d.pullback_pct||0).toFixed(1)}%<br>VR: ${Number(d.vol_ratio||0).toFixed(1)}x`}
              </td>

              <td>
                <button
                  class="btn btn-outline trade-btn"
                  data-symbol="${d.symbol}"
                  data-entry="${d.entry}"
                  data-stop="${d.stop_loss}"
                  data-target="${d.target||0}"
                  style="padding:.25rem .5rem;font-size:.75rem;"
                >
                  Trade
                </button>
              </td>
            </tr>
          `).join(""),x()}catch(l){s.innerHTML=`
        <tr>
          <td colspan="7" class="negative">
            Error loading signals: ${l.message}
          </td>
        </tr>
      `}}function y(l){if(l)switch(o.textContent=`Regime: ${l}`,l){case"BULL":o.className="badge badge-success";break;case"PANIC":o.className="badge badge-danger";break;default:o.className="badge badge-warning"}}function x(){document.querySelectorAll(".trade-btn").forEach(l=>{l.addEventListener("click",async()=>{const u=l.dataset.symbol,d=Number(l.dataset.entry),M=Number(l.dataset.stop),R=Number(l.dataset.target),F=t.value;try{if(!confirm(`Open trade for ${u} at ₹${d.toFixed(2)} ?`))return;await f.create({symbol:u,strategy:F,entry_price:d,stop_loss:M,target:R,quantity:1}),alert("Trade opened successfully.")}catch(I){alert(`Failed to open trade: ${I.message}`)}})})}function b(){v&&(v.close(),v=null),a.style.display="block",e.disabled=!0,v=A("/scanner/progress",l=>{if(l.total&&l.total>0){const u=Math.round(l.current/l.total*100);i.textContent=`${u}%`,n.style.width=`${u}%`,g.textContent=`Scanning ${l.symbol||"..."}...`}if(l.done||l.error){if(v&&(v.close(),v=null),a.style.display="none",e.disabled=!1,l.error){alert(`Scan failed: ${l.error}`);return}c()}})}e.addEventListener("click",async()=>{try{const l=t.value;await S.run(l),b()}catch(l){l.message&&l.message.toLowerCase().includes("already running")?b():alert(l.message)}}),t.addEventListener("change",c),await c()}let h=null;async function V(r){r.innerHTML=`
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
  `;const e=async()=>{try{const o=await E.results(),t=document.getElementById("bt-results");if(!o.length){t.innerHTML='<tr><td colspan="7" style="text-align:center;">No backtests run yet.</td></tr>';return}t.innerHTML=o.map(a=>`
        <tr class="clickable-row" data-id="${a.id}" style="cursor:pointer;">
          <td>${new Date(a.run_date).toLocaleDateString()}</td>
          <td><span class="badge" style="background:var(--border-color); font-size:0.75rem;">${a.strategy}</span></td>
          <td style="font-size:0.875rem">${a.start_date} → ${a.end_date}</td>
          <td class="mono ${a.total_return_pct>=0?"positive":"negative"}">${a.total_return_pct}%</td>
          <td class="mono">${a.win_rate}%</td>
          <td class="mono negative">-${a.max_drawdown}%</td>
          <td class="mono">${a.total_trades}</td>
        </tr>
      `).join(""),document.querySelectorAll(".clickable-row").forEach(a=>{a.addEventListener("click",async()=>{const n=a.getAttribute("data-id");await s(n)})})}catch(o){console.error(o)}};async function s(o){try{const t=await E.detail(o);let a=document.getElementById("bt-detail-modal");a||(a=document.createElement("div"),a.id="bt-detail-modal",document.body.appendChild(a)),a.style.position="fixed",a.style.top="0",a.style.left="0",a.style.width="100vw",a.style.height="100vh",a.style.background="rgba(11, 15, 25, 0.85)",a.style.backdropFilter="blur(8px)",a.style.zIndex="1000",a.style.display="flex",a.style.justifyContent="center",a.style.alignItems="center",a.style.padding="2rem";const n=(t.trade_log||[]).map((i,g)=>{const c=i.pnl||0,y=i.pnl_pct||0,x=i.entry||i.entry_price||0,b=i.exit||i.exit_price||0,l=i.qty||i.shares||0;return`
          <tr>
            <td style="color:var(--text-muted)">${g+1}</td>
            <td style="font-weight:600;">${i.symbol}</td>
            <td><span class="badge" style="background:var(--border-color);">${i.strategy||"—"}</span></td>
            <td>${i.entry_date||"—"}</td>
            <td>${i.exit_date||"—"}</td>
            <td class="mono">₹${x.toLocaleString("en-IN")}</td>
            <td class="mono">${b?`₹${b.toLocaleString("en-IN")}`:"—"}</td>
            <td class="mono">${l}</td>
            <td class="mono ${c>=0?"positive":"negative"}">${c>=0?"+":""}₹${Math.abs(c).toLocaleString("en-IN")}</td>
            <td class="mono ${y>=0?"positive":"negative"}">${y>=0?"+":""}${y.toFixed(1)}%</td>
            <td><span class="badge" style="background:rgba(255,255,255,0.05); color:var(--text-muted);">${i.exit_reason||"—"}</span></td>
          </tr>
        `}).join("");a.innerHTML=`
        <div class="card" style="width: 90%; max-width: 1200px; max-height: 85vh; overflow-y: auto; display: flex; flex-direction: column; gap: 1.5rem; position: relative; border: 1px solid var(--border-color); background: var(--bg-color);">
          <button id="close-modal-btn" style="position: absolute; top: 1.5rem; right: 1.5rem; background: transparent; color: var(--text-muted); font-size: 1.5rem; width: 32px; height: 32px; border-radius: 50%; display: flex; justify-content: center; align-items: center; border: 1px solid var(--border-color); cursor: pointer;">
            &times;
          </button>
          
          <div>
            <h2>Backtest Details</h2>
            <p class="text-muted" style="font-size: 0.875rem;">Strategy: <strong>${t.strategy}</strong> | Tested Period: <strong>${t.start_date} → ${t.end_date}</strong></p>
          </div>
          
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 1rem;">
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Total Return</div>
              <div class="stat-value ${t.total_return_pct>=0?"positive":"negative"}">${t.total_return_pct>=0?"+":""}${t.total_return_pct}%</div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Win Rate</div>
              <div class="stat-value">${t.win_rate}%</div>
              <div style="font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem;">${t.winning_trades}W / ${t.losing_trades}L</div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Profit Factor</div>
              <div class="stat-value">${t.profit_factor}</div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Max Drawdown</div>
              <div class="stat-value negative">-${t.max_drawdown}%</div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Avg Win / Loss</div>
              <div style="font-size: 1.1rem; font-weight: 700; margin-top: 0.5rem; font-family: var(--font-mono);">
                <span class="positive">+${t.avg_gain_pct}%</span> / <span class="negative">-${t.avg_loss_pct}%</span>
              </div>
            </div>
            <div class="card" style="padding: 1rem; text-align: center; background: rgba(255,255,255,0.02)">
              <div class="stat-label">Ending Capital</div>
              <div class="stat-value" style="font-size: 1.5rem; margin-top: 0.75rem;">₹${t.final_capital.toLocaleString("en-IN")}</div>
            </div>
          </div>

          <div>
            <h3 class="mb-3">Executed Trades (${t.total_trades} total)</h3>
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
                  ${n||'<tr><td colspan="11" style="text-align:center;">No trades were executed.</td></tr>'}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `,document.getElementById("close-modal-btn").onclick=()=>{a.remove()},a.onclick=i=>{i.target===a&&a.remove()}}catch(t){alert("Failed to load backtest details: "+t.message)}}await e(),document.getElementById("bt-form").addEventListener("submit",async o=>{o.preventDefault();const t=document.getElementById("btn-run-bt"),a=document.getElementById("bt-prog");try{await E.run({strategy:document.getElementById("bt-strat").value,start_date:document.getElementById("bt-start").value,end_date:document.getElementById("bt-end").value,capital:parseFloat(document.getElementById("bt-cap").value)}),t.disabled=!0,a.style.display="block",h&&h.close(),h=A("/backtest/progress/stream",n=>{if(n.total>0){const i=Math.round(n.current/n.total*100);document.getElementById("bt-pct").textContent=`${i}%`,document.getElementById("bt-bar").style.width=`${i}%`,document.getElementById("bt-sym").textContent=`Testing ${n.symbol}...`}(n.done||n.error)&&(h.close(),t.disabled=!1,a.style.display="none",n.error?alert("Error: "+n.error):e())})}catch(n){n.message.includes("already running")?alert("A backtest is already in progress."):alert(n.message)}})}async function j(r){r.innerHTML=`
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
  `;const e=async()=>{try{const s=await L.logs(),o=document.getElementById("fwd-body");if(!s.length){o.innerHTML='<tr><td colspan="7" style="text-align:center;">No forward test data yet. Ensure daily scan is running.</td></tr>';return}o.innerHTML=s.map(t=>`
        <tr>
          <td><strong>${t.date}</strong></td>
          <td><span class="badge ${t.regime==="BULL"?"badge-success":t.regime==="PANIC"?"badge-danger":"badge-warning"}">${t.regime}</span></td>
          <td class="mono">${t.signals_count}</td>
          <td class="mono">${t.trades_entered}</td>
          <td class="mono">${t.trades_closed}</td>
          <td class="mono ${t.daily_pnl>0?"positive":t.daily_pnl<0?"negative":""}">₹${t.daily_pnl.toFixed(2)}</td>
          <td class="mono ${t.cumulative_pnl>=0?"positive":"negative"}"><strong>₹${t.cumulative_pnl.toFixed(2)}</strong></td>
        </tr>
      `).join("")}catch(s){document.getElementById("fwd-body").innerHTML=`<tr><td colspan="7" class="negative">Error: ${s.message}</td></tr>`}};await e(),document.getElementById("btn-update-fwd").addEventListener("click",async s=>{const o=s.target;o.disabled=!0,o.textContent="Updating...";try{const t=await L.update();alert(`Update complete. Closed ${t.closed} trades, P&L today: ₹${t.pnl_today}`),await e()}catch(t){alert(t.message)}finally{o.disabled=!1,o.textContent="Trigger End-of-Day Update"}})}async function O(r){r.innerHTML=`
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
  `;const e=async()=>{try{const s=document.getElementById("filter-mode").value,o=document.getElementById("filter-status").value,t=await f.list(s,o),a=document.getElementById("trades-body");if(!t.length){a.innerHTML='<tr><td colspan="7" style="text-align:center; padding: 2rem;">No trades found.</td></tr>';return}a.innerHTML=t.map(n=>{const i=n.status==="closed",g=i?`<span class="mono ${n.pnl>=0?"positive":"negative"}">₹${n.pnl.toFixed(2)} (${n.pnl_pct.toFixed(2)}%)</span>`:'<span class="text-muted">—</span>';let c="badge-info";return n.mode==="live"&&(c="badge-danger"),n.mode==="forward"&&(c="badge-warning"),`
          <tr>
            <td><strong>${n.symbol}</strong><br><span style="font-size:0.75rem" class="text-muted">${new Date(n.entry_date).toLocaleDateString()}</span></td>
            <td><span class="badge ${c}">${n.mode.toUpperCase()}</span></td>
            <td><span class="badge ${i?"":"badge-success"}">${n.status.toUpperCase()}</span></td>
            <td>
              <div class="mono">₹${n.entry_price.toFixed(2)}</div>
              <div class="text-muted" style="font-size:0.75rem">Qty: ${n.quantity}</div>
            </td>
            <td>
              ${i?`<div class="mono">₹${n.exit_price.toFixed(2)}</div><div class="text-muted" style="font-size:0.75rem">${n.exit_reason}</div>`:'<span class="text-muted">Open</span>'}
            </td>
            <td>${g}</td>
            <td>
              ${i?"":`<button class="btn btn-outline" style="padding:0.25rem 0.5rem; font-size:0.75rem;" onclick="window.closeTrade(${n.id}, ${n.target||n.entry_price*1.1})">Close</button>`}
            </td>
          </tr>
        `}).join("")}catch(s){document.getElementById("trades-body").innerHTML=`<tr><td colspan="7" class="negative">Error: ${s.message}</td></tr>`}};await e(),document.getElementById("filter-mode").addEventListener("change",e),document.getElementById("filter-status").addEventListener("change",e),window.closeTrade=async(s,o)=>{const t=prompt("Enter exit price:",o.toFixed(2));if(!t)return;const a=parseFloat(t);if(isNaN(a))return alert("Invalid price");try{await f.close(s,{exit_price:a,exit_reason:"MANUAL"}),e()}catch(n){alert("Failed to close trade: "+n.message)}}}async function W(r){r.innerHTML=`
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
  `;try{const e=await $.get();document.getElementById("capital").value=e.capital,document.getElementById("risk_pct").value=e.risk_pct,document.getElementById("max_sl_pct").value=e.max_sl_pct,document.getElementById("min_quality").value=e.min_quality;const s=document.getElementById("opt-live");if(e.trading_mode==="live"){s.disabled=!1;const o=document.getElementById("btn-live");o.textContent="LIVE MODE ACTIVE",o.disabled=!0,o.style.opacity="0.5"}document.getElementById("trading_mode").value=e.trading_mode}catch(e){console.error("Failed to load settings:",e)}document.getElementById("settings-form").addEventListener("submit",async e=>{e.preventDefault();try{await $.update({trading_mode:document.getElementById("trading_mode").value,capital:parseFloat(document.getElementById("capital").value),risk_pct:parseFloat(document.getElementById("risk_pct").value),max_sl_pct:parseFloat(document.getElementById("max_sl_pct").value),min_quality:parseInt(document.getElementById("min_quality").value,10)}),alert("Parameters saved successfully! Reloading..."),window.location.reload()}catch(s){alert("Error saving parameters: "+s.message)}}),document.getElementById("live-form").addEventListener("submit",async e=>{if(e.preventDefault(),!document.getElementById("g_confirm").checked)return alert("You must check the confirmation box.");const s=document.getElementById("btn-live");s.textContent="Verifying with Groww...",s.disabled=!0;try{await $.enableLive({confirm:!0,groww_api_key:document.getElementById("g_api").value,groww_secret_key:document.getElementById("g_sec").value,groww_client_id:document.getElementById("g_cid").value}),alert("LIVE mode enabled successfully! Reloading..."),window.location.reload()}catch(o){alert("Failed to enable LIVE mode: "+o.message),s.textContent="Authenticate & Enable LIVE",s.disabled=!1}})}const P=document.getElementById("app"),T={"/":{title:"Dashboard",render:q},"/scanner":{title:"Scanner",render:U},"/backtest":{title:"Backtest Engine",render:V},"/forward-test":{title:"Forward Testing",render:j},"/trades":{title:"Trades & Portfolio",render:O},"/settings":{title:"Settings",render:W}};async function G(){try{const r=await _.me();K(r),B(window.location.pathname)}catch{N()}}function N(){P.innerHTML=`
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
  `;let r="login";const e=document.getElementById("tab-login"),s=document.getElementById("tab-register"),o=document.getElementById("submit-btn"),t=document.getElementById("auth-error");e.addEventListener("click",()=>{r="login",e.style.borderBottomColor="var(--primary-color)",e.style.color="var(--text-color)",s.style.borderBottomColor="transparent",s.style.color="var(--text-muted)",o.textContent="Login",t.textContent=""}),s.addEventListener("click",()=>{r="register",s.style.borderBottomColor="var(--primary-color)",s.style.color="var(--text-color)",e.style.borderBottomColor="transparent",e.style.color="var(--text-muted)",o.textContent="Register",t.textContent=""}),document.getElementById("auth-form").addEventListener("submit",async a=>{a.preventDefault();const n=document.getElementById("username").value,i=document.getElementById("password").value;try{if(r==="login"){t.textContent="Authenticating...";const g=await _.login(n,i);localStorage.setItem("mb_token",g.access_token),window.location.reload()}else t.textContent="Creating account...",await _.register(n,i),t.className="positive mt-4",t.style.textAlign="center",t.textContent="Account created successfully! Switching to Login...",setTimeout(()=>{e.click()},1500)}catch(g){t.className="negative mt-4",t.style.textAlign="center",t.textContent=g.message}})}function K(r){P.innerHTML=`
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
          <span class="badge ${r.trading_mode==="live"?"badge-danger":"badge-info"}">Mode: ${r.trading_mode.toUpperCase()}</span>
          <span style="font-size: 0.875rem; color: var(--text-muted);">${r.app}</span>
        </div>
      </header>
      <div id="page-container" class="page-container">
        <!-- Content gets injected here -->
      </div>
    </main>
  `,document.getElementById("logout-btn").addEventListener("click",()=>{localStorage.removeItem("mb_token"),window.location.reload()}),document.querySelectorAll(".nav-link").forEach(e=>{e.addEventListener("click",s=>{s.preventDefault(),B(s.currentTarget.getAttribute("data-route"))})})}function B(r){window.location.pathname!==r&&window.history.pushState({},"",r);const e=T[r]||T["/"];document.getElementById("page-title").textContent=e.title,document.querySelectorAll(".nav-link").forEach(t=>t.classList.remove("active"));const s=document.querySelector(`.nav-link[data-route="${r}"]`);s&&s.classList.add("active");const o=document.getElementById("page-container");o.innerHTML='<div style="text-align:center; padding: 2rem;">Loading...</div>',e.render(o).catch(t=>{o.innerHTML=`<div class="card negative">Error loading page: ${t.message}</div>`})}window.addEventListener("popstate",()=>{B(window.location.pathname)});window.addEventListener("auth:expired",()=>{N()});G();
