export function renderLandingPage(container, onShowAuth) {
  container.innerHTML = `
    <div class="landing-page">
      
      <nav class="landing-nav">
        <div class="sidebar-logo" style="margin:0; padding:0; display:flex; align-items:center; gap:0.5rem; font-family: var(--font-mono); font-size: 1.25rem;">
          <img src="/logo.png" alt="MarketBot Logo" width="32" height="32" style="border-radius: 6px;">
          MARKET_BOT_OS
        </div>
        <div class="flex gap-4">
          <button id="nav-login-btn" class="btn btn-outline" style="background: transparent;">Log In</button>
          <button id="nav-register-btn" class="btn btn-primary" style="padding: 0.6rem 1.5rem;">Initialize Engine</button>
        </div>
      </nav>

      <!-- Live Ticker Tape Marquee -->
      <div class="ticker-wrap">
        <div class="ticker-content">
          <div class="ticker-item"><span class="text-muted">NIFTY 50</span> 23,450.50 <span class="text-green">▲ 0.8%</span></div>
          <div class="ticker-item"><span class="text-muted">RELIANCE</span> 2,980.00 <span class="text-green">▲ 1.2%</span></div>
          <div class="ticker-item"><span class="text-muted">HDFCBANK</span> 1,580.10 <span class="text-red">▼ 0.4%</span></div>
          <div class="ticker-item"><span class="text-muted">TCS</span> 3,845.20 <span class="text-green">▲ 0.5%</span></div>
          <div class="ticker-item"><span class="text-muted">INFY</span> 1,420.00 <span class="text-red">▼ 1.1%</span></div>
          <div class="ticker-item"><span class="text-muted">SBIN</span> 840.50 <span class="text-green">▲ 2.1%</span></div>
          <!-- Duplicate for seamless loop -->
          <div class="ticker-item"><span class="text-muted">NIFTY 50</span> 23,450.50 <span class="text-green">▲ 0.8%</span></div>
          <div class="ticker-item"><span class="text-muted">RELIANCE</span> 2,980.00 <span class="text-green">▲ 1.2%</span></div>
          <div class="ticker-item"><span class="text-muted">HDFCBANK</span> 1,580.10 <span class="text-red">▼ 0.4%</span></div>
          <div class="ticker-item"><span class="text-muted">TCS</span> 3,845.20 <span class="text-green">▲ 0.5%</span></div>
          <div class="ticker-item"><span class="text-muted">INFY</span> 1,420.00 <span class="text-red">▼ 1.1%</span></div>
          <div class="ticker-item"><span class="text-muted">SBIN</span> 840.50 <span class="text-green">▲ 2.1%</span></div>
        </div>
      </div>

      <main class="hero-section">
        <div class="hero-glow"></div>
        <div class="hero-content">
          <h1 class="hero-title">Master the Market.<br>Engineered for Precision.</h1>
          <p class="hero-subtitle">
            Professional-grade backtesting, real-time market scanning, and automated forward testing. 
            Build your algorithmic edge without risking real capital.
          </p>
          <button id="hero-cta-btn" class="btn btn-primary" style="font-size: 1.1rem; padding: 1rem 2.5rem; border-radius: 8px;">
            Deploy Sandbox Environment
          </button>

          <div class="terminal-mockup">
            <div class="terminal-header">
              <div class="dot dot-red"></div>
              <div class="dot dot-yellow"></div>
              <div class="dot dot-green"></div>
            </div>
            <div>> MarketBot Engine v2.0.0 initializing...</div>
            <div>> Connecting to market data stream... [OK]</div>
            <div>> Loading VCP scanner protocol... [OK]</div>
            <div style="color:var(--text-muted);">> Analyzing NIFTY 500 universe...</div>
            <br>
            <div><span style="color:var(--accent-green);">[SIGNAL]</span> BUY TITAN.NS @ 3420.50 (VCP Breakout)</div>
            <div><span style="color:var(--accent-green);">[SIGNAL]</span> BUY RELIANCE.NS @ 2950.00 (MACD Crossover)</div>
            <div><span style="color:var(--accent-red);">[ALERT]</span> STOP LOSS HIT - INFY.NS @ 1420.00</div>
            <br>
            <div class="spinner" style="border-width:2px; width:12px; height:12px; border-top-color:#0f0;"></div> Awaiting next tick...
          </div>
        </div>
      </main>

      <!-- Bento Box Features -->
      <section class="bento-grid">
        <div class="bento-card bento-large">
          <div class="bento-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path></svg>
          </div>
          <h3 class="bento-title">Zero-Risk Sandbox</h3>
          <p class="text-muted" style="font-size: 1.05rem; line-height: 1.6;">
            Execute paper trades in real-time. Our sandbox environment hooks directly into live market data feeds so you can test your strategies exactly as they would perform in the wild.
          </p>
        </div>
        
        <div class="bento-card bento-small">
          <div class="bento-icon" style="background: rgba(239, 83, 80, 0.1); color: var(--accent-red);">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
          </div>
          <h3 class="bento-title">Backtest Engine</h3>
          <p class="text-muted">Simulate thousands of trades across 5+ years of historical OHLCV data instantly.</p>
        </div>

        <div class="bento-card bento-small">
          <div class="bento-icon" style="background: rgba(38, 166, 154, 0.1); color: var(--accent-green);">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
          </div>
          <h3 class="bento-title">Market Scanner</h3>
          <p class="text-muted">Automated scans detect MACD crossovers, VCP breakouts, and momentum anomalies.</p>
        </div>

        <div class="bento-card bento-large">
          <div class="bento-icon" style="background: rgba(244, 162, 97, 0.1); color: #f4a261;">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
          </div>
          <h3 class="bento-title">Automated Forward Testing</h3>
          <p class="text-muted" style="font-size: 1.05rem; line-height: 1.6;">
            Turn your manual strategies into background cron jobs. Let the engine monitor the NIFTY 500 universe and execute paper trades on your behalf while you sleep.
          </p>
        </div>
      </section>

      <!-- Stats Footer -->
      <section class="stats-section">
        <div class="stats-grid">
          <div>
            <div class="stat-big-val">1.2M+</div>
            <div class="text-muted" style="font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">Candles Analyzed</div>
          </div>
          <div>
            <div class="stat-big-val">0ms</div>
            <div class="text-muted" style="font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">Execution Latency</div>
          </div>
          <div>
            <div class="stat-big-val">500+</div>
            <div class="text-muted" style="font-weight: 500; text-transform: uppercase; letter-spacing: 1px;">Supported Assets</div>
          </div>
        </div>
      </section>
    </div>
  `;

  document.getElementById('nav-login-btn').addEventListener('click', () => onShowAuth('login'));
  document.getElementById('nav-register-btn').addEventListener('click', () => onShowAuth('register'));
  document.getElementById('hero-cta-btn').addEventListener('click', () => onShowAuth('register'));
}
