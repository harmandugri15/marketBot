import Chart from 'chart.js/auto';
import 'chartjs-adapter-date-fns';
import { CandlestickController, CandlestickElement } from 'chartjs-chart-financial';
Chart.register(CandlestickController, CandlestickElement);
import { sandbox } from '../api.js';

const POPULAR_STOCKS = [
  { symbol: 'RELIANCE.NS', name: 'Reliance Industries' },
  { symbol: 'TCS.NS', name: 'TCS' },
  { symbol: 'HDFCBANK.NS', name: 'HDFC Bank' },
  { symbol: 'INFY.NS', name: 'Infosys' },
  { symbol: 'ICICIBANK.NS', name: 'ICICI Bank' },
  { symbol: 'SBIN.NS', name: 'State Bank of India' },
  { symbol: 'BHARTIARTL.NS', name: 'Bharti Airtel' },
  { symbol: 'ITC.NS', name: 'ITC' },
  { symbol: 'KOTAKBANK.NS', name: 'Kotak Bank' },
  { symbol: 'LT.NS', name: 'Larsen & Toubro' },
  { symbol: 'TITAN.NS', name: 'Titan Company' },
  { symbol: 'AXISBANK.NS', name: 'Axis Bank' },
  { symbol: 'SUNPHARMA.NS', name: 'Sun Pharma' },
  { symbol: 'TMCV.NS', name: 'Tata Motors CV' },
  { symbol: 'ETERNAL.NS', name: 'Eternal (Zomato)' },
  { symbol: 'LTM.NS', name: 'LTM (Mindtree)' },
  { symbol: 'WIPRO.NS', name: 'Wipro' },
  { symbol: 'MARUTI.NS', name: 'Maruti Suzuki' },
  { symbol: 'TATASTEEL.NS', name: 'Tata Steel' },
  { symbol: 'JSWSTEEL.NS', name: 'JSW Steel' },
];

const PERIODS = [
  { label: '1M', value: '1mo' },
  { label: '3M', value: '3mo' },
  { label: '6M', value: '6mo' },
  { label: '1Y', value: '1y' },
  { label: '5Y', value: '5y' },
];

const INTERVALS = [
  { label: '5m', value: '5m' },
  { label: '15m', value: '15m' },
  { label: '1H', value: '1h' },
  { label: '1D', value: '1d' },
];

let mainChart = null;
let rsiChart = null;

