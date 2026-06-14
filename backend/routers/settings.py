"""
routers/settings.py
-------------------
GET  /api/v1/settings          — read current settings
PUT  /api/v1/settings          — update settings
POST /api/v1/settings/live     — enable live trading (requires confirmation)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from config import get_settings
from core.groww_client import GrowwClient
from core.security import get_current_user
from schemas.settings import SettingsRead, SettingsUpdate, LiveModeRequest

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


@router.get("", response_model=SettingsRead)
def read_settings(current_user: User = Depends(get_current_user)):
    s = get_settings()
    return SettingsRead(
        trading_mode        = current_user.trading_mode,
        capital             = current_user.capital,
        risk_pct            = current_user.risk_pct,
        max_sl_pct          = current_user.max_sl_pct,
        max_trades_per_day  = s.max_trades_per_day,
        vol_mult            = s.vol_mult,
        expansion_pct       = s.expansion_pct,
        rsi_oversold        = s.rsi_oversold,
        min_quality         = current_user.min_quality,
        groww_api_configured = bool(current_user.groww_api_key),
        telegram_configured  = bool(s.telegram_bot_token),
    )


@router.put("")
def update_settings(
    body: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update non-live settings on the user database record.
    NOTE: Live mode requires the dedicated /settings/live endpoint.
    """
    if body.trading_mode == "live":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use POST /settings/live to enable live trading"
        )

    if body.trading_mode is not None:
        current_user.trading_mode = body.trading_mode
    if body.capital is not None:
        current_user.capital = body.capital
    if body.risk_pct is not None:
        current_user.risk_pct = body.risk_pct
    if body.max_sl_pct is not None:
        current_user.max_sl_pct = body.max_sl_pct
    if body.min_quality is not None:
        current_user.min_quality = body.min_quality
    if body.groww_api_key is not None:
        current_user.groww_api_key = body.groww_api_key
    if body.groww_secret_key is not None:
        current_user.groww_secret_key = body.groww_secret_key
    if body.groww_client_id is not None:
        current_user.groww_client_id = body.groww_client_id

    db.commit()
    return {"message": "Settings updated"}


@router.post("/live")
def enable_live_trading(
    body: LiveModeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Enable live trading. Requires:
    1. confirm=True
    2. Valid Groww credentials that can actually connect
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail="You must set confirm=true to enable live trading"
        )

    # Verify credentials work before enabling
    client = GrowwClient(
        api_key=body.groww_api_key,
        secret_key=body.groww_secret_key,
        client_id=body.groww_client_id
    )
    if not client.test_connection():
        raise HTTPException(
            status_code=400,
            detail="Could not connect to Groww API with provided credentials. Check your API key."
        )

    current_user.trading_mode = "live"
    current_user.groww_api_key = body.groww_api_key
    current_user.groww_secret_key = body.groww_secret_key
    current_user.groww_client_id = body.groww_client_id

    db.commit()
    return {"message": "Live trading enabled. Be careful!", "trading_mode": "live"}
