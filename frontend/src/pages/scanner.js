import { scanner, trades, createSSE } from "../api.js";

let sse = null;

export async function renderScanner(container) {
  container.innerHTML = `
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
          <option value="GOOGLE_SWING">Google Swing (EMA/RSI/ATR)</option>
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
  `;

  const btnRun = document.getElementById("btn-run-scan");
  const tbody = document.getElementById("signals-body");
  const regimeBadge = document.getElementById("regime-badge");
  const stratSelect = document.getElementById("scan-strat");

  const progressContainer = document.getElementById(
    "scan-progress-container"
  );
  const progressBar = document.getElementById("scan-bar");
  const progressPct = document.getElementById("scan-pct");
  const progressSymbol = document.getElementById("scan-symbol");

  async function loadSignals() {
    try {
      const selectedStrat = stratSelect.value;
      const data = await scanner.signals(50, selectedStrat);

      updateRegimeBadge(data.market_regime);

      if (!data.signals || data.signals.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align:center;padding:2rem;">
              No active signals today for this strategy.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = data.signals
        .map(
          (signal) => `
            <tr>
              <td>
                <strong>${signal.symbol}</strong>
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
                        width:${signal.quality}%;
                        background:${
                          signal.quality > 85
                            ? "var(--accent-color)"
                            : "var(--warning-color)"
                        };
                        border-radius:3px;
                      "
                    ></div>
                  </div>

                  <span class="mono">${signal.quality}</span>
                </div>
              </td>

              <td class="mono">
                ₹${Number(signal.entry).toFixed(2)}
              </td>

              <td class="mono negative">
                ₹${Number(signal.stop_loss).toFixed(2)}
              </td>

              <td class="mono positive">
                ₹${Number(signal.target || 0).toFixed(2)}
              </td>

              <td
                style="
                  font-size:0.875rem;
                  color:var(--text-muted);
                "
              >
                ${
                  signal.strategy === 'VWAP_RUNNER'
                    ? `Intraday VWAP Bounce<br>No daily indicators`
                    : signal.strategy === 'HARMAN1_PULLBACK'
                    ? `RSI: ${signal.rsi ? Number(signal.rsi).toFixed(1) : 'N/A'}<br>Pullback: ${signal.pullback_pct ? Number(signal.pullback_pct).toFixed(1) : '0.0'}%`
                    : `PB: ${Number(signal.pullback_pct || 0).toFixed(1)}%<br>VR: ${Number(signal.vol_ratio || 0).toFixed(1)}x`
                }
              </td>

              <td>
                <button
                  class="btn btn-outline trade-btn"
                  data-symbol="${signal.symbol}"
                  data-entry="${signal.entry}"
                  data-stop="${signal.stop_loss}"
                  data-target="${signal.target || 0}"
                  style="padding:.25rem .5rem;font-size:.75rem;"
                >
                  Trade
                </button>
              </td>
            </tr>
          `
        )
        .join("");

      attachTradeHandlers();
    } catch (error) {
      tbody.innerHTML = `
        <tr>
          <td colspan="7" class="negative">
            Error loading signals: ${error.message}
          </td>
        </tr>
      `;
    }
  }

  function updateRegimeBadge(regime) {
    if (!regime) return;

    regimeBadge.textContent = `Regime: ${regime}`;

    switch (regime) {
      case "BULL":
        regimeBadge.className = "badge badge-success";
        break;

      case "PANIC":
        regimeBadge.className = "badge badge-danger";
        break;

      default:
        regimeBadge.className = "badge badge-warning";
    }
  }

  function attachTradeHandlers() {
    document.querySelectorAll(".trade-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const symbol = btn.dataset.symbol;
        const entry = Number(btn.dataset.entry);
        const stopLoss = Number(btn.dataset.stop);
        const target = Number(btn.dataset.target);
        const selectedStrat = stratSelect.value;

        try {
          const ok = confirm(
            `Open trade for ${symbol} at ₹${entry.toFixed(2)} ?`
          );

          if (!ok) return;

          await trades.create({
            symbol,
            strategy: selectedStrat,
            entry_price: entry,
            stop_loss: stopLoss,
            target,
            quantity: 1,
          });

          alert("Trade opened successfully.");
        } catch (error) {
          alert(`Failed to open trade: ${error.message}`);
        }
      });
    });
  }

  function connectSSE() {
    if (sse) {
      sse.close();
      sse = null;
    }

    progressContainer.style.display = "block";
    btnRun.disabled = true;

    sse = createSSE("/scanner/progress", (data) => {
      if (data.total && data.total > 0) {
        const percentage = Math.round(
          (data.current / data.total) * 100
        );

        progressPct.textContent = `${percentage}%`;
        progressBar.style.width = `${percentage}%`;
        progressSymbol.textContent =
          `Scanning ${data.symbol || "..."}...`;
      }

      if (data.done || data.error) {
        if (sse) {
          sse.close();
          sse = null;
        }

        progressContainer.style.display = "none";
        btnRun.disabled = false;

        if (data.error) {
          alert(`Scan failed: ${data.error}`);
          return;
        }

        loadSignals();
      }
    });
  }

  btnRun.addEventListener("click", async () => {
    try {
      const selectedStrat = stratSelect.value;
      await scanner.run(selectedStrat);
      connectSSE();
    } catch (error) {
      if (
        error.message &&
        error.message.toLowerCase().includes("already running")
      ) {
        connectSSE();
      } else {
        alert(error.message);
      }
    }
  });

  stratSelect.addEventListener("change", loadSignals);

  await loadSignals();
}