import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from core.groww_client import GrowwClient
from models.user import User
from models.trade import Trade, TradeStatus
from schemas.trade import TradeCreate, TradeClose
from services.trade_service import open_trade, close_trade, TradingModeError

logger = logging.getLogger(__name__)

def process_auto_trading_signals(db: Session, signals: list[dict], regime: str):
    """
    Called after scanner completes. 
    Checks for active auto-trading users, filters signals, and places trades automatically.
    """
    if regime == "PANIC":
        logger.warning("AutoTrading: Market regime is PANIC. Skipping new entries.")
        return

    # Find users with auto_trading_enabled
    users = db.query(User).filter(User.is_active == True, User.auto_trading_enabled == True).all()
    if not users:
        return
        
    logger.info(f"AutoTrading: Processing signals for {len(users)} users.")

    for user in users:
        strat = user.auto_trading_strategy
        
        # Filter signals for user's strategy and min_quality
        valid_signals = [
            s for s in signals 
            if s["strategy"] == strat and s.get("quality", 0) >= user.min_quality
        ]
        
        # Sort by highest quality first
        valid_signals.sort(key=lambda x: x.get("quality", 0), reverse=True)
        
        # Fetch current open trades for this user to avoid double buying
        open_trades = db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.status == TradeStatus.open
        ).all()
        open_symbols = {t.symbol for t in open_trades}
        
        for sig in valid_signals:
            symbol = sig["symbol"]
            
            # Skip if we already hold this symbol
            if symbol in open_symbols:
                continue
                
            try:
                # Prepare TradeCreate payload
                trade_in = TradeCreate(
                    symbol=symbol,
                    strategy=strat,
                    entry_price=sig["close"], # Buying at close for simulated/forward/live market order
                    stop_loss=sig["stop_loss"],
                    target=sig["target"],
                    quantity=None, # will be calculated by trade_service
                    capital_deployed=None
                )
                
                logger.info(f"AutoTrading: [User {user.username}] Buying {symbol} (Score: {sig.get('quality')})")
                
                # Execute Trade (will route to live/paper based on user.trading_mode)
                open_trade(db=db, user=user, trade_in=trade_in)
                
                # Update local open_symbols to prevent duplicate buys in same loop
                open_symbols.add(symbol)
                
            except ValueError as ve:
                logger.warning(f"AutoTrading: [User {user.username}] Trade skipped for {symbol}: {ve}")
            except TradingModeError as tme:
                logger.error(f"AutoTrading: [User {user.username}] Live Execution Error for {symbol}: {tme}")
                
                
def monitor_auto_trades(db: Session):
    """
    Called periodically by scheduler.
    Fetches all open trades for auto-trading users.
    Checks live prices to see if target or stop_loss is hit.
    """
    users = db.query(User).filter(User.is_active == True, User.auto_trading_enabled == True).all()
    if not users:
        return
        
    for user in users:
        open_trades = db.query(Trade).filter(
            Trade.user_id == user.id,
            Trade.status == TradeStatus.open
        ).all()
        
        if not open_trades:
            continue
            
        client = GrowwClient(
            api_key=user.groww_api_key,
            secret_key=user.groww_secret_key,
            client_id=user.groww_client_id
        )
        
        for trade in open_trades:
            # Fetch LTP
            ltp = client.get_ltp(trade.symbol)
            if not ltp:
                continue
                
            reason = None
            if trade.stop_loss and ltp <= trade.stop_loss:
                reason = "STOP_LOSS_HIT"
            elif trade.target and ltp >= trade.target:
                reason = "TARGET_HIT"
                
            if reason:
                logger.info(f"AutoTrading: [User {user.username}] {reason} for {trade.symbol} @ {ltp}")
                close_data = TradeClose(
                    exit_price=ltp,
                    exit_reason=reason
                )
                try:
                    close_trade(db=db, user=user, trade_id=trade.id, close_data=close_data)
                except Exception as e:
                    logger.error(f"AutoTrading: [User {user.username}] Failed to close {trade.symbol}: {e}")
