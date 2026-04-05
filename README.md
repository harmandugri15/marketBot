# VCP Trading Bot — Vijay Thakkar Strategy
## Setup Guide for Beginners

---

## What this bot does

This bot automates the VCP (Volatility Contraction Pattern) swing trading
strategy described by Vijay Thakkar. It:

1. Scans NSE small/mid-cap stocks every day after market close
2. Identifies stocks that match all 6 VCP criteria
3. Shows you the entry price and stop loss for each setup
4. Lets you backtest the strategy on 1 year of real historical data
5. Tracks your trades and P&L in a web dashboard
6. Can place real orders via your Groww API (optional)

**By default it runs in PAPER TRADING mode — no real money is touched
until you explicitly switch to live mode in the settings.**

---

## Step 1: Install Python packages

Open a terminal (Command Prompt on Windows, Terminal on Mac/Linux).
Navigate to this folder, then run:

```
pip install -r requirements.txt
```

If that gives an error on Linux, run:
```
pip install -r requirements.txt --break-system-packages
```

---

## Step 2: Add your Groww API key

1. Open the file called `.env` in this folder (use Notepad or any text editor)
2. Replace `your_api_key_here` with your actual Groww API key
3. Replace `your_secret_key_here` with your Groww secret key
4. Replace `your_client_id_here` with your Groww client ID
5. Save the file

You can also do this from the dashboard (Configuration tab) after starting the bot.

To find your Groww API credentials:
- Log in to Groww
- Go to Settings → Developer / API
- Copy your API Key, Secret Key, and Client ID

---

## Step 3: Start the bot

In your terminal, run:

```
python app.py
```

You should see:
```
VCP Trading Bot starting up
Paper trading: True
Capital: ₹5,00,000
Open your browser at: http://localhost:5000
```

---

## Step 4: Open the dashboard

Open your web browser and go to:

```
http://localhost:5000
```

You'll see the VCP Trading Bot dashboard.

---

## Step 5: Run a backtest first

Before using real money, run the backtest:

1. Click "Backtest" in the left sidebar
2. Set the date range (e.g. 2024-01-01 to 2024-12-31)
3. Click "Run Backtest"
4. Wait for it to complete (may take a few minutes)
5. Review the results: win rate, equity curve, trade log

This will tell you how the strategy would have performed on real historical data.

---

## Step 6: Run the live scanner

After market close (after 3:30 PM IST):

1. Click "Live Signals" in the sidebar
2. Click "Run VCP Scanner Now"
3. The bot will scan all 50 stocks and show valid setups
4. Review each signal — entry price, stop loss, quality score
5. Click "+ Open Trade" to enter a paper trade

---

## Understanding the dashboard

| Section | What it shows |
|---|---|
| Dashboard | Overview of capital, active trades, P&L |
| Live Signals | Stocks currently meeting VCP criteria |
| Trades | All open and closed positions |
| Backtest | Historical performance testing |
| Logs | Real-time activity log |
| Configuration | API keys and risk settings |
| Strategy Guide | Full explanation of the VCP strategy |

---

## Important notes for beginners

1. **Always start in paper trading mode.** The default is paper mode.
   No real orders are placed until you change the setting to "Live Trading."

2. **Run the backtest first.** Understand how the strategy performs
   before putting real money at risk.

3. **Never risk more than 2% per trade.** The bot enforces this by default.

4. **The 5% stop loss rule is mandatory.** If the stop loss would be
   more than 5% from the entry price, the bot rejects that trade.

5. **Do not trade when the index is defensive.** The bot checks this
   automatically during the scan.

---

## File structure

```
vcp_bot/
├── app.py              ← Start the bot (run this)
├── config.py           ← All settings in one place
├── groww_api.py        ← Groww API communication
├── indicators.py       ← EMA, volume, pattern calculations
├── scanner.py          ← Finds VCP setups daily
├── backtester.py       ← Historical strategy testing
├── trade_manager.py    ← Manages open/closed trades
├── requirements.txt    ← Python packages needed
├── .env                ← Your API keys (keep private!)
├── data/
│   ├── trades.json     ← Your trade history
│   ├── signals.json    ← Latest scan results
│   └── backtest_results.json ← Latest backtest
├── logs/
│   └── bot.log         ← Bot activity log
└── templates/
    └── index.html      ← The web dashboard
```

---

## Getting help

If you see an error:

1. Check `logs/bot.log` — it contains detailed error messages
2. Make sure your `.env` file has the correct API key
3. Make sure you're connected to the internet
4. Make sure Python packages are installed (`pip install -r requirements.txt`)

---

## Switching to live trading

When you're confident the strategy works (after backtesting and paper trading):

1. Go to Configuration tab in the dashboard
2. Change Mode to "Live Trading (Real money)"
3. Click Save Configuration
4. Restart the bot (`python app.py`)

**Warning:** Live trading places real orders on your Groww account.
Start with small capital. Monitor the bot closely.