export async function renderSandbox(container) {
  const stockOptions = POPULAR_STOCKS.map(s =>
    `<option value="${s.symbol}">${s.name} (${s.symbol.replace('.NS', '')})</option>`
  ).join('');

  const periodBtns = PERIODS.map(p =>
    `<button class="period-btn ${p.value === '6mo' ? 'active' : ''}" data-period="${p.value}">${p.label}</button>`
  ).join('');

  const intervalBtns = INTERVALS.map(i =>
    `<button class="interval-btn period-btn ${i.value === '1d' ? 'active' : ''}" data-interval="${i.value}">${i.label}</button>`
  ).join('');

  container.innerHTML = `
    <div class="sandbox-layout">
      <!-- Left Panel: Chart -->
      <div class="sandbox-chart-card">
        <div class="flex justify-between items-center mb-4" style="gap:1rem; flex-wrap:wrap;">
          <div class="flex gap-3 items-center" style="flex:1; min-width:200px;">
            <select id="sb-stock" class="form-control" style="max-width:280px; margin:0;">
              <option value="">Select a stock…</option>
              ${stockOptions}
            </select>
            <select id="sb-chart-type" class="form-control" style="max-width:140px; margin:0;">
              <option value="line">Line Chart</option>
              <option value="bar">Bar Chart</option>
              <option value="candlestick">Candlestick</option>
            </select>
          </div>
          <div class="flex items-center">
            <div class="period-selector" id="sb-intervals" style="margin-right:0.75rem; padding-right:0.75rem; border-right:1px solid rgba(0,0,0,0.1);">
              ${intervalBtns}
            </div>
            <div class="period-selector" id="sb-periods">
              ${periodBtns}
            </div>
          </div>
        </div>

        <div id="sb-chart-wrapper" style="position:relative; width:100%; min-height:350px;">
          <canvas id="sb-main-chart"></canvas>
        </div>

        <div id="sb-rsi-wrapper" style="display:none; position:relative; width:100%; height:120px; margin-top:0.75rem;">
          <canvas id="sb-rsi-chart"></canvas>
        </div>

        <div class="indicator-toggles" id="sb-indicators">
          <label class="indicator-toggle">
            <input type="checkbox" id="ind-ema10"> EMA 10
          </label>
          <label class="indicator-toggle">
            <input type="checkbox" id="ind-ema20"> EMA 20
          </label>
          <label class="indicator-toggle">
            <input type="checkbox" id="ind-rsi"> RSI
          </label>
          <label class="indicator-toggle">
            <input type="checkbox" id="ind-volume"> Volume
          </label>
        </div>

        <div id="sb-chart-placeholder" class="text-center" style="padding:4rem 1rem; color:var(--text-muted);">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.3; margin-bottom:1rem;"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline></svg>
          <p style="font-weight:600;">Select a stock to view chart</p>
          <p style="font-size:0.82rem;">Choose from popular NSE stocks above</p>
        </div>
      </div>

      <!-- Right Panel: Trading -->
      <div class="sandbox-panel-card">
        <h3 class="mb-4" style="font-size:1rem;">Trading Panel</h3>

        <div id="sb-price-display" class="mb-4">
          <div class="stat-label">Current Price</div>
          <div class="current-price" id="sb-current-price">
            <span class="currency">₹</span><span id="sb-price-val">—</span>
          </div>
          <div id="sb-stock-name" style="font-size:0.82rem; color:var(--text-muted); margin-top:0.15rem;"></div>
        </div>

        <div class="trade-actions mb-4">
          <button class="btn-buy" id="sb-buy-btn" disabled>BUY</button>
          <button class="btn-sell" id="sb-sell-btn" disabled>SELL</button>
        </div>

        <div class="form-group">
          <label class="form-label">Quantity</label>
          <input type="number" id="sb-qty" class="form-control" min="1" value="1" placeholder="Shares" />
        </div>

        <div class="flex gap-3">
          <div class="form-group" style="flex:1;">
            <label class="form-label">Stop Loss</label>
            <input type="number" id="sb-sl" class="form-control" step="0.05" placeholder="₹ SL" />
          </div>
          <div class="form-group" style="flex:1;">
            <label class="form-label">Target</label>
            <input type="number" id="sb-target" class="form-control" step="0.05" placeholder="₹ Target" />
          </div>
        </div>

        <div class="risk-calc" id="sb-risk-calc">
          <div class="row">
            <span class="label">Total Value</span>
            <span class="value" id="rc-total">₹0</span>
          </div>
          <div class="row">
            <span class="label">Risk (Entry − SL) × Qty</span>
            <span class="value" id="rc-risk">₹0</span>
          </div>
          <div class="row">
            <span class="label">Reward (Target − Entry) × Qty</span>
            <span class="value" id="rc-reward">₹0</span>
          </div>
          <div class="row" style="border-top:1px solid rgba(0,0,0,0.06); padding-top:0.5rem; margin-top:0.3rem;">
            <span class="label">Risk:Reward</span>
            <span class="value" id="rc-rr">—</span>
          </div>
        </div>

        <button class="btn btn-primary w-full mt-4" id="sb-submit-trade" disabled>
          Submit Paper Trade
        </button>
        <div id="sb-trade-msg" class="auth-error mt-2"></div>

        <!-- Active Positions -->
        <div class="positions-list" id="sb-positions">
          <h4 class="mb-3 mt-6" style="font-size:0.9rem;">Active Positions</h4>
          <div id="sb-positions-list" style="color:var(--text-muted); font-size:0.85rem;">
            No positions yet
          </div>
        </div>
      </div>
    </div>
  `;

  // State
  let currentData = null;
  let currentIndicators = null;
  let selectedPeriod = '6mo';
  let selectedInterval = '1d';
  let tradeAction = null; // 'BUY' or 'SELL'
  let selectedChartType = 'line';
  let activePositions = []; // Store positions to update PnL
  let ws = null;

  // Elements
  const stockSelect = document.getElementById('sb-stock');
  const chartTypeSelect = document.getElementById('sb-chart-type');
  const priceVal = document.getElementById('sb-price-val');
  const stockNameEl = document.getElementById('sb-stock-name');
  const buyBtn = document.getElementById('sb-buy-btn');
  const sellBtn = document.getElementById('sb-sell-btn');
  const qtyInput = document.getElementById('sb-qty');
  const slInput = document.getElementById('sb-sl');
  const targetInput = document.getElementById('sb-target');
  const submitBtn = document.getElementById('sb-submit-trade');
  const tradeMsgEl = document.getElementById('sb-trade-msg');
  const placeholder = document.getElementById('sb-chart-placeholder');
  const chartWrapper = document.getElementById('sb-chart-wrapper');
  const rsiWrapper = document.getElementById('sb-rsi-wrapper');

  // Indicator checkboxes
  const indEma10 = document.getElementById('ind-ema10');
  const indEma20 = document.getElementById('ind-ema20');
  const indRsi = document.getElementById('ind-rsi');
  const indVolume = document.getElementById('ind-volume');

  // ── Chart loading ────────────────────────────────────────────────────
  async function loadChart() {
    const symbol = stockSelect.value;
    if (!symbol) return;

    placeholder.style.display = 'none';
    priceVal.textContent = '…';
    stockNameEl.textContent = 'Loading chart data…';

    try {
      const res = await sandbox.chart(symbol, selectedPeriod, selectedInterval);
      currentData = res.data || [];
      currentIndicators = res.indicators || {};

      if (!currentData.length) {
        stockNameEl.textContent = 'No data available for this period';
        return;
      }

      const lastRow = currentData[currentData.length - 1];
      const lastPrice = lastRow.close || lastRow.Close || 0;
      priceVal.textContent = Number(lastPrice).toLocaleString('en-IN', { minimumFractionDigits: 2 });

      const stockInfo = POPULAR_STOCKS.find(s => s.symbol === symbol);
      stockNameEl.textContent = stockInfo ? stockInfo.name : symbol;

      buyBtn.disabled = false;
      sellBtn.disabled = false;

      renderMainChart();
    } catch (err) {
      stockNameEl.textContent = `Error: ${err.message}`;
      currentData = null;
    }
  }

  // ── Render main chart ────────────────────────────────────────────────
  function renderMainChart() {
    if (!currentData || !currentData.length) return;

    const labels = currentData.map(d => d.date || d.Date || '');
    
    let datasets = [];
    if (selectedChartType === 'candlestick') {
      const candleData = currentData.map(d => ({
        x: new Date(d.date || d.Date).valueOf(),
        o: d.open || d.Open || 0,
        h: d.high || d.High || 0,
        l: d.low || d.Low || 0,
        c: d.close || d.Close || 0,
      }));
      datasets.push({
        label: 'Price',
        data: candleData,
        yAxisID: 'y',
        color: { up: '#2ec4b6', down: '#e63946', unchanged: '#94a3b8' },
        borderColor: { up: '#2ec4b6', down: '#e63946', unchanged: '#94a3b8' },
      });
    } else {
      const closes = currentData.map(d => d.close || d.Close || 0);
      datasets.push({
        label: 'Close',
        data: closes,
        borderColor: '#4361ee',
        backgroundColor: 'rgba(67, 97, 238, 0.06)',
        borderWidth: 2,
        pointRadius: 0,
        pointHoverRadius: 4,
        fill: true,
        tension: 0.3,
        yAxisID: 'y',
      });
    }

    // EMA overlays
    if (indEma10.checked && currentIndicators.ema10) {
      datasets.push({
        label: 'EMA 10',
        data: currentIndicators.ema10,
        borderColor: '#f4a261',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
        yAxisID: 'y',
      });
    }

    if (indEma20.checked && currentIndicators.ema20) {
      datasets.push({
        label: 'EMA 20',
        data: currentIndicators.ema20,
        borderColor: '#2ec4b6',
        borderWidth: 1.5,
        pointRadius: 0,
        fill: false,
        tension: 0.3,
        yAxisID: 'y',
      });
    }

    // Volume bars
    const isLight = document.body.classList.contains('theme-light');
    const textColor = isLight ? '#787b86' : '#64748b';
    const gridColor = isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)';
    const tooltipBg = isLight ? '#131722' : '#1a1f36';

    const scales = {
      x: {
        type: selectedChartType === 'candlestick' ? 'time' : 'category',
        display: true,
        grid: { display: false },
        time: selectedChartType === 'candlestick' ? { unit: 'day' } : undefined,
        ticks: {
          maxTicksLimit: 10,
          font: { size: 10, family: "'Inter', sans-serif" },
          color: textColor,
        },
      },
      y: {
        display: true,
        position: 'right',
        grid: { color: gridColor, drawBorder: false },
        ticks: {
          font: { size: 10, family: "'JetBrains Mono', monospace" },
          color: textColor,
        },
      },
    };

    if (indVolume.checked) {
      const volumes = currentData.map(d => d.volume || d.Volume || 0);
      datasets.push({
        label: 'Volume',
        data: volumes,
        type: 'bar',
        backgroundColor: 'rgba(67, 97, 238, 0.08)',
        borderColor: 'rgba(67, 97, 238, 0.15)',
        borderWidth: 1,
        yAxisID: 'yVol',
        order: 10,
      });
      scales.yVol = {
        display: false,
        position: 'left',
        grid: { display: false },
        max: Math.max(...currentData.map(d => d.volume || d.Volume || 0)) * 4,
      };
    }

    // Destroy old chart
    if (mainChart) { mainChart.destroy(); mainChart = null; }

    const ctx = document.getElementById('sb-main-chart');
    mainChart = new Chart(ctx, {
      type: selectedChartType,
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            display: datasets.length > 1,
            position: 'top',
            labels: {
              usePointStyle: true,
              pointStyle: 'circle',
              padding: 16,
              font: { size: 11, family: "'Inter', sans-serif" },
              color: '#64748b',
            },
          },
          tooltip: {
            backgroundColor: tooltipBg,
            titleFont: { family: "'Inter', sans-serif", size: 12 },
            bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
            padding: 10,
            cornerRadius: 6,
            displayColors: false,
          },
        },
        scales,
      },
    });

    // RSI chart
    handleRsiChart(labels);
  }

  function handleRsiChart(labels) {
    const isLight = document.body.classList.contains('theme-light');
    const textColor = isLight ? '#787b86' : '#64748b';
    const gridColor = isLight ? 'rgba(0,0,0,0.05)' : 'rgba(255,255,255,0.05)';
    const tooltipBg = isLight ? '#131722' : '#1a1f36';

    if (indRsi.checked && currentIndicators.rsi) {
      rsiWrapper.style.display = 'block';
      if (rsiChart) { rsiChart.destroy(); rsiChart = null; }

      const ctx = document.getElementById('sb-rsi-chart');
      rsiChart = new Chart(ctx, {
        type: 'line',
        data: {
          labels,
          datasets: [{
            label: 'RSI',
            data: currentIndicators.rsi,
            borderColor: '#a855f7',
            borderWidth: 1.5,
            pointRadius: 0,
            fill: false,
            tension: 0.3,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              backgroundColor: tooltipBg,
              bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
              cornerRadius: 4,
            },
          },
          scales: {
            x: { display: false },
            y: {
              min: 0,
              max: 100,
              grid: { color: gridColor, drawBorder: false },
              ticks: {
                stepSize: 30,
                font: { size: 9 },
                color: textColor,
              },
            },
          },
        },
      });
    } else {
      rsiWrapper.style.display = 'none';
      if (rsiChart) { rsiChart.destroy(); rsiChart = null; }
    }
  }

  // ── Risk calculator update ───────────────────────────────────────────
  function updateRiskCalc() {
    const price = parseFloat(priceVal.textContent.replace(/,/g, '')) || 0;
    const qty = parseInt(qtyInput.value) || 0;
    const sl = parseFloat(slInput.value) || 0;
    const target = parseFloat(targetInput.value) || 0;

    const total = price * qty;
    const risk = sl > 0 ? (price - sl) * qty : 0;
    const reward = target > 0 ? (target - price) * qty : 0;

    document.getElementById('rc-total').textContent = `₹${total.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    document.getElementById('rc-risk').textContent = `₹${Math.abs(risk).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    document.getElementById('rc-reward').textContent = `₹${Math.abs(reward).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

    if (risk > 0 && reward > 0) {
      const rr = (reward / risk).toFixed(2);
      document.getElementById('rc-rr').textContent = `1:${rr}`;
    } else {
      document.getElementById('rc-rr').textContent = '—';
    }
  }

  async function loadPositions() {
    const listEl = document.getElementById('sb-positions-list');
    try {
      activePositions = await sandbox.positions();
      renderPositionsList();
      updateWsSubscription();
    } catch (err) {
      listEl.innerHTML = `<div class="negative" style="font-size:0.82rem;">Failed to load positions</div>`;
    }
  }

  function renderPositionsList() {
    const listEl = document.getElementById('sb-positions-list');
    if (!activePositions || !activePositions.length) {
      listEl.innerHTML = '<div style="color:var(--text-muted); font-size:0.85rem;">No positions yet</div>';
      return;
    }

    listEl.innerHTML = activePositions.map(p => {
      const pnl = p.pnl || 0;
      const pnlClass = pnl >= 0 ? 'positive' : 'negative';
      return `
        <div class="position-item" id="pos-${p.id}">
          <div>
            <div class="symbol">${p.symbol}</div>
            <div class="details">${p.action || 'BUY'} × ${p.quantity} @ ₹${Number(p.entry_price).toFixed(2)}</div>
          </div>
          <div class="text-right">
            <div class="mono ${pnlClass} pos-pnl" style="font-weight:700; font-size:0.88rem;">
              ${pnl >= 0 ? '+' : ''}₹${Number(pnl).toFixed(2)}
            </div>
            <div class="details pos-ltp">LTP: ₹${Number(p.current_price || p.entry_price).toFixed(2)}</div>
          </div>
        </div>
      `;
    }).join('');
  }

  // ── WebSockets Live Data ─────────────────────────────────────────────
  function connectWebSocket() {
    if (ws) ws.close();
    
    const token = localStorage.getItem('mb_token');
    if (!token) return;

    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/api/v1/sandbox/ws/live?token=${token}`;
    
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      updateWsSubscription();
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'ltp_update') {
        const results = msg.data;
        const activeSymbol = stockSelect.value;
        let positionsUpdated = false;

        results.forEach(res => {
          if (!res || !res.ltp) return;
          const sym = res.symbol;
          const ltp = res.ltp;

          // If this is the chart's active symbol, update chart and price
          if (sym === activeSymbol) {
            priceVal.textContent = ltp.toLocaleString('en-IN', { minimumFractionDigits: 2 });
            updateRiskCalc();

            if (currentData && currentData.length > 0) {
              const lastRow = currentData[currentData.length - 1];
              if (lastRow.close) lastRow.close = ltp;
              if (lastRow.Close) lastRow.Close = ltp;
              if (ltp > (lastRow.high || lastRow.High)) {
                if (lastRow.high !== undefined) lastRow.high = ltp;
                if (lastRow.High !== undefined) lastRow.High = ltp;
              }
              if (ltp < (lastRow.low || lastRow.Low)) {
                if (lastRow.low !== undefined) lastRow.low = ltp;
                if (lastRow.Low !== undefined) lastRow.Low = ltp;
              }
              if (mainChart) mainChart.update('none');
            }
          }

          // Update active positions for this symbol
          activePositions.forEach(p => {
            if (p.symbol === sym) {
              p.current_price = ltp;
              const diff = ltp - p.entry_price;
              p.pnl = p.action === 'BUY' ? diff * p.quantity : -diff * p.quantity;
              positionsUpdated = true;
            }
          });
        });

        if (positionsUpdated) {
          renderPositionsList();
        }
      }
    };

    ws.onclose = () => {
      setTimeout(connectWebSocket, 5000); // Auto reconnect
    };
  }

  function updateWsSubscription() {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    
    const activeSymbol = stockSelect.value;
    const symbolsToPoll = new Set();
    if (activeSymbol) symbolsToPoll.add(activeSymbol);
    activePositions.forEach(p => symbolsToPoll.add(p.symbol));
    
    if (symbolsToPoll.size > 0) {
      ws.send(JSON.stringify({
        action: 'subscribe',
        symbols: Array.from(symbolsToPoll)
      }));
    }
  }

  // ── Event Listeners ──────────────────────────────────────────────────

  // Stock select
  stockSelect.addEventListener('change', () => {
    tradeAction = null;
    buyBtn.style.opacity = '1';
    sellBtn.style.opacity = '1';
    loadChart();
    updateWsSubscription();
  });

  // Chart type select
  chartTypeSelect.addEventListener('change', () => {
    selectedChartType = chartTypeSelect.value;
    if (currentData) renderMainChart();
  });

  // Interval buttons
  document.getElementById('sb-intervals').addEventListener('click', (e) => {
    const btn = e.target.closest('.interval-btn');
    if (!btn) return;
    document.querySelectorAll('.interval-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedInterval = btn.dataset.interval;
    if (stockSelect.value) loadChart();
  });

  // Period buttons
  document.getElementById('sb-periods').addEventListener('click', (e) => {
    const btn = e.target.closest('.period-btn:not(.interval-btn)');
    if (!btn) return;
    document.querySelectorAll('#sb-periods .period-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedPeriod = btn.dataset.period;
    if (stockSelect.value) loadChart();
  });

  // Indicator toggles
  [indEma10, indEma20, indRsi, indVolume].forEach(cb => {
    cb.addEventListener('change', () => {
      if (currentData) renderMainChart();
    });
  });

  // Listen to theme changes
  window.addEventListener('themeChanged', () => {
    if (currentData) renderMainChart();
  });

  // Buy / Sell buttons
  buyBtn.addEventListener('click', () => {
    tradeAction = 'BUY';
    buyBtn.style.opacity = '1';
    sellBtn.style.opacity = '0.4';
    submitBtn.disabled = false;
  });

  sellBtn.addEventListener('click', () => {
    tradeAction = 'SELL';
    sellBtn.style.opacity = '1';
    buyBtn.style.opacity = '0.4';
    submitBtn.disabled = false;
  });

  // Risk calc live update
  [qtyInput, slInput, targetInput].forEach(input => {
    input.addEventListener('input', updateRiskCalc);
  });

  // Submit trade
  submitBtn.addEventListener('click', async () => {
    if (!tradeAction || !stockSelect.value) return;

    const price = parseFloat(priceVal.textContent.replace(/,/g, '')) || 0;
    const data = {
      symbol: stockSelect.value,
      action: tradeAction,
      quantity: parseInt(qtyInput.value) || 1,
      price: price,
      stop_loss: parseFloat(slInput.value) || 0,
      target: parseFloat(targetInput.value) || 0,
    };

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Placing…';
    tradeMsgEl.className = 'auth-error mt-2';
    tradeMsgEl.style.display = 'none';

    try {
      await sandbox.trade(data);
      tradeMsgEl.className = 'auth-error mt-2 show success';
      tradeMsgEl.textContent = `${tradeAction} order placed for ${data.quantity} shares of ${data.symbol}`;
      await loadPositions();
    } catch (err) {
      tradeMsgEl.className = 'auth-error mt-2 show error';
      tradeMsgEl.textContent = err.message;
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = 'Submit Paper Trade';
    }
  });

  // Initial setup
  await loadPositions();
  connectWebSocket();
}
