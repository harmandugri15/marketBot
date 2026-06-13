import { scanner, trades, createSSE } from "../api.js";

let sse = null;

export async function renderScanner(container) {
  container.innerHTML = `
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
  `;

  const btnRun = document.getElementById("btn-run-scan");
  const tbody = document.getElementById("signals-body");
  const regimeBadge = document.getElementById("regime-badge");

  const progressContainer = document.getElementById(
    "scan-progress-container"
  );
  const progressBar = document.getElementById("scan-bar");
  const progressPct = document.getElementById("scan-pct");
  const progressSymbol = document.getElementById("scan-symbol");

  async function loadSignals() {
    try {
      const data = await scanner.signals();

      updateRegimeBadge(data.market_regime);

      if (!data.signals || data.signals.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="7" style="text-align:center;padding:2rem;">
              No active signals today.
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
                PB: ${Number(signal.pullback_pct || 0).toFixed(1)}%
                <br>
                VR: ${Number(signal.vol_ratio || 0).toFixed(1)}x
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

        try {
          const ok = confirm(
            `Open trade for ${symbol} at ₹${entry.toFixed(2)} ?`
          );

          if (!ok) return;

          await trades.create({
            symbol,
            strategy: "VCP",
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
      await scanner.run();
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

  await loadSignals();
}