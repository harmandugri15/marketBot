"""
routers/sandbox.py
------------------
Student sandbox endpoints for paper trading with chart data and indicators.

GET  /api/v1/sandbox/chart      — fetch chart data with technical indicators
POST /api/v1/sandbox/trade      — create a sandbox paper trade
GET  /api/v1/sandbox/positions  — list open sandbox positions
"""

import logging
from typing import Optional
from datetime import datetime, timedelta

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
import asyncio
from core.security import decode_token
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from models.trade import Trade, TradeMode, TradeStatus
from core.security import get_current_user
from core.groww_client import GrowwClient
from schemas.trade import TradeCreate, TradeRead
from services.trade_service import open_trade

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sandbox", tags=["Sandbox"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class SandboxTradeRequest(BaseModel):
    symbol: str
    action: str = Field(..., pattern="^(BUY|SELL)$")
    quantity: int = Field(..., ge=1)
    price: float = Field(..., gt=0)
    stop_loss: Optional[float] = None
    target: Optional[float] = None


class IndicatorsResponse(BaseModel):
    ema10: list[Optional[float]]
    ema20: list[Optional[float]]
    ema50: list[Optional[float]]
    rsi: list[Optional[float]]
    bollinger_upper: list[Optional[float]]
    bollinger_lower: list[Optional[float]]
    bollinger_mid: list[Optional[float]]


class ChartDataPoint(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class ChartResponse(BaseModel):
    symbol: str
    data: list[ChartDataPoint]
    indicators: IndicatorsResponse


# ── Indicator Calculations ────────────────────────────────────────────────────

def _calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate RSI (Relative Strength Index)."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _compute_indicators(df: pd.DataFrame) -> IndicatorsResponse:
    """Compute EMA10, EMA20, EMA50, RSI14, Bollinger Bands (20,2) from a close series."""
    close = df["close"]

    ema10 = close.ewm(span=10, adjust=False).mean()
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()

    rsi = _calculate_rsi(close, period=14)

    bb_mid = close.rolling(window=20).mean()
    bb_std = close.rolling(window=20).std()
    bb_upper = bb_mid + 2 * bb_std
    bb_lower = bb_mid - 2 * bb_std

    def _to_list(s: pd.Series) -> list[Optional[float]]:
        return [round(v, 2) if pd.notna(v) else None for v in s]

    return IndicatorsResponse(
        ema10=_to_list(ema10),
        ema20=_to_list(ema20),
        ema50=_to_list(ema50),
        rsi=_to_list(rsi),
        bollinger_upper=_to_list(bb_upper),
        bollinger_lower=_to_list(bb_lower),
        bollinger_mid=_to_list(bb_mid),
    )


# ── Period/Interval → Date Range Mapping ──────────────────────────────────────

_PERIOD_DAYS = {
    "1mo": 30, "3mo": 90, "6mo": 180, "1y": 365, "2y": 730, "5y": 1825,
}


def _resolve_dates(period: str) -> tuple[str, str]:
    """Convert period string to (from_date, to_date) in YYYY-MM-DD format."""
    days = _PERIOD_DAYS.get(period, 180)
    to_dt = datetime.utcnow()
    from_dt = to_dt - timedelta(days=days)
    return from_dt.strftime("%Y-%m-%d"), to_dt.strftime("%Y-%m-%d")


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/chart", response_model=ChartResponse)
def get_chart_data(
    symbol: str = Query(..., description="Stock symbol, e.g. RELIANCE.NS"),
    period: str = Query(default="6mo", description="Period: 1mo, 3mo, 6mo, 1y, 2y, 5y"),
    interval: str = Query(default="1d", description="Interval: 1d, 5m, 15m, 1h"),
    current_user: User = Depends(get_current_user),
):
    """Fetch chart data with technical indicators for a symbol."""
    from_date, to_date = _resolve_dates(period)

    client = GrowwClient(
        api_key=current_user.groww_api_key,
        secret_key=current_user.groww_secret_key,
        client_id=current_user.groww_client_id,
    )
    raw_data = client.get_historical_data(symbol, from_date, to_date, interval=interval)

    if not raw_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data found for symbol {symbol}",
        )

    df = pd.DataFrame(raw_data)
    indicators = _compute_indicators(df)

    return ChartResponse(
        symbol=symbol,
        data=[ChartDataPoint(**row) for row in raw_data],
        indicators=indicators,
    )


