"""
indicators.py
-------------
Pure Python / pandas calculations for all technical indicators
used by the VCP strategy. No API calls here — just math.

All functions take a pandas DataFrame with columns:
    date, open, high, low, close, volume
and return either a Series or a scalar value.
"""

import pandas as pd
import numpy as np


# ── Moving Averages ───────────────────────────────────────────────────────────

def ema(series: pd.Series, period: int) -> pd.Series:
    """
    Exponential Moving Average.
    Uses the standard formula: multiplier = 2 / (period + 1)
    """
    return series.ewm(span=period, adjust=False).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def add_emas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add EMA-10, EMA-20, and EMA-200 columns to the DataFrame.
    These are the three EMAs used in the VCP strategy.
    """
    df = df.copy()
    df["ema10"]  = ema(df["close"], 10)
    df["ema20"]  = ema(df["close"], 20)
    df["ema200"] = ema(df["close"], 200)
    return df


# ── Volume Analysis ───────────────────────────────────────────────────────────

def volume_sma(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """20-day average volume — used as the baseline for volume analysis."""
    return sma(df["volume"], period)


def add_volume_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add volume indicators:
      - vol_sma20:  20-day average volume
      - vol_ratio:  today's volume as a fraction of the 20-day average
                    e.g. 0.4 means volume dried up to 40% of average
    """
    df = df.copy()
    df["vol_sma20"] = volume_sma(df)
    df["vol_ratio"] = df["volume"] / df["vol_sma20"]
    return df


# ── Stage 2 Detection ─────────────────────────────────────────────────────────

def is_stage2(df: pd.DataFrame) -> bool:
    """
    Determine if a stock is in Stage 2 (Mark Minervini / Vijay Thakkar definition).

    Stage 2 requires:
      1. Price is above the 200-day EMA
      2. The 200-day EMA is rising (sloping upward)
      3. The stock had a clear prior uptrend (price well above where it was 6 months ago)

    Needs at least 200 rows of data.
    Returns True / False.
    """
    if len(df) < 200:
        return False

    last = df.iloc[-1]
    ema200_now  = last["ema200"]
    ema200_prev = df.iloc[-20]["ema200"]   # 20 days ago

    # Rule 1: price above 200 EMA
    if last["close"] < ema200_now:
        return False

    # Rule 2: 200 EMA must be rising (higher now than 20 days ago)
    if ema200_now <= ema200_prev:
        return False

    # Rule 3: stock is higher than it was ~6 months ago (approx 125 trading days)
    if len(df) >= 125:
        price_6m_ago = df.iloc[-125]["close"]
        if last["close"] < price_6m_ago * 1.10:   # at least 10% higher
            return False

    return True


# ── Pullback Analysis ─────────────────────────────────────────────────────────

def find_recent_high(df: pd.DataFrame, lookback: int = 60) -> tuple:
    """
    Find the most recent significant high within the last `lookback` trading days.

    Returns: (high_price, high_index) — the price and row index of the high.
    """
    window = df.tail(lookback)
    idx    = window["high"].idxmax()
    return df.loc[idx, "high"], idx


def analyze_pullback(df: pd.DataFrame, lookback: int = 60) -> dict:
    """
    Analyze the pullback from the recent high.

    Returns a dict with:
        is_valid:        True if pullback depth is within 12-20%
        pullback_pct:    actual pullback % from high
        is_orderly:      True if the drop was not a hard/fast crash
        high_price:      the recent high price
        current_price:   the latest closing price
        days_in_pullback: how many days since the high
    """
    result = {
        "is_valid":        False,
        "pullback_pct":    0,
        "is_orderly":      False,
        "high_price":      0,
        "current_price":   0,
        "days_in_pullback": 0
    }

    if len(df) < 30:
        return result

    high_price, high_idx = find_recent_high(df, lookback)
    current_price = df.iloc[-1]["close"]
    result["high_price"]    = round(high_price, 2)
    result["current_price"] = round(current_price, 2)

    # Pullback percentage from high to current price
    pullback_pct = (high_price - current_price) / high_price * 100
    result["pullback_pct"] = round(pullback_pct, 2)

    # How many days since the high?
    high_pos = df.index.get_loc(high_idx)
    days_in_pullback = len(df) - 1 - high_pos
    result["days_in_pullback"] = days_in_pullback

    # Rule: pullback must be between 12% and 20%
    from config import PULLBACK_MIN_PCT, PULLBACK_MAX_PCT, PULLBACK_MAX_DAYS, HARD_PULLBACK_3DAY
    if not (PULLBACK_MIN_PCT <= pullback_pct <= PULLBACK_MAX_PCT):
        return result
    result["is_valid"] = True

    # Orderly pullback check: no single 3-day window should drop more than 20%
    since_high = df.iloc[high_pos:]
    if len(since_high) >= 3:
        for i in range(len(since_high) - 2):
            three_day_high = since_high.iloc[i]["high"]
            three_day_low  = since_high.iloc[i+2]["low"]
            if three_day_high > 0:
                three_day_drop = (three_day_high - three_day_low) / three_day_high * 100
                if three_day_drop > HARD_PULLBACK_3DAY:
                    result["is_orderly"] = False
                    return result

    result["is_orderly"] = True
    return result


