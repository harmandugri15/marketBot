"""
routers/scanner.py
------------------
GET  /api/v1/scanner/signals         — latest signals from DB
POST /api/v1/scanner/run             — trigger a new scan now
GET  /api/v1/scanner/progress        — SSE progress stream
GET  /api/v1/scanner/regime          — current market regime
"""

import asyncio
import json
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from core.groww_client import GrowwClient
from core.security import get_current_user
from services.scanner_service import run_scan, get_latest_signals
from schemas.signal import SignalListResponse, SignalRead

router = APIRouter(prefix="/api/v1/scanner", tags=["Scanner"])

# Shared progress state (simple; would use Redis for multi-instance deploy)
_scan_state = {
    "running": False,
    "current": 0,
    "total":   0,
    "symbol":  "",
    "done":    False,
    "error":   None,
}


@router.get("/signals", response_model=SignalListResponse)
def get_signals(
    limit:    int = Query(default=50, le=200),
    strategy: Optional[str] = None,
    db:       Session = Depends(get_db),
):
    """Return the latest active signals from the database."""
    signals = get_latest_signals(db, limit=limit)
    if strategy:
        signals = [s for s in signals if s.strategy == strategy]
    regime = signals[0].market_regime if signals else None
    return SignalListResponse(
        count=len(signals),
        market_regime=regime,
        signals=[SignalRead.model_validate(s) for s in signals],
    )


@router.post("/run", status_code=202)
def trigger_scan(
    strategy: str = "AUTO",
    user:     dict = Depends(get_current_user),
    db:       Session = Depends(get_db),
):
    """Start a scan in a background thread."""
    global _scan_state
    if _scan_state["running"]:
        raise HTTPException(status_code=409, detail="A scan is already running")

    _scan_state = {"running": True, "current": 0, "total": 0, "symbol": "", "done": False, "error": None}

    def _run():
        global _scan_state
        try:
            client = GrowwClient()

            def progress(current, total, symbol):
                _scan_state["current"] = current
                _scan_state["total"]   = total
                _scan_state["symbol"]  = symbol

            run_scan(db, client, strategy=strategy, progress_callback=progress)
            _scan_state["done"]    = True
            _scan_state["running"] = False
        except Exception as e:
            _scan_state["error"]   = str(e)
            _scan_state["running"] = False

    threading.Thread(target=_run, daemon=True).start()
    return {"message": "Scan started", "status": "running"}


@router.get("/progress")
def scan_progress():
    """Server-Sent Events stream for real-time scan progress."""
    def _event_stream():
        import time
        while _scan_state["running"] or not _scan_state["done"]:
            data = json.dumps(_scan_state)
            yield f"data: {data}\n\n"
            time.sleep(0.5)
            if _scan_state["done"] or _scan_state["error"]:
                yield f"data: {json.dumps(_scan_state)}\n\n"
                break

    return StreamingResponse(_event_stream(), media_type="text/event-stream")


@router.get("/regime")
def get_regime(db: Session = Depends(get_db)):
    """Return the most recent market regime from signal records."""
    from models.signal import Signal
    latest = db.query(Signal).order_by(Signal.scan_date.desc()).first()
    regime = latest.market_regime if latest else "UNKNOWN"
    return {"regime": regime}
