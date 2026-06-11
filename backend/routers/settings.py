"""
routers/settings.py
-------------------
GET  /api/v1/settings          — read current settings
PUT  /api/v1/settings          — update settings
POST /api/v1/settings/live     — enable live trading (requires confirmation)
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from config import get_settings
from core.groww_client import GrowwClient
from core.security import get_current_user
from schemas.settings import SettingsRead, SettingsUpdate, LiveModeRequest

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])


@router.get("", response_model=SettingsRead)
def read_settings():
    s = get_settings()
    return SettingsRead(
        trading_mode        = s.trading_mode,
        capital             = s.capital,
        risk_pct            = s.risk_pct,
        max_sl_pct          = s.max_sl_pct,
        max_trades_per_day  = s.max_trades_per_day,
        vol_mult            = s.vol_mult,
        expansion_pct       = s.expansion_pct,
        rsi_oversold        = s.rsi_oversold,
        min_quality         = s.min_quality,
        groww_api_configured = bool(s.groww_api_key),
        telegram_configured  = bool(s.telegram_bot_token),
    )


@router.put("")
def update_settings(
    body: SettingsUpdate,
    user: dict = Depends(get_current_user),
):
    """
    Update non-live settings by writing to .env file.
    NOTE: Live mode requires the dedicated /settings/live endpoint.
    """
    if body.trading_mode == "live":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use POST /settings/live to enable live trading"
        )

    updates = body.model_dump(exclude_none=True)
    env_map = {
        "trading_mode":       "TRADING_MODE",
        "capital":            "CAPITAL",
        "risk_pct":           "RISK_PCT",
        "max_sl_pct":         "MAX_SL_PCT",
        "max_trades_per_day": "MAX_TRADES_PER_DAY",
        "vol_mult":           "VOL_MULT",
        "expansion_pct":      "EXPANSION_PCT",
        "rsi_oversold":       "RSI_OVERSOLD",
        "min_quality":        "MIN_QUALITY",
        "groww_api_key":      "GROWW_API_KEY",
        "groww_secret_key":   "GROWW_SECRET_KEY",
        "groww_client_id":    "GROWW_CLIENT_ID",
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_chat_id":   "TELEGRAM_CHAT_ID",
    }
    for field, value in updates.items():
        env_key = env_map.get(field)
        if env_key:
            os.environ[env_key] = str(value)
            _update_env_file(env_key, str(value))

    # Bust the cached settings
    get_settings.cache_clear()
    return {"message": "Settings updated", "updated_fields": list(updates.keys())}


@router.post("/live")
def enable_live_trading(
    body: LiveModeRequest,
    user: dict = Depends(get_current_user),
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
    import os
    os.environ["GROWW_API_KEY"]    = body.groww_api_key
    os.environ["GROWW_SECRET_KEY"] = body.groww_secret_key
    os.environ["GROWW_CLIENT_ID"]  = body.groww_client_id
    get_settings.cache_clear()

    client = GrowwClient()
    if not client.test_connection():
        raise HTTPException(
            status_code=400,
            detail="Could not connect to Groww API with provided credentials. Check your API key."
        )

    os.environ["TRADING_MODE"] = "live"
    _update_env_file("TRADING_MODE", "live")
    _update_env_file("GROWW_API_KEY", body.groww_api_key)
    _update_env_file("GROWW_SECRET_KEY", body.groww_secret_key)
    _update_env_file("GROWW_CLIENT_ID", body.groww_client_id)
    get_settings.cache_clear()

    return {"message": "Live trading enabled. Be careful!", "trading_mode": "live"}


def _update_env_file(key: str, value: str):
    """Write a single key=value to the .env file."""
    env_path = ".env"
    lines = []
    found = False
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={value}\n"
                found = True
                break
    if not found:
        lines.append(f"{key}={value}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