# ── Volume Contraction Check ──────────────────────────────────────────────────

def check_volume_contraction(df: pd.DataFrame, pullback_start_idx: int) -> dict:
    """
    Check if volume has dried up during the pullback.

    During a valid VCP pullback, volume should decrease as the stock pulls back —
    showing that sellers are exhausted, not panicking.

    Returns dict with:
        is_contracting: True if volume is below the required threshold
        avg_vol_during_pullback: average volume since the high
        baseline_vol:   20-day average volume before the high
        vol_ratio:      ratio (lower = more contraction)
    """
    from config import VOLUME_DRY_UP_PCT

    result = {
        "is_contracting":        False,
        "avg_vol_during_pullback": 0,
        "baseline_vol":          0,
        "vol_ratio":             1.0
    }

    if pullback_start_idx <= 0 or len(df) < 25:
        return result

    # Baseline volume = average of 20 days BEFORE the high
    pre_high = df.iloc[max(0, pullback_start_idx - 20): pullback_start_idx]
    pullback_period = df.iloc[pullback_start_idx:]

    if pre_high.empty or pullback_period.empty:
        return result

    baseline_vol = pre_high["volume"].mean()
    pullback_vol = pullback_period["volume"].mean()

    if baseline_vol == 0:
        return result

    vol_ratio = pullback_vol / baseline_vol
    result["baseline_vol"]           = round(baseline_vol)
    result["avg_vol_during_pullback"] = round(pullback_vol)
    result["vol_ratio"]              = round(vol_ratio, 2)

    # Volume must drop by at least VOLUME_DRY_UP_PCT% from baseline
    required_ratio = 1 - (VOLUME_DRY_UP_PCT / 100)
    result["is_contracting"] = vol_ratio <= required_ratio

    return result


# ── Inside Bar (Mother Candle) Detection ──────────────────────────────────────

def find_inside_bar(df: pd.DataFrame) -> dict:
    """
    Find an Inside Bar (Mother Candle) pattern in the last few candles.

    An Inside Bar is a candle whose HIGH and LOW are both within
    the range of the PREVIOUS candle (the Mother Candle).

    This is the final contraction signal before the breakout.

    Returns dict with:
        found:         True if inside bar exists
        mother_high:   high of the mother candle (= entry price trigger)
        mother_low:    low of the mother candle (= stop loss area)
        prev_day_low:  low of the day before inside bar (actual SL)
        inside_bar_date: date of the inside bar candle
        near_ema:      True if inside bar is within 3% of 10 or 20 EMA
    """
    from config import EMA_PROXIMITY_PCT

    result = {
        "found":          False,
        "mother_high":    0,
        "mother_low":     0,
        "prev_day_low":   0,
        "inside_bar_date": None,
        "near_ema":       False
    }

    if len(df) < 3:
        return result

    # Check the last 5 candles for any inside bar
    for i in range(-1, -6, -1):
        if abs(i) >= len(df):
            break
        curr = df.iloc[i]
        prev = df.iloc[i - 1]   # the mother candle

        # Inside bar condition: current candle HIGH <= mother HIGH
        #                   AND current candle LOW  >= mother LOW
        if curr["high"] <= prev["high"] and curr["low"] >= prev["low"]:
            result["found"]        = True
            result["mother_high"]  = round(prev["high"], 2)
            result["mother_low"]   = round(prev["low"], 2)
            result["inside_bar_date"] = str(curr.name)[:10] if hasattr(curr, "name") else ""

            # Previous day low = the low of the day BEFORE the mother candle (= stop loss)
            if abs(i) + 1 < len(df):
                result["prev_day_low"] = round(df.iloc[i - 2]["low"], 2)
            else:
                result["prev_day_low"] = round(prev["low"], 2)

            # Check if inside bar is near 10 or 20 EMA
            close = curr["close"]
            ema10_val = curr.get("ema10", 0)
            ema20_val = curr.get("ema20", 0)

            near_10 = (abs(close - ema10_val) / ema10_val * 100 <= EMA_PROXIMITY_PCT) if ema10_val else False
            near_20 = (abs(close - ema20_val) / ema20_val * 100 <= EMA_PROXIMITY_PCT) if ema20_val else False
            result["near_ema"] = near_10 or near_20

            break

    return result


