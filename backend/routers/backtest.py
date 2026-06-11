"""
routers/backtest.py
-------------------
POST /api/v1/backtest/run      — start a backtest (async, background)
GET  /api/v1/backtest/progress — SSE progress stream
GET  /api/v1/backtest/results  — list all past runs
GET  /api/v1/backtest/{id}     — detail for one run
"""

import json
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from core.groww_client import GrowwClient
from core.security import get_current_user
from models.backtest_result import BacktestResult
from services.backtest_service import run_backtest
from schemas.backtest import BacktestRequest, BacktestSummary, BacktestDetail, BacktestProgress

router = APIRouter(prefix="/api/v1/backtest", tags=["Backtest"])

_bt_state = {
    "running": False,
    "current": 0,
    "total":   0,
    "symbol":  "",
    "done":    False,
    "error":   None,
    "result_id": None,
}


@router.post("/run", status_code=202)
def start_backtest(
    req:  BacktestRequest,
    user: dict = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    global _bt_state
    if _bt_state["running"]:
        raise HTTPException(status_code=409, detail="A backtest is already running")

    _bt_state = {"running": True, "current": 0, "total": 0, "symbol": "", "done": False, "error": None, "result_id": None}

    def _run():
        global _bt_state
        # Create a new DB session for the thread
        from database import SessionLocal
        thread_db = SessionLocal()
        try:
            client = GrowwClient()

            def progress(current, total, symbol):
                _bt_state["current"] = current
                _bt_state["total"]   = total
                _bt_state["symbol"]  = symbol

            result = run_backtest(thread_db, client, req, progress_callback=progress)
            _bt_state["done"]      = True
            _bt_state["running"]   = False
            _bt_state["result_id"] = result.id
        except Exception as e:
            _bt_state["error"]   = str(e)
            _bt_state["running"] = False
        finally:
            thread_db.close()

    threading.Thread(target=_run, daemon=True).start()
    return {"message": "Backtest started", "status": "running"}


@router.get("/progress", response_model=BacktestProgress)
def backtest_progress():
    return BacktestProgress(**_bt_state)


@router.get("/progress/stream")
def backtest_progress_stream():
    """SSE stream for frontend progress bar."""
    def _gen():
        import time
        while _bt_state["running"] or not _bt_state["done"]:
            yield f"data: {json.dumps(_bt_state)}\n\n"
            time.sleep(0.8)
            if _bt_state["done"] or _bt_state["error"]:
                yield f"data: {json.dumps(_bt_state)}\n\n"
                break

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/results", response_model=list[BacktestSummary])
def list_results(
    limit:    int = Query(default=20, le=100),
    strategy: Optional[str] = None,
    db:       Session = Depends(get_db),
):
    q = db.query(BacktestResult)
    if strategy:
        q = q.filter(BacktestResult.strategy == strategy)
    results = q.order_by(BacktestResult.run_date.desc()).limit(limit).all()
    return [BacktestSummary.model_validate(r) for r in results]


@router.get("/{result_id}", response_model=BacktestDetail)
def get_result(result_id: int, db: Session = Depends(get_db)):
    result = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    return BacktestDetail.model_validate(result)
