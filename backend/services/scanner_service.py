"""
services/scanner_service.py
----------------------------
Orchestrates the daily VCP scan across the stock universe.
Writes results to the database, not JSON files.
Supports progress streaming via a callback.
"""

import logging
import time
import random
import concurrent.futures
from datetime import datetime, timedelta, date

import pandas as pd
from sqlalchemy.orm import Session

from config import get_settings, STOCK_UNIVERSE
from core.indicators import detect_vcp, get_market_regime, add_emas
from core.groww_client import GrowwClient
from models.signal import Signal
from schemas.signal import SignalCreate

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_nifty_regime(client: GrowwClient) -> str:
    """Fetch Nifty 50 data and determine market regime."""
    try:
        from_date = (datetime.now() - timedelta(days=350)).strftime("%Y-%m-%d")
        to_date   = datetime.now().strftime("%Y-%m-%d")
        raw       = client.get_historical_data("^NSEI", from_date, to_date)
        if not raw:
            return "CASH"
        df = pd.DataFrame(raw)
        df = add_emas(df)
        return get_market_regime(df)
    except Exception as e:
        logger.error(f"Market regime check failed: {e}")
        return "CASH"


def _fetch_and_analyse(
    symbol: str,
    client: GrowwClient,
    regime: str,
    strategy: str = "AUTO",
) -> dict | None:
    """
    Fetch OHLCV data for one symbol, run chosen strategy detection.
    Returns a signal dict or None if no setup found.
    """
    time.sleep(random.uniform(0.3, 0.8))   # jitter to avoid burst calls

    active_strategy = strategy
    if active_strategy == "AUTO":
        active_strategy = "VCP"

    try:
        if active_strategy in ["VWAP_RUNNER", "INTRADAY"]:
            # Fetch last 3 days of 5m candles to ensure we have today's candles safely
            from_date = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            to_date   = datetime.now().strftime("%Y-%m-%d")
            raw = client.get_historical_intraday_data(symbol, from_date, to_date)
            if not raw or len(raw) < 5:
                return None

            df = pd.DataFrame(raw)
            df["close"]  = pd.to_numeric(df["close"], errors="coerce")
            df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
            df["high"]   = pd.to_numeric(df["high"], errors="coerce")
            df["low"]    = pd.to_numeric(df["low"], errors="coerce")
            df["open"]   = pd.to_numeric(df["open"], errors="coerce")
            df = df.dropna(subset=["close"])

            from core.indicators import detect_vwap_bounce
            result = detect_vwap_bounce(df)
            if not result["passed"]:
                return None

            last = df.iloc[-1]
            return {
                "symbol":       symbol,
                "strategy":     "VWAP_RUNNER",
                "close":        float(last["close"]),
                "entry":        result["entry"],
                "stop_loss":    result["stop_loss"],
                "target":       result["target"],
                "quality":      result["score"],
                "rsi":          None,
                "vol_ratio":    None,
                "pullback_pct": None,
                "market_regime": regime,
            }

        elif active_strategy in ["HARMAN1_PULLBACK", "SWING"]:
            from_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
            to_date   = datetime.now().strftime("%Y-%m-%d")
            raw = client.get_historical_data(symbol, from_date, to_date)
            if not raw or len(raw) < 20:
                return None

            df = pd.DataFrame(raw)
            df["close"]  = pd.to_numeric(df["close"], errors="coerce")
            df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
            df["high"]   = pd.to_numeric(df["high"], errors="coerce")
            df["low"]    = pd.to_numeric(df["low"], errors="coerce")
            df = df.dropna(subset=["close"])

            from core.indicators import detect_swing_pullback
            result = detect_swing_pullback(df)
            if not result["passed"]:
                return None

            last = df.iloc[-1]
            return {
                "symbol":       symbol,
                "strategy":     "HARMAN1_PULLBACK",
                "close":        float(last["close"]),
                "entry":        result["entry"],
                "stop_loss":    result["stop_loss"],
                "target":       result["target"],
                "quality":      result["score"],
                "rsi":          result["rsi"],
                "vol_ratio":    None,
                "pullback_pct": result["dist"] * 100 if result["dist"] is not None else None,
                "market_regime": regime,
            }

        else: # Default: VCP
            from_date = (datetime.now() - timedelta(days=260)).strftime("%Y-%m-%d")
            to_date   = datetime.now().strftime("%Y-%m-%d")
            raw = client.get_historical_data(symbol, from_date, to_date)
            if not raw or len(raw) < 100:
                return None

            df = pd.DataFrame(raw)
            df["close"]  = pd.to_numeric(df["close"], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")
            df = df.dropna(subset=["close", "volume"])

            result = detect_vcp(df, settings.vol_mult, settings.expansion_pct)

            if not result["passed"] or result["score"] < settings.min_quality:
                return None

            last = df.iloc[-1]
            return {
                "symbol":       symbol,
                "strategy":     "VCP",
                "close":        float(last["close"]),
                "entry":        result["entry"],
                "stop_loss":    result["stop_loss"],
                "target":       result["target"],
                "quality":      result["score"],
                "rsi":          float(df.iloc[-1].get("rsi", 0)) if "rsi" in df.columns else None,
                "vol_ratio":    result["pullback"].get("vol_ratio"),
                "pullback_pct": result["pullback"].get("pullback_pct"),
                "market_regime": regime,
            }
    except Exception as e:
        logger.warning(f"Error scanning {symbol}: {e}")
        return None


def run_scan(
    db: Session,
    client: GrowwClient,
    strategy: str = "AUTO",
    progress_callback=None,
    symbols: list[str] | None = None,
) -> list[dict]:
    """
    Main scan function — scans all symbols, saves signals to DB.
    Returns list of signal dicts.
    """
    symbols = symbols or STOCK_UNIVERSE
    regime  = _get_nifty_regime(client)

    logger.info(f"Starting scan | regime={regime} | symbols={len(symbols)} | strategy={strategy}")

    if regime == "PANIC":
        logger.warning("MARKET PANIC — circuit breaker active. Scan aborted.")
        return []

    signals = []
    total   = len(symbols)

    # Deactivate old signals of this strategy from today
    today_start = datetime.combine(date.today(), datetime.min.time())
    active_strat = strategy if strategy != "AUTO" else "VCP"
    db.query(Signal).filter(
        Signal.scan_date >= today_start,
        Signal.strategy == active_strat
    ).update({"is_active": False})
    db.commit()

    def _worker(args):
        idx, symbol = args
        if progress_callback:
            progress_callback(idx, total, symbol)
        return _fetch_and_analyse(symbol, client, regime, strategy)

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(_worker, enumerate(symbols, 1)))

    for sig_data in results:
        if sig_data is None:
            continue
        db_signal = Signal(**sig_data)
        db.add(db_signal)
        signals.append(sig_data)

    db.commit()
    logger.info(f"Scan complete — {len(signals)} signals found")
    return signals


def get_latest_signals(db: Session, limit: int = 50, strategy: str = None) -> list[Signal]:
    """Return most recent active signals."""
    q = db.query(Signal).filter(Signal.is_active == True)
    if strategy:
        q = q.filter(Signal.strategy == strategy)
    return (
        q.order_by(Signal.quality.desc(), Signal.scan_date.desc())
        .limit(limit)
        .all()
    )
