"""
main.py
-------
FastAPI application entry point.
Includes startup/shutdown lifecycle, CORS, all routers, and scheduler.
"""

import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import get_settings
from database import init_db
from routers import auth, scanner, trades, backtest, forward_test, settings as settings_router

# ── Logging ───────────────────────────────────────────────────────────────────
import os
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("logs/marketbot.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

app_settings = get_settings()


# ── Lifespan (startup / shutdown) ────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs once on startup:
    1. Creates all DB tables
    2. Starts the APScheduler for daily scans
    """
    logger.info(f"╔══════════════════════════════════════════╗")
    logger.info(f"║  MarketBot starting up                   ║")
    logger.info(f"║  Mode:    {app_settings.trading_mode:<30} ║")
    logger.info(f"║  Capital: ₹{app_settings.capital:<28,.0f} ║")
    logger.info(f"╚══════════════════════════════════════════╝")

    # Init DB
    init_db()
    logger.info("Database initialised")

    # Start scheduler
    try:
        from core.scheduler import register_jobs, scheduler
        from database import SessionLocal
        from core.groww_client import GrowwClient

        def _daily_scan_job():
            db = SessionLocal()
            try:
                from services.scanner_service import run_scan
                from services.forward_test_service import log_daily_signals
                from models.user import User
                from models.signal import Signal

                # 1. Run global scan using default client
                client = GrowwClient()
                signals = []
                try:
                    signals.extend(run_scan(db, client, strategy="VCP"))
                except Exception as ex:
                    logger.error(f"[Scheduler] VCP scan failed: {ex}")
                try:
                    signals.extend(run_scan(db, client, strategy="HARMAN1_PULLBACK"))
                except Exception as ex:
                    logger.error(f"[Scheduler] HARMAN1_PULLBACK scan failed: {ex}")

                latest = db.query(Signal).order_by(Signal.scan_date.desc()).first()
                regime = latest.market_regime if latest else "CASH"
                nifty_close = latest.close if latest and latest.symbol == "^NSEI" else None

                # 2. Process daily signals for every active user
                users = db.query(User).filter(User.is_active == True).all()
                for user in users:
                    try:
                        user_client = GrowwClient(
                            api_key=user.groww_api_key,
                            secret_key=user.groww_secret_key,
                            client_id=user.groww_client_id
                        )
                        log_daily_signals(db, user, user_client, signals, regime, nifty_close)
                    except Exception as ue:
                        logger.error(f"[Scheduler] Failed to process signals for user {user.username}: {ue}")
            finally:
                db.close()

        def _forward_update_job():
            db = SessionLocal()
            try:
                from services.forward_test_service import update_open_forward_trades
                from models.user import User

                users = db.query(User).filter(User.is_active == True).all()
                for user in users:
                    try:
                        user_client = GrowwClient(
                            api_key=user.groww_api_key,
                            secret_key=user.groww_secret_key,
                            client_id=user.groww_client_id
                        )
                        update_open_forward_trades(db, user, user_client)
                    except Exception as ue:
                        logger.error(f"[Scheduler] Failed to update forward trades for user {user.username}: {ue}")
            finally:
                db.close()

        register_jobs(_daily_scan_job, _forward_update_job)
        logger.info("Scheduler started")
    except Exception as e:
        logger.warning(f"Scheduler failed to start: {e}")

    yield

    # Shutdown
    try:
        from core.scheduler import scheduler
        if scheduler.running:
            scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
    except Exception:
        pass
    logger.info("MarketBot shutdown complete")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="MarketBot API",
    description="VCP Trading Bot — Vijay Thakkar Strategy | Paper → Forward → Live",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(scanner.router)
app.include_router(trades.router)
app.include_router(backtest.router)
app.include_router(forward_test.router)
app.include_router(settings_router.router)


# ── Health Check ──────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health():
    return {
        "status":       "ok",
        "app":          app_settings.app_name,
        "trading_mode": app_settings.trading_mode,
        "version":      "2.0.0",
    }


# ── Serve Frontend (production) ───────────────────────────────────────────────
# When deployed, the built frontend is served from /frontend/dist
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def serve_spa(full_path: str):
        """Serve the SPA for all non-API routes."""
        index = os.path.join(FRONTEND_DIST, "index.html")
        if os.path.exists(index):
            return FileResponse(index)
        return {"error": "Frontend not built"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=app_settings.debug,
        log_level="info",
    )
