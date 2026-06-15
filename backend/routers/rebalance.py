"""
routers/rebalance.py
--------------------
Exposes the ETF Multi-Asset Rebalancing Engine.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
from core.security import get_current_user
from core.groww_client import GrowwClient
from services.rebalance_service import run_etf_rebalance

router = APIRouter(prefix="/api/v1/rebalance", tags=["Rebalance"])


@router.get("")
def get_rebalance_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Checks the current drift between NIFTYBEES and GOLDBEES
    based on the user's allocated capital.
    """
    client = GrowwClient(
        api_key=current_user.groww_api_key,
        secret_key=current_user.groww_secret_key,
        client_id=current_user.groww_client_id
    )
    result = run_etf_rebalance(db, current_user, client)
    return result
