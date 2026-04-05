"""
scanner.py
----------
Scans the stock universe for two strategies:
  - DEP (Delayed Episodic Pivot): Sniper, tight stop, waits for expansion + quiet pullback
  - VT  (Vijay Thakkar VCP):     Swing trade on 20 EMA bounce with MACD confirmation

Run after 3:30 PM every weekday.
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta

import pandas as pd

from config import (
    STOCK_UNIVERSE, SIGNALS_DB, TRADING_CAPITAL,
    RISK_PER_TRADE_PCT, MIN_QUALITY_SCORE
)

logger = logging.getLogger(__name__)


def _build_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate all required indicators on a clean OHLCV DataFrame."""
    df = df.copy()
    df["ema10"]      = df["close"].ewm(span=10, adjust=False).mean()
    df["ema20"]      = df["close"].ewm(span=20, adjust=False).mean()
    df["ema50"]      = df["close"].ewm(span=50, adjust=False).mean()
    df["ema200"]     = df["close"].ewm(span=200, adjust=False).mean()
    df["vol_sma50"]  = df["volume"].rolling(window=50).mean()
    df["vol_sma20"]  = df["volume"].rolling(window=20).mean()
    df["daily_ret"]  = df["close"].pct_change() * 100

    # MACD
    exp12            = df["close"].ewm(span=12, adjust=False).mean()
    exp26            = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]       = exp12 - exp26
    df["macd_sig"]   = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]  = df["macd"] - df["macd_sig"]

    # Pivot (use previous day's values to avoid look-ahead)
    df["pivot"]      = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3

    return df


def _check_dep(df: pd.DataFrame, symbol: str) -> dict | None:
    """
    Delayed Episodic Pivot (DEP) Setup.

    Looks for:
      1. A recent expansion day (big move up on big volume in last 15 days)
      2. Stock has since pulled back quietly — small candles, low volume, near 10 EMA
      3. Entry is above today's high; SL is below today's low
    """
    if len(df) < 100:
        return None

    today     = df.iloc[-1]
    yesterday = df.iloc[-2]

    # ── Find expansion day in last 15 sessions ──
    expansion_found = False
    for i in range(len(df) - 2, max(len(df) - 17, 0), -1):
        day = df.iloc[i]
        vol_avg = day.get("vol_sma50", 0)
        if vol_avg <= 0:
            continue
        if day["daily_ret"] >= 5.0 and day["volume"] >= 2.5 * vol_avg:
            # Make sure prior 20-day run-up is < 40% (don't buy exhausted moves)
            prior_close = df.iloc[max(0, i - 20)]["close"]
            run_up = (day["close"] - prior_close) / prior_close * 100
            if run_up < 40:
                expansion_found = True
                break

    if not expansion_found:
        return None

    # ── Quiet pullback: today must be low volume and tight range ──
    vol_avg_today = today.get("vol_sma50", 0)
    if vol_avg_today <= 0 or today["volume"] > vol_avg_today * 1.2:
        return None

    candle_range_pct = (today["high"] - today["low"]) / today["low"] * 100
    if candle_range_pct > 4.0:
        return None

    # ── Near 10 EMA ──
    ema10 = today.get("ema10", 0)
    if ema10 <= 0:
        return None
    dist_to_ema = abs(today["low"] - ema10) / ema10 * 100
    if dist_to_ema > 2.5:
        return None

    # ── Build signal ──
    entry = round(today["high"] + 0.05, 2)
    sl    = round(today["low"] - 0.05, 2)
    sl_pct = (entry - sl) / entry * 100

    if not (0.5 <= sl_pct <= 5.0):
        return None

    quality = 90 if sl_pct < 2.5 else 80

    return {
        "strategy":   "DEP",
        "symbol":     symbol,
        "entry_price": entry,
        "stop_loss":  sl,
        "sl_pct":     round(sl_pct, 2),
        "quality_score": quality,
        "notes":      f"DEP: Expansion + quiet pullback, {round(candle_range_pct,1)}% range, near 10 EMA"
    }


