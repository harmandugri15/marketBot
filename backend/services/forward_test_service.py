"""
services/forward_test_service.py
---------------------------------
Forward testing service — logs real-time signals and tracks their
P&L over time WITHOUT placing real orders. This is the bridge
between paper trading and going live.

Each day's log shows:
- What signals were generated
- What prices they hit (SL / target / neither)
- Running cumulative P&L if you had followed every signal

Analyze this for 4–8 weeks before switching to live mode.
"""

import logging
from datetime import date, datetime, timezone
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from config import get_settings
from core.groww_client import GrowwClient
from core.indicators import calculate_position_size
from models.user import User
from models.forward_test_log import ForwardTestLog
from models.trade import Trade, TradeMode, TradeStatus

logger = logging.getLogger(__name__)
settings = get_settings()


def log_daily_signals(
    db: Session,
    user: User,
    client: GrowwClient,
    signals: list[dict],
    regime: str,
    nifty_close: Optional[float] = None,
) -> ForwardTestLog:
    """
    Create a daily forward test log entry for today's signals.
    Also auto-opens paper trades for each signal.
    """
    today = date.today()

    # Get or create today's log for this user
    existing = db.query(ForwardTestLog).filter(
        ForwardTestLog.log_date == today,
        ForwardTestLog.user_id == user.id
    ).first()

    if existing:
        log = existing
    else:
        log = ForwardTestLog(
            user_id      = user.id,
            log_date     = today,
            strategy     = "VCP",
            market_regime = regime,
            nifty_close  = nifty_close,
        )
        db.add(log)

    log.signals_count = len(signals)
    log.signals       = signals

    # Auto-open paper/forward trades for each signal
    trades_entered = 0
    for sig in signals[:settings.max_trades_per_day]:   # cap per day
        pos = calculate_position_size(
            capital   = user.capital,
            risk_pct  = user.risk_pct,
            entry     = sig["entry"],
            stop_loss = sig["stop_loss"],
        )
        if pos["quantity"] < 1:
            continue

        trade = Trade(
            user_id          = user.id,
            symbol           = sig["symbol"],
            strategy         = sig.get("strategy", "VCP"),
            mode             = TradeMode.forward,
            status           = TradeStatus.open,
            entry_price      = sig["entry"],
            quantity         = pos["quantity"],
            stop_loss        = sig["stop_loss"],
            target           = sig.get("target"),
            capital_deployed = pos["capital_deployed"],
        )
        db.add(trade)
        trades_entered += 1

    log.trades_entered = trades_entered
    db.commit()
    db.refresh(log)
    logger.info(f"Forward test log for {today} (User {user.username}): {len(signals)} signals, {trades_entered} trades entered")
    return log


def update_open_forward_trades(db: Session, user: User, client: GrowwClient) -> dict:
    """
    For each open forward-test trade, check if today's price
    hit the stop-loss or target, and close accordingly.
    Run this once per day after market close.
    """
    open_trades = (
        db.query(Trade)
        .filter(
            Trade.user_id == user.id,
            Trade.mode == TradeMode.forward,
            Trade.status == TradeStatus.open
        )
        .all()
    )

    closed_today = 0
    pnl_today    = 0.0

    for trade in open_trades:
        ltp = client.get_ltp(trade.symbol)
        if ltp is None:
            continue

        exit_price  = None
        exit_reason = None

        if ltp <= trade.stop_loss:
            exit_price  = trade.stop_loss
            exit_reason = "SL_HIT"
        elif trade.target and ltp >= trade.target:
            exit_price  = trade.target
            exit_reason = "TARGET_HIT"

        if exit_price:
            pnl = (exit_price - trade.entry_price) * trade.quantity
            trade.exit_price  = exit_price
            trade.exit_date   = datetime.now(timezone.utc)
            trade.exit_reason = exit_reason
            trade.pnl         = round(pnl, 2)
            trade.pnl_pct     = round((exit_price - trade.entry_price) / trade.entry_price * 100, 2)
            trade.status      = TradeStatus.closed
            closed_today += 1
            pnl_today    += pnl

    db.commit()

    # Update today's forward test log
    today = date.today()
    log   = db.query(ForwardTestLog).filter(
        ForwardTestLog.log_date == today,
        ForwardTestLog.user_id == user.id
    ).first()

    if log:
        log.trades_closed = closed_today
        log.daily_pnl     = round(pnl_today, 2)
        # Cumulative P&L
        prev_logs = (
            db.query(ForwardTestLog)
            .filter(
                ForwardTestLog.user_id == user.id,
                ForwardTestLog.log_date < today
            )
            .order_by(ForwardTestLog.log_date.desc())
            .first()
        )
        prev_cumulative = prev_logs.cumulative_pnl if prev_logs else 0.0
        log.cumulative_pnl = round(prev_cumulative + pnl_today, 2)
        db.commit()

    return {"closed": closed_today, "pnl_today": round(pnl_today, 2)}


def get_forward_test_summary(db: Session, user: User) -> dict:
    """Get overall forward test performance summary."""
    logs = db.query(ForwardTestLog).filter(ForwardTestLog.user_id == user.id).order_by(ForwardTestLog.log_date).all()

    if not logs:
        return {"days_logged": 0, "total_signals": 0, "cumulative_pnl": 0}

    all_trades = (
        db.query(Trade)
        .filter(
            Trade.user_id == user.id,
            Trade.mode == TradeMode.forward,
            Trade.status == TradeStatus.closed
        )
        .all()
    )

    total_trades = len(all_trades)
    winners      = [t for t in all_trades if (t.pnl or 0) > 0]
    win_rate     = len(winners) / total_trades * 100 if total_trades else 0
    total_pnl    = sum(t.pnl or 0 for t in all_trades)

    return {
        "days_logged":    len(logs),
        "total_signals":  sum(l.signals_count for l in logs),
        "total_trades":   total_trades,
        "win_rate":       round(win_rate, 1),
        "cumulative_pnl": round(total_pnl, 2),
        "latest_date":    str(logs[-1].log_date),
        "daily_logs":     [
            {
                "date":          str(l.log_date),
                "regime":        l.market_regime,
                "signals":       l.signals_count,
                "daily_pnl":     l.daily_pnl,
                "cumulative_pnl": l.cumulative_pnl,
            }
            for l in logs
        ],
    }
