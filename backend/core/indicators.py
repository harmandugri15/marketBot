"""
core/indicators.py
------------------
Pure Python / pandas technical indicator calculations.
No API calls, no side effects — just math.
All functions take a DataFrame with columns: open, high, low, close, volume.
"""

import pandas as pd
import numpy as np


# ── Moving Averages ───────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    """Add EMA-10, EMA-20, EMA-50, EMA-200 columns."""
    df = df.copy()
    df["ema10"]  = ema(df["close"], 10)
    df["ema20"]  = ema(df["close"], 20)
    df["ema50"]  = ema(df["close"], 50)
    df["ema200"] = ema(df["close"], 200)
    return df


# ── RSI ───────────────────────────────────────────────────────────────────────

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Wilder RSI using EMA-based smoothing."""
    delta = series.diff()
    gain  = delta.where(delta > 0, 0).ewm(alpha=1 / period, adjust=False).mean()
    loss  = (-delta.where(delta < 0, 0)).ewm(alpha=1 / period, adjust=False).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


# ── MACD ──────────────────────────────────────────────────────────────────────

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """Returns DataFrame with macd_line, signal_line, histogram."""
    fast_ema   = ema(series, fast)
    slow_ema   = ema(series, slow)
    macd_line  = fast_ema - slow_ema
    signal_line = ema(macd_line, signal)
    return pd.DataFrame({
        "macd_line":   macd_line,
        "signal_line": signal_line,
        "histogram":   macd_line - signal_line,
    })


# ── Volume ────────────────────────────────────────────────────────────────────

def add_volume_analysis(df: pd.DataFrame, period: int = 50) -> pd.DataFrame:
    """Add vol_sma50 and vol_ratio columns."""
    df = df.copy()
    df["vol_sma50"] = sma(df["volume"], period)
    df["vol_ratio"] = df["volume"] / df["vol_sma50"]
    return df


# ── VWAP (Intraday) ───────────────────────────────────────────────────────────

def vwap(df: pd.DataFrame) -> pd.Series:
    """Volume-Weighted Average Price for intraday data."""
    typical = (df["high"] + df["low"] + df["close"]) / 3
    return (typical * df["volume"]).cumsum() / df["volume"].cumsum()


# ── ATR ───────────────────────────────────────────────────────────────────────

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range."""
    high_low   = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift()).abs()
    low_close  = (df["low"]  - df["close"].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return sma(tr, period)


# ── Stage 2 Detection ─────────────────────────────────────────────────────────

def is_stage2(df: pd.DataFrame) -> bool:
    """
    Mark Minervini / Vijay Thakkar Stage 2 criteria:
    1. Price above 200 EMA
    2. 200 EMA is rising (higher than 20 days ago)
    3. Price at least 10% above where it was ~6 months ago (125 trading days)
    """
    if len(df) < 200 or "ema200" not in df.columns:
        return False

    last        = df.iloc[-1]
    ema200_now  = last["ema200"]
    ema200_prev = df.iloc[-20]["ema200"]

    if last["close"] < ema200_now:
        return False
    if ema200_now <= ema200_prev:
        return False
    if len(df) >= 125:
        if last["close"] < df.iloc[-125]["close"] * 1.10:
            return False
    return True


# ── Pullback Analysis ─────────────────────────────────────────────────────────

def analyze_pullback(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    Analyze pullback from recent high.
    Returns dict with is_valid, pullback_pct, is_orderly, days_in_pullback.
    """
    window     = df.tail(lookback)
    high_price = window["high"].max()
    high_idx   = window["high"].idxmax()
    current    = df.iloc[-1]["close"]

    if high_price == 0:
        return {"is_valid": False, "pullback_pct": 0, "is_orderly": False}

    pullback_pct     = (high_price - current) / high_price * 100
    days_in_pullback = len(df) - df.index.get_loc(high_idx) if high_idx in df.index else 0

    # Valid pullback: 5–25%
    is_valid = 5.0 <= pullback_pct <= 25.0

    # Orderly: no single day dropped more than 7%
    post_high   = df.loc[high_idx:] if high_idx in df.index else df.tail(10)
    daily_drops = post_high["close"].pct_change().abs() * 100
    is_orderly  = bool(daily_drops.max() < 7.0)

    return {
        "is_valid":        is_valid,
        "pullback_pct":    round(pullback_pct, 2),
        "is_orderly":      is_orderly,
        "high_price":      round(high_price, 2),
        "current_price":   round(current, 2),
        "days_in_pullback": days_in_pullback,
    }


# ── VCP Pattern Detection ─────────────────────────────────────────────────────

def detect_vcp(df: pd.DataFrame, vol_mult: float = 1.5, expansion_pct: float = 4.0) -> dict:
    """
    Volatility Contraction Pattern (Vijay Thakkar / Minervini):
    Looks for:
    1. Stock in Stage 2
    2. Valid orderly pullback (5–25%)
    3. Volume drying up (today vol < 50% of 50-day avg)
    4. Volume expansion on signal day (> vol_mult * avg)
    5. Price expansion above yesterday high
    Returns: dict with passed (bool), score (0–100), and details.
    """
    result = {
        "passed":       False,
        "score":        0,
        "stage2":       False,
        "pullback":     {},
        "vol_contraction": False,
        "vol_expansion":   False,
        "price_expansion": False,
        "entry":        None,
        "stop_loss":    None,
        "target":       None,
    }

    if len(df) < 60:
        return result

    df = add_emas(df)
    df = add_volume_analysis(df)

    stage2 = is_stage2(df)
    result["stage2"] = stage2

    pb = analyze_pullback(df)
    result["pullback"] = pb

    last = df.iloc[-1]
    prev = df.iloc[-2]

    vol_contraction = bool(prev["vol_ratio"] < 0.8)
    vol_expansion   = bool(last["vol_ratio"] > vol_mult)
    price_expansion = bool(last["close"] > prev["close"] * (1 + (expansion_pct / 2) / 100))

    result["vol_contraction"] = vol_contraction
    result["vol_expansion"]   = vol_expansion
    result["price_expansion"] = price_expansion

    score = 0
    if stage2:            score += 30
    if pb["is_valid"]:    score += 25
    if pb["is_orderly"]:  score += 15
    if vol_contraction:   score += 15
    if vol_expansion:     score += 10
    if price_expansion:   score += 5

    result["score"] = score
    result["passed"] = score >= 70

    if result["passed"]:
        entry     = round(last["close"] * 1.002, 2)
        stop_loss = round(last["close"] * (1 - min(pb["pullback_pct"] / 100, 0.12)), 2)
        risk      = entry - stop_loss
        target    = round(entry + (risk * 3), 2)

        result["entry"]     = entry
        result["stop_loss"] = stop_loss
        result["target"]    = target

    return result


# ── Market Regime ─────────────────────────────────────────────────────────────

def get_market_regime(nifty_df: pd.DataFrame) -> str:
    """
    Returns BULL / CASH / PANIC based on Nifty 50.
    BULL: price above 20 EMA
    CASH: between 20 and 200 EMA
    PANIC: below 200 EMA — stop all trading
    """
    if nifty_df is None or len(nifty_df) < 10:
        return "CASH"

    df = add_emas(nifty_df)
    last = df.iloc[-1]

    if last["close"] > last["ema20"]:
        return "BULL"
    if last["close"] < last["ema200"]:
        return "PANIC"
    return "CASH"


# ── Position Sizing ───────────────────────────────────────────────────────────

def calculate_position_size(
    capital: float,
    risk_pct: float,
    entry: float,
    stop_loss: float,
) -> dict:
    """
    Returns quantity and capital_deployed for a trade.
    risk_pct = % of total capital risked on this trade (e.g. 1.0 = 1%)
    """
    risk_amount = capital * (risk_pct / 100)
    risk_per_share = entry - stop_loss
    if risk_per_share <= 0:
        return {"quantity": 0, "capital_deployed": 0}

    quantity = int(risk_amount / risk_per_share)
    capital_deployed = round(quantity * entry, 2)

    return {
        "quantity":         quantity,
        "capital_deployed": capital_deployed,
        "risk_amount":      round(risk_amount, 2),
        "risk_per_share":   round(risk_per_share, 2),
    }


# ── Swing Pullback (HARMAN1_PULLBACK) ─────────────────────────────────────────

def detect_swing_pullback(df: pd.DataFrame) -> dict:
    """
    HARMAN1_PULLBACK Swing Strategy:
    1. Distance to EMA20 is 0-4% (0 < (close - ema20)/ema20 < 0.04)
    2. RSI(14) is 40-65
    3. Stop loss is max(min(low * 0.99, entry * 0.95), entry * 0.92)
    4. Target is 3R
    """
    res = {
        "passed": False,
        "score": 0,
        "entry": None,
        "stop_loss": None,
        "target": None,
        "rsi": None,
        "dist": None,
    }
    if len(df) < 20:
        return res

    df = df.copy()
    if "ema20" not in df.columns:
        df["ema20"] = ema(df["close"], 20)
    if "rsi" not in df.columns:
        df["rsi"] = rsi(df["close"], 14)

    today = df.iloc[-1]
    dist = (today["close"] - today["ema20"]) / today["ema20"]

    res["rsi"] = float(today["rsi"])
    res["dist"] = float(dist)

    if 0 < dist < 0.04 and 40 < today["rsi"] < 65:
        entry = float(today["close"])
        sl = float(max(min(today["low"] * 0.99, entry * 0.95), entry * 0.92))
        one_r = entry - sl
        if one_r > 0:
            res["passed"] = True
            res["score"] = 90  # default high score for meeting criteria
            res["entry"] = round(entry, 2)
            res["stop_loss"] = round(sl, 2)
            res["target"] = round(entry + (3 * one_r), 2)

    return res


# ── Intraday VWAP Bounce (VWAP_RUNNER) ────────────────────────────────────────

def detect_vwap_bounce(df: pd.DataFrame) -> dict:
    """
    VWAP_RUNNER Intraday Strategy:
    1. Timeframe: 5-minute candles
    2. Price is above today's open (close > day_open)
    3. Previous low is very close to VWAP (abs(prev_low - prev_vwap)/prev_vwap < 0.002)
    4. Current candle is green (close > open)
    5. Stop loss is current_vwap * 0.998
    6. Max SL width is 1.5% (one_r / entry < 0.015)
    """
    res = {
        "passed": False,
        "score": 0,
        "entry": None,
        "stop_loss": None,
        "target": None,
        "distance_to_vwap": None,
    }
    if len(df) < 5:
        return res

    df = df.copy()
    if "vwap" not in df.columns:
        typical_price = (df["high"] + df["low"] + df["close"]) / 3
        # Volume-Weighted Average Price
        # Cumulative typical price * volume divided by cumulative volume
        df["vwap"] = (typical_price * df["volume"]).cumsum() / df["volume"].cumsum()

    day_open = df.iloc[0]["open"]
    curr_candle = df.iloc[-1]
    prev_candle = df.iloc[-2]

    curr_vwap = curr_candle["vwap"]
    prev_vwap = prev_candle["vwap"]

    distance_to_vwap = abs(prev_candle["low"] - prev_vwap) / prev_vwap
    res["distance_to_vwap"] = float(distance_to_vwap)

    if curr_candle["close"] > day_open and distance_to_vwap < 0.002:
        if curr_candle["close"] > curr_candle["open"]:
            entry = float(curr_candle["close"])
            sl = float(curr_vwap * 0.998)
            one_r = entry - sl
            if one_r > 0 and (one_r / entry * 100) < 1.5:
                res["passed"] = True
                res["score"] = 90
                res["entry"] = round(entry, 2)
                res["stop_loss"] = round(sl, 2)
                res["target"] = round(entry + (3 * one_r), 2)  # default target

    return res
