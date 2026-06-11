"""
services/trade_service.py
--------------------------
Trade lifecycle management with hard separation between paper, forward, and live modes.
The mode guard is the key safety mechanism:
- paper mode:   simulates fills, no API calls
- forward mode: records trade in DB as paper, but uses real market prices
- live mode:    calls Groww API — only if credentials are verified
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from config import get_settings
from core.groww_client import GrowwClient
from core.indicators import calculate_position_size
from models.trade import Trade, TradeMode, TradeStatus
from schemas.trade import TradeCreate, TradeClose, PortfolioSummary

logger = logging.getLogger(__name__)
settings = get_settings()


class TradingModeError(Exception):
    """Raised when trying to place a live order without valid credentials."""
    pass


def _resolve_mode() -> TradeMode:
    return TradeMode(settings.trading_mode)


def open_trade(
    db: Session,
    client: GrowwClient,
    trade_in: TradeCreate,
    override_mode: Optional[str] = None,
) -> Trade:
    """
    Open a new trade. Routes to paper/forward/live based on current mode.
    """
    mode = TradeMode(override_mode) if override_mode else _resolve_mode()

    pos = calculate_position_size(
        capital=settings.capital,
        risk_pct=settings.risk_pct,
        entry=trade_in.entry_price,
        stop_loss=trade_in.stop_loss,
    )

    quantity = trade_in.quantity or pos["quantity"]
    if quantity <= 0:
        raise ValueError("Position size is 0 — check capital and risk settings.")

    groww_order_id = None
    groww_status   = None

    if mode == TradeMode.live:
        # ── LIVE: place real order ────────────────────────────────────────────
        if not client.is_configured:
            raise TradingModeError("Live mode requires valid Groww API credentials.")
        logger.info(f"LIVE ORDER: BUY {quantity}x {trade_in.symbol} @ {trade_in.entry_price}")
        order = client.place_order(
            symbol     = trade_in.symbol,
            side       = "BUY",
            quantity   = quantity,
            order_type = "LIMIT",
            price      = trade_in.entry_price,
            product    = "CNC",
        )
        groww_order_id = order.get("order_id")
        groww_status   = order.get("status", "PENDING")
    else:
        logger.info(f"{mode.upper()} TRADE: {trade_in.symbol} @ {trade_in.entry_price}")

    trade = Trade(
        symbol           = trade_in.symbol,
        strategy         = trade_in.strategy,
        mode             = mode,
        status           = TradeStatus.open,
        entry_price      = trade_in.entry_price,
        quantity         = quantity,
        stop_loss        = trade_in.stop_loss,
        target           = trade_in.target,
        capital_deployed = trade_in.capital_deployed or pos["capital_deployed"],
        groww_order_id   = groww_order_id,
        groww_order_status = groww_status,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    logger.info(f"Trade opened: {trade}")
    return trade


def close_trade(
    db: Session,
    client: GrowwClient,
    trade_id: int,
    close_data: TradeClose,
) -> Trade:
    """
    Close an open trade, calculate P&L, optionally place exit order.
    """
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise ValueError(f"Trade {trade_id} not found")
    if trade.status != TradeStatus.open:
        raise ValueError(f"Trade {trade_id} is already {trade.status}")

    if trade.mode == TradeMode.live and client.is_configured:
        logger.info(f"LIVE EXIT: SELL {trade.quantity}x {trade.symbol} @ {close_data.exit_price}")
        client.place_order(
            symbol     = trade.symbol,
            side       = "SELL",
            quantity   = trade.quantity,
            order_type = "LIMIT",
            price      = close_data.exit_price,
            product    = "CNC",
        )

    pnl     = (close_data.exit_price - trade.entry_price) * trade.quantity
    pnl_pct = ((close_data.exit_price - trade.entry_price) / trade.entry_price) * 100

    trade.exit_price  = close_data.exit_price
    trade.exit_date   = datetime.now(timezone.utc)
    trade.exit_reason = close_data.exit_reason
    trade.pnl         = round(pnl, 2)
    trade.pnl_pct     = round(pnl_pct, 2)
    trade.status       = TradeStatus.closed

    db.commit()
    db.refresh(trade)
    logger.info(f"Trade closed: {trade}")
    return trade


def get_portfolio_summary(db: Session) -> PortfolioSummary:
    """Aggregate portfolio metrics across all trades."""
    all_trades    = db.query(Trade).all()
    open_trades   = [t for t in all_trades if t.status == TradeStatus.open]
    closed_trades = [t for t in all_trades if t.status == TradeStatus.closed]

    realized_pnl = sum(t.pnl or 0 for t in closed_trades)

    # Approximate open P&L (would need current prices for accuracy)
    open_pnl = 0.0

    winners = [t for t in closed_trades if (t.pnl or 0) > 0]
    win_rate = (len(winners) / len(closed_trades) * 100) if closed_trades else 0.0

    return PortfolioSummary(
        open_trades   = len(open_trades),
        total_trades  = len(all_trades),
        open_pnl      = round(open_pnl, 2),
        realized_pnl  = round(realized_pnl, 2),
        win_rate       = round(win_rate, 1),
        trading_mode  = settings.trading_mode,
    )