def _check_vt(df: pd.DataFrame, symbol: str) -> dict | None:
    """
    Vijay Thakkar (VT) VCP Momentum Setup.

    Looks for:
      1. Stock above 20 EMA and above central pivot
      2. Today crossed above or bounced off 20 EMA
      3. MACD histogram is rising (momentum increasing)
      4. Not an Open=High candle (bearish sign)
    """
    if len(df) < 50:
        return None

    today     = df.iloc[-1]
    yesterday = df.iloc[-2]

    # Must not be an Open=High candle (sign of weakness at open)
    if abs(today["open"] - today["high"]) < 0.01:
        return None

    ema20 = today.get("ema20", 0)
    pivot = today.get("pivot", 0)
    if ema20 <= 0 or pivot <= 0:
        return None

    # Price must be above 20 EMA and above pivot
    if today["close"] < ema20 or today["close"] < pivot:
        return None

    # 20 EMA bounce or cross
    y_ema20 = yesterday.get("ema20", 0)
    crossed_above = (y_ema20 > 0 and yesterday["close"] < y_ema20 and today["close"] > ema20)
    bounced       = (today["low"] <= ema20 * 1.005 and today["close"] > ema20)
    if not (crossed_above or bounced):
        return None

    # MACD momentum rising
    if today.get("macd_hist", 0) <= yesterday.get("macd_hist", 0):
        return None

    entry = round(today["high"] + 0.05, 2)
    sl    = round(today["low"] - 0.05, 2)
    sl_pct = (entry - sl) / entry * 100

    if not (0.5 <= sl_pct <= 7.0):
        return None

    quality = 85 if sl_pct < 4.0 else 75

    return {
        "strategy":   "VT",
        "symbol":     symbol,
        "entry_price": entry,
        "stop_loss":  sl,
        "sl_pct":     round(sl_pct, 2),
        "quality_score": quality,
        "notes":      f"VT: 20 EMA {'cross' if crossed_above else 'bounce'}, MACD rising"
    }


def _position_size(entry: float, sl: float) -> dict:
    """Calculate shares and invested capital based on risk settings."""
    one_r = entry - sl
    if one_r <= 0:
        return {"shares": 0, "invested": 0, "risk_amount": 0, "one_r": 0}

    risk_amount = TRADING_CAPITAL * (RISK_PER_TRADE_PCT / 100)
    shares      = int(risk_amount / one_r)

    # Cap: don't invest more than full capital in one trade
    if shares * entry > TRADING_CAPITAL:
        shares = int(TRADING_CAPITAL / entry)

    if shares <= 0:
        return {"shares": 0, "invested": 0, "risk_amount": 0, "one_r": 0}

    return {
        "shares":      shares,
        "invested":    round(shares * entry, 2),
        "risk_amount": round(risk_amount, 2),
        "one_r":       round(one_r, 2),
    }


def _targets(entry: float, sl: float) -> dict:
    """Pre-calculate all exit price levels."""
    one_r = entry - sl
    return {
        "one_r":            round(one_r, 2),
        "breakeven_trigger": round(entry + 2 * one_r, 2),
        "partial_exit_1":   round(entry + 4 * one_r, 2),
        "two_r_price":      round(entry + 2 * one_r, 2),
        "four_r_price":     round(entry + 4 * one_r, 2),
        "six_r_price":      round(entry + 6 * one_r, 2),
        "ten_r_price":      round(entry + 10 * one_r, 2),
    }


