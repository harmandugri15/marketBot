"""
routers/data_log.py
-------------------
GET /api/v1/logs/data — view recent yfinance data-fetch logs
"""

import os
import logging
from collections import deque

from fastapi import APIRouter, Depends, Query

from models.user import User
from core.security import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/logs", tags=["Logs"])

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "marketbot.log")


@router.get("/data")
def get_data_logs(
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
):
    """Return the last N log lines containing [yfinance] markers."""
    if not os.path.isfile(LOG_FILE):
        return {"logs": []}

    try:
        matching: deque[str] = deque(maxlen=limit)
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if "[yfinance]" in line:
                    matching.append(line.rstrip())
        return {"logs": list(matching)}
    except Exception as e:
        logger.error(f"Failed to read log file: {e}")
        return {"logs": []}
