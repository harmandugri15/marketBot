"""
routers/trades.py
-----------------
GET    /api/v1/trades              — list all trades
POST   /api/v1/trades              — open new trade
GET    /api/v1/trades/{id}         — get single trade
POST   /api/v1/trades/{id}/close   — close a trade
DELETE /api/v1/trades/{id}         — cancel/delete a trade
GET    /api/v1/trades/summary      — portfolio summary
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from core.groww_client import GrowwClient
from core.security import get_current_user
from models.trade import Trade, TradeMode, TradeStatus
from services.trade_service import open_trade, close_trade, get_portfolio_summary
from schemas.trade import TradeCreate, TradeClose, TradeRead, PortfolioSummary

router = APIRouter(prefix="/api/v1/trades", tags=["Trades"])


@router.get("/summary", response_model=PortfolioSummary)
def portfolio_summary(db: Session = Depends(get_db)):
    return get_portfolio_summary(db)


@router.get("", response_model=list[TradeRead])
def list_trades(
    mode:   Optional[str] = None,
    status: Optional[str] = None,
    limit:  int = Query(default=100, le=500),
    db:     Session = Depends(get_db),
):
    q = db.query(Trade)
    if mode:
        q = q.filter(Trade.mode == mode)
    if status:
        q = q.filter(Trade.status == status)
    trades = q.order_by(Trade.entry_date.desc()).limit(limit).all()
    return [TradeRead.model_validate(t) for t in trades]


@router.post("", response_model=TradeRead, status_code=status.HTTP_201_CREATED)
def create_trade(
    trade_in: TradeCreate,
    user:     dict = Depends(get_current_user),
    db:       Session = Depends(get_db),
):
    client = GrowwClient()
    trade  = open_trade(db, client, trade_in)
    return TradeRead.model_validate(trade)


@router.get("/{trade_id}", response_model=TradeRead)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return TradeRead.model_validate(trade)


@router.post("/{trade_id}/close", response_model=TradeRead)
def close_trade_endpoint(
    trade_id:  int,
    close_data: TradeClose,
    user:      dict = Depends(get_current_user),
    db:        Session = Depends(get_db),
):
    client = GrowwClient()
    trade  = close_trade(db, client, trade_id, close_data)
    return TradeRead.model_validate(trade)


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_trade(
    trade_id: int,
    user:     dict = Depends(get_current_user),
    db:       Session = Depends(get_db),
):
    trade = db.query(Trade).filter(Trade.id == trade_id).first()
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    trade.status = TradeStatus.cancelled
    db.commit()
