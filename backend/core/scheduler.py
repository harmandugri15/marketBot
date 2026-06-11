"""
core/scheduler.py
-----------------
APScheduler job definitions. Registered in main.py on startup.
All jobs run at IST (UTC+5:30).
"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")
scheduler = BackgroundScheduler(timezone=IST)


def register_jobs(run_daily_scan_fn, update_forward_trades_fn):
    """
    Register all scheduled jobs.
    Called from main.py lifespan context.
    """

    # Daily VCP scan — runs at 4:15 PM IST (after NSE close at 3:30 PM)
    @scheduler.scheduled_job(
        CronTrigger(hour=16, minute=15, timezone=IST),
        id="daily_vcp_scan",
        max_instances=1,
    )
    def _daily_scan():
        logger.info(f"[Scheduler] Daily VCP scan triggered at {datetime.now(IST)}")
        try:
            run_daily_scan_fn()
        except Exception as e:
            logger.error(f"[Scheduler] Daily scan failed: {e}")

    # Forward test update — check if open trades hit SL/target
    @scheduler.scheduled_job(
        CronTrigger(hour=15, minute=45, timezone=IST),
        id="update_forward_trades",
        max_instances=1,
    )
    def _update_forward():
        logger.info(f"[Scheduler] Updating forward test trades at {datetime.now(IST)}")
        try:
            update_forward_trades_fn()
        except Exception as e:
            logger.error(f"[Scheduler] Forward trade update failed: {e}")

    if not scheduler.running:
        scheduler.start()
        logger.info("[Scheduler] Started with jobs: daily_vcp_scan, update_forward_trades")
