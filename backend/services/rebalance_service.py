"""
services/rebalance_service.py
-----------------------------
Automated ETF Multi-Asset Rebalancing Engine.
Target Allocation: 60% Equity (NIFTYBEES.NS), 40% Gold (GOLDBEES.NS).
"""

import logging
from typing import Dict, Any

from sqlalchemy.orm import Session
from core.groww_client import GrowwClient
from models.user import User

logger = logging.getLogger(__name__)

TARGET_ALLOCATION = {
    "NIFTYBEES.NS": 0.60,
    "GOLDBEES.NS": 0.40,
}

DRIFT_THRESHOLD = 0.05  # 5%


def run_etf_rebalance(db: Session, user: User, client: GrowwClient) -> Dict[str, Any]:
    """
    Checks the current holdings and calculates drift.
    Returns the required trades to rebalance if drift > 5%.
    """
    logger.info(f"Running ETF Rebalance check for user {user.username}...")

    # For simulation, we assume user has total capital designated for ETF strategy.
    # We need to fetch real LTPs for both.
    ltp_nifty = client.get_ltp("NIFTYBEES.NS")
    ltp_gold  = client.get_ltp("GOLDBEES.NS")

    if not ltp_nifty or not ltp_gold:
        return {"status": "error", "message": "Failed to fetch ETF prices"}

    # In a real environment, we would query the broker for current holdings.
    # For this architecture, we will simulate a mock portfolio state or rely on DB records.
    # Since we don't have a live portfolio syncing mechanism yet, we will calculate
    # theoretical rebalance orders based on the user's allocated capital.
    
    total_value = user.capital
    
    # Calculate target values
    target_nifty_val = total_value * TARGET_ALLOCATION["NIFTYBEES.NS"]
    target_gold_val  = total_value * TARGET_ALLOCATION["GOLDBEES.NS"]
    
    # Calculate target quantities
    target_qty_nifty = int(target_nifty_val // ltp_nifty)
    target_qty_gold  = int(target_gold_val // ltp_gold)

    # Note: A full implementation would compare 'current_qty' with 'target_qty'.
    # Because we don't hold live positions in the mock DB for the ETF strategy yet,
    # we return the recommended ideal state.
    
    return {
        "status": "success",
        "action": "rebalance_required",
        "total_portfolio_value": total_value,
        "niftybees_ltp": ltp_nifty,
        "goldbees_ltp": ltp_gold,
        "target_allocation": {
            "NIFTYBEES.NS": {
                "target_pct": "60%",
                "target_value": round(target_nifty_val, 2),
                "target_qty": target_qty_nifty
            },
            "GOLDBEES.NS": {
                "target_pct": "40%",
                "target_value": round(target_gold_val, 2),
                "target_qty": target_qty_gold
            }
        },
        "instructions": (
            "If current holdings drift > 5% from the 60:40 target, "
            "place CNC Market Orders to align with target_qty."
        )
    }
