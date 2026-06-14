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
from models.user import User
from core.groww_client import GrowwClient
from core.security import get_current_user
from models.backtest_result import BacktestResult
from services.backtest_service import run_backtest
from schemas.backtest import BacktestRequest, BacktestSummary, BacktestDetail, BacktestProgress

router = APIRouter(prefix="/api/v1/backtest", tags=["Backtest"])

# Map user_id -> backtest state dict
_bt_states = {}


def get_user_bt_state(user_id: int) -> dict:
    if user_id not in _bt_states:
        _bt_states[user_id] = {
            "running": False,
            "current": 0,
            "total":   0,
            "symbol":  "",
            "done":    False,
            "error":   None,
            "result_id": None,
        }
    return _bt_states[user_id]


@router.post("/run", status_code=202)
def start_backtest(
    req:  BacktestRequest,
    current_user: User = Depends(get_current_user),
    db:   Session = Depends(get_db),
):
    user_id = current_user.id
    state = get_user_bt_state(user_id)
    if state["running"]:
        raise HTTPException(status_code=409, detail="A backtest is already running")

    state.update({"running": True, "current": 0, "total": 0, "symbol": "", "done": False, "error": None, "result_id": None})

    def _run():
        # Create a new DB session for the thread
        from database import SessionLocal
        thread_db = SessionLocal()
        try:
            user = thread_db.query(User).filter(User.id == user_id).first()
            if not user:
                raise Exception("User not found")
            client = GrowwClient(
                api_key=user.groww_api_key,
                secret_key=user.groww_secret_key,
                client_id=user.groww_client_id
            )

            def progress(current, total, symbol):
                state["current"] = current
                state["total"]   = total
                state["symbol"]  = symbol

            result = run_backtest(thread_db, user, client, req, progress_callback=progress)
            state["done"]      = True
            state["running"]   = False
            state["result_id"] = result.id
        except Exception as e:
            state["error"]   = str(e)
            state["running"] = False
        finally:
            thread_db.close()

    threading.Thread(target=_run, daemon=True).start()
    return {"message": "Backtest started", "status": "running"}


@router.get("/progress", response_model=BacktestProgress)
def backtest_progress(current_user: User = Depends(get_current_user)):
    return BacktestProgress(**get_user_bt_state(current_user.id))


@router.get("/progress/stream")
def backtest_progress_stream(current_user: User = Depends(get_current_user)):
    """SSE stream for frontend progress bar."""
    user_id = current_user.id
    state = get_user_bt_state(user_id)

    def _gen():
        import time
        while state["running"] or not state["done"]:
            yield f"data: {json.dumps(state)}\n\n"
            time.sleep(0.8)
            if state["done"] or state["error"]:
                yield f"data: {json.dumps(state)}\n\n"
                break

    return StreamingResponse(_gen(), media_type="text/event-stream")


@router.get("/results", response_model=list[BacktestSummary])
def list_results(
    limit:    int = Query(default=20, le=100),
    strategy: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db:       Session = Depends(get_db),
):
    q = db.query(BacktestResult).filter(BacktestResult.user_id == current_user.id)
    if strategy:
        q = q.filter(BacktestResult.strategy == strategy)
    results = q.order_by(BacktestResult.run_date.desc()).limit(limit).all()
    return [BacktestSummary.model_validate(r) for r in results]


@router.get("/{result_id}", response_model=BacktestDetail)
def get_result(
    result_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    result = db.query(BacktestResult).filter(
        BacktestResult.id == result_id,
        BacktestResult.user_id == current_user.id
    ).first()
    if not result:
        raise HTTPException(status_code=404, detail="Backtest result not found")
    return BacktestDetail.model_validate(result)