# ── Entry & Stop Loss Calculation ─────────────────────────────────────────────

def calculate_entry_and_sl(mother_high: float, prev_day_low: float,
                            current_price: float) -> dict:
    """
    Calculate exact entry price, stop loss, and position sizing info.

    Entry:     high of the mother candle (buy on breakout above this)
    Stop Loss: previous day low — but capped at MAX_STOP_LOSS_PCT from entry

    Returns dict with:
        entry_price:   where to place the buy order (limit order)
        stop_loss:     where to set the initial stop loss
        sl_pct:        stop loss % from entry
        is_valid:      False if SL > max allowed %
        risk_per_share: entry - stop_loss
    """
    from config import MAX_STOP_LOSS_PCT

    entry_price = mother_high
    stop_loss   = prev_day_low

    if entry_price <= 0:
        return {"is_valid": False}

    sl_pct = (entry_price - stop_loss) / entry_price * 100

    # If SL is larger than the maximum allowed, the trade is invalid
    is_valid = sl_pct <= MAX_STOP_LOSS_PCT

    return {
        "entry_price":    round(entry_price, 2),
        "stop_loss":      round(stop_loss, 2),
        "sl_pct":         round(sl_pct, 2),
        "is_valid":       is_valid,
        "risk_per_share": round(entry_price - stop_loss, 2)
    }


def calculate_position_size(entry_price: float, stop_loss: float,
                              capital: float) -> dict:
    """
    Calculate how many shares to buy.

    Formula: position_size = (capital * risk_pct) / risk_per_share
    This ensures we never lose more than risk_pct% of our capital on one trade.

    Returns dict with:
        shares:        number of shares to buy (rounded down)
        invested:      total money deployed
        risk_amount:   max loss in rupees if SL is hit
        risk_pct:      actual % of capital at risk
    """
    from config import RISK_PER_TRADE_PCT

    risk_per_share = entry_price - stop_loss
    if risk_per_share <= 0:
        return {"shares": 0, "invested": 0, "risk_amount": 0, "risk_pct": 0}

    risk_amount = capital * (RISK_PER_TRADE_PCT / 100)
    shares      = int(risk_amount / risk_per_share)

    if shares <= 0:
        return {"shares": 0, "invested": 0, "risk_amount": 0, "risk_pct": 0}

    invested = round(shares * entry_price, 2)
    return {
        "shares":      shares,
        "invested":    invested,
        "risk_amount": round(risk_amount, 2),
        "risk_pct":    RISK_PER_TRADE_PCT
    }


# ── Exit Price Calculations ───────────────────────────────────────────────────

def calculate_exit_targets(entry_price: float, stop_loss: float) -> dict:
    """
    Pre-calculate all exit price levels based on the strategy rules.

    1R = risk per share (entry - stop_loss)
    2R = break-even trigger (move SL to entry)
    4R = first partial exit (sell 1/3)

    Returns dict of all key price levels.
    """
    one_r = entry_price - stop_loss

    return {
        "one_r":         round(one_r, 2),
        "breakeven_trigger": round(entry_price + (2 * one_r), 2),   # at this price, SL moves to entry
        "partial_exit_1":    round(entry_price + (4 * one_r), 2),   # sell 1/3 here
        "two_r_price":       round(entry_price + (2 * one_r), 2),
        "four_r_price":      round(entry_price + (4 * one_r), 2),
        "six_r_price":       round(entry_price + (6 * one_r), 2),
        "ten_r_price":       round(entry_price + (10 * one_r), 2),
    }


# ── Index Filter ──────────────────────────────────────────────────────────────

def check_index_filter(index_df: pd.DataFrame) -> dict:
    """
    Check if the market is in a condition to trade (index filter).

    Rule: BSE Smallcap 100 must be ABOVE its 10-day EMA.
    If below → be defensive, don't enter new trades.

    Returns dict with:
        is_bullish:  True if index > 10 EMA (safe to trade)
        index_value: current index level
        ema10_value: current 10-day EMA of index
        gap_pct:     how far above/below EMA the index is
    """
    if len(index_df) < 10:
        return {"is_bullish": False, "index_value": 0, "ema10_value": 0, "gap_pct": 0}

    index_df = index_df.copy()
    index_df["ema10"] = ema(index_df["close"], 10)

    last = index_df.iloc[-1]
    index_val = last["close"]
    ema10_val = last["ema10"]

    gap_pct = (index_val - ema10_val) / ema10_val * 100

    return {
        "is_bullish":  index_val > ema10_val,
        "index_value": round(index_val, 2),
        "ema10_value": round(ema10_val, 2),
        "gap_pct":     round(gap_pct, 2)
    }
