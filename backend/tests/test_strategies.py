import pytest
import pandas as pd
import numpy as np
from core.indicators import detect_swing_pullback, detect_vwap_bounce

def test_detect_swing_pullback():
    dates = pd.date_range(end="2026-06-14", periods=30)
    df = pd.DataFrame({
        "close": [100.0] * 30,
        "open": [100.0] * 30,
        "high": [101.0] * 30,
        "low": [99.0] * 30,
        "volume": [1000] * 30,
    }, index=dates)

    df["close"] = [100.0 + i * 0.5 for i in range(30)]
    df["open"] = df["close"] - 0.2
    df["high"] = df["close"] + 0.3
    df["low"] = df["close"] - 0.4

    df.loc[df.index[-1], "close"] = 110.0
    df.loc[df.index[-1], "low"] = 109.0
    df.loc[df.index[-1], "high"] = 111.0

    res = detect_swing_pullback(df)
    assert isinstance(res, dict)
    assert "passed" in res

def test_detect_vwap_bounce():
    df = pd.DataFrame({
        "open": [100.0] * 10,
        "high": [101.0] * 10,
        "low": [99.0] * 10,
        "close": [100.5] * 10,
        "volume": [1000] * 10,
        "time": ["09:15:00", "09:20:00", "09:25:00", "09:30:00", "09:35:00", "09:40:00", "09:45:00", "09:50:00", "09:55:00", "10:00:00"],
    })

    res = detect_vwap_bounce(df)
    assert isinstance(res, dict)
    assert "passed" in res