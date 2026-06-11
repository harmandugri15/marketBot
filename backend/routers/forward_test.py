"""
routers/forward_test.py
-----------------------
GET  /api/v1/forward-test/summary   — overall forward test stats
GET  /api/v1/forward-test/logs      — daily logs list
POST /api/v1/forward-test/update    — manually trigger trade updates
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from core.groww_client import GrowwClient
from core.security import get_current_user
from models.forward_test_log import ForwardTestLog
from services.forward_test_service import get_forward_test_summary, update_open_forward_trades

router = APIRouter(prefix="/api/v1/forward-test", tags=["Forward Test"])


@router.get("/summary")
def forward_test_summary(db: Session = Depends(get_db)):
    """Aggregate stats across all forward test days."""
    return get_forward_test_summary(db)


@router.get("/logs")
def forward_test_logs(
    limit: int = Query(default=30, le=365),
    db:    Session = Depends(get_db),
):
    """Most recent N days of forward test logs."""
    logs = (
        db.query(ForwardTestLog)
        .order_by(ForwardTestLog.log_date.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id":             l.id,
            "date":           str(l.log_date),
            "regime":         l.market_regime,
            "nifty_close":    l.nifty_close,
            "signals_count":  l.signals_count,
            "trades_entered": l.trades_entered,
            "trades_closed":  l.trades_closed,
            "daily_pnl":      l.daily_pnl,
            "cumulative_pnl": l.cumulative_pnl,
            "hits_sl":        l.hits_sl,
            "hits_target":    l.hits_target,
        }
        for l in logs
    ]


@router.post("/update")
def trigger_update(
    user: dict = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    """Manually check open forward-test trades against current prices."""
    client = GrowwClient()
    result = update_open_forward_trades(db, client)
    return {"message": "Update complete", **result}