class LtpResponse(BaseModel):
    symbol: str
    ltp: Optional[float]


@router.get("/ltp", response_model=LtpResponse)
def get_sandbox_ltp(
    symbol: str = Query(..., description="Stock symbol, e.g. RELIANCE.NS"),
    current_user: User = Depends(get_current_user),
):
    """Fetch live Last Traded Price (LTP) for a symbol."""
    client = GrowwClient(
        api_key=current_user.groww_api_key,
        secret_key=current_user.groww_secret_key,
        client_id=current_user.groww_client_id,
    )
    price = client.get_ltp(symbol)
    return LtpResponse(symbol=symbol, ltp=price)


@router.post("/trade", response_model=TradeRead, status_code=status.HTTP_201_CREATED)
def create_sandbox_trade(
    body: SandboxTradeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a sandbox paper trade."""
    # Default stop_loss to 5% below entry for BUY if not provided
    stop_loss = body.stop_loss
    if stop_loss is None:
        stop_loss = round(body.price * 0.95, 2) if body.action == "BUY" else round(body.price * 1.05, 2)

    trade_in = TradeCreate(
        symbol=body.symbol,
        strategy="SANDBOX",
        entry_price=body.price,
        quantity=body.quantity,
        stop_loss=stop_loss,
        target=body.target,
        capital_deployed=round(body.price * body.quantity, 2),
    )

    trade = open_trade(db, current_user, trade_in, override_mode="paper")
    return TradeRead.model_validate(trade)


@router.get("/positions", response_model=list[TradeRead])
def get_sandbox_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all open sandbox paper trades for the current user."""
    trades = (
        db.query(Trade)
        .filter(
            Trade.user_id == current_user.id,
            Trade.mode == TradeMode.paper,
            Trade.strategy == "SANDBOX",
            Trade.status == TradeStatus.open,
        )
        .order_by(Trade.entry_date.desc())
        .all()
    )
    return [TradeRead.model_validate(t) for t in trades]


@router.websocket("/ws/live")
async def sandbox_live_ws(
    websocket: WebSocket,
    token: str = Query(None, description="JWT token for auth"),
    db: Session = Depends(get_db),
):
    """WebSocket endpoint for real-time sandbox updates (LTP)."""
    await websocket.accept()

    if not token:
        await websocket.close(code=1008)
        return

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user or not user.is_active:
            raise ValueError("Invalid user")
    except Exception:
        await websocket.close(code=1008)
        return

    client = GrowwClient(
        api_key=user.groww_api_key,
        secret_key=user.groww_secret_key,
        client_id=user.groww_client_id,
    )

    subscribed_symbols = set()

    async def receive_loop():
        try:
            while True:
                data = await websocket.receive_json()
                if data.get("action") == "subscribe":
                    symbols = data.get("symbols", [])
                    subscribed_symbols.clear()
                    subscribed_symbols.update(symbols)
        except WebSocketDisconnect:
            pass

    async def send_loop():
        try:
            while True:
                if subscribed_symbols:
                    results = []
                    for sym in subscribed_symbols:
                        try:
                            price = await asyncio.to_thread(client.get_ltp, sym)
                            if price is not None:
                                results.append({"symbol": sym, "ltp": price})
                        except Exception:
                            pass
                    if results:
                        await websocket.send_json({"type": "ltp_update", "data": results})
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"WebSocket send error: {e}")

    task1 = asyncio.create_task(receive_loop())
    task2 = asyncio.create_task(send_loop())
    
    done, pending = await asyncio.wait([task1, task2], return_when=asyncio.FIRST_COMPLETED)
    for task in pending:
        task.cancel()