def run_scan(api, progress_callback=None, strategy="DEP"):
    """
    Scan all stocks in the universe for the chosen strategy.

    Args:
        api:               GrowwAPI instance
        progress_callback: function(current, total, symbol) for UI progress
        strategy:          "DEP" or "VT"

    Returns:
        List of signal dicts (also saved to data/signals.json)
    """
    logger.info(f"Starting {strategy} scan over {len(STOCK_UNIVERSE)} stocks")

    # Market regime check (Nifty 50 above 20 EMA)
    if USE_MARKET_FILTER:
        try:
            raw_nifty = api.get_historical_data(
                "^NSEI",
                from_date=(datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d"),
                to_date=datetime.now().strftime("%Y-%m-%d")
            )
            if raw_nifty and len(raw_nifty) >= 20:
                nifty_df  = pd.DataFrame(raw_nifty)
                nifty_df.columns = [c.lower().strip() for c in nifty_df.columns]
                if "close" in nifty_df.columns:
                    nifty_df["ema20"] = nifty_df["close"].ewm(span=20, adjust=False).mean()
                    last_close = float(nifty_df["close"].iloc[-1])
                    last_ema20 = float(nifty_df["ema20"].iloc[-1])
                    if last_close < last_ema20:
                        logger.warning(f"MARKET FILTER: Nifty ({last_close:.0f}) < 20 EMA ({last_ema20:.0f}). Defensive mode.")
                        # Don't block — just warn. User decides.
        except Exception as e:
            logger.warning(f"Market regime check skipped: {e}")

    signals    = []
    total      = len(STOCK_UNIVERSE)
    start_date = (datetime.now() - timedelta(days=300)).strftime("%Y-%m-%d")
    end_date   = datetime.now().strftime("%Y-%m-%d")

    for i, symbol in enumerate(STOCK_UNIVERSE, 1):
        if progress_callback:
            progress_callback(i, total, symbol)

        try:
            raw = api.get_historical_data(symbol, from_date=start_date, to_date=end_date)
            if not raw or len(raw) < 50:
                logger.debug(f"{symbol}: insufficient data ({len(raw) if raw else 0} bars)")
                continue

            df = pd.DataFrame(raw)
            df.columns = [c.lower().strip() for c in df.columns]
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df.dropna(subset=["close", "high", "low", "volume"], inplace=True)
            df.reset_index(drop=True, inplace=True)

            if len(df) < 50:
                continue

            df = _build_indicators(df)

            # Run the selected strategy checker
            if strategy == "DEP":
                result = _check_dep(df, symbol)
            else:
                result = _check_vt(df, symbol)

            if result is None:
                logger.debug(f"{symbol}: no {strategy} setup today")
                continue

            if result["quality_score"] < MIN_QUALITY_SCORE:
                logger.debug(f"{symbol}: quality {result['quality_score']} < min {MIN_QUALITY_SCORE}")
                continue

            # Attach position sizing and targets
            pos  = _position_size(result["entry_price"], result["stop_loss"])
            tgts = _targets(result["entry_price"], result["stop_loss"])

            if pos["shares"] <= 0:
                logger.debug(f"{symbol}: 0 shares (capital too small or risk too tight)")
                continue

            result["shares"]      = pos["shares"]
            result["invested"]    = pos["invested"]
            result["risk_amount"] = pos["risk_amount"]
            result["targets"]     = tgts
            result["scan_date"]   = datetime.now().strftime("%Y-%m-%d")
            result["scan_time"]   = datetime.now().strftime("%H:%M:%S")

            # Extra chart data for the frontend
            result["pullback_pct"] = round(
                (df["high"].iloc[-30:].max() - df["close"].iloc[-1]) / df["high"].iloc[-30:].max() * 100, 1
            ) if len(df) >= 30 else 0
            result["vol_ratio"]    = round(
                float(df["volume"].iloc[-1]) / float(df["vol_sma20"].iloc[-1]), 2
            ) if df["vol_sma20"].iloc[-1] > 0 else 1.0

            signals.append(result)
            logger.info(f"✓ {strategy} SIGNAL: {symbol} | Entry Rs{result['entry_price']} | SL {result['sl_pct']}% | Q{result['quality_score']}")

        except Exception as e:
            logger.error(f"Error scanning {symbol}: {e}")

        time.sleep(0.2)   # gentle rate limiting

    # Sort best quality first
    signals.sort(key=lambda s: s["quality_score"], reverse=True)

    os.makedirs(os.path.dirname(SIGNALS_DB), exist_ok=True)
    with open(SIGNALS_DB, "w", encoding="utf-8") as f:
        json.dump(signals, f, indent=2, default=str)

    logger.info(f"Scan complete: {len(signals)} signals from {total} stocks")
    return signals


def load_signals():
    if not os.path.exists(SIGNALS_DB):
        return []
    try:
        with open(SIGNALS_DB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


# Import guard — must be after all defs
from config import USE_MARKET_FILTER