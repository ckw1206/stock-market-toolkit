"""In-process job scheduler.

The backend is a long-running process, so nightly jobs are scheduled here
directly rather than relying on an external caller (e.g. a CI cron) to hit
the /cron/* endpoints — see issue #283, where the screener never scanned
because nothing external was ever wired up to trigger it.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import structlog

log = structlog.get_logger(__name__)


def start_scheduler() -> AsyncIOScheduler:
    """Create and start a fresh scheduler instance.

    A fresh instance per call (rather than a module-level singleton) matters
    because APScheduler can't be restarted after shutdown — the FastAPI
    lifespan runs start/shutdown once per app instance, and reusing one
    scheduler object across multiple lifespan cycles (e.g. tests that boot
    the app's lifespan more than once via TestClient) would try to restart
    an already-shut-down scheduler.
    """
    from app.routes.cron import scan_signals_job
    from app.services.alert_checker import check_alerts

    scheduler = AsyncIOScheduler()

    async def run_scan_signals() -> None:
        result = await scan_signals_job()
        log.info("scheduled_scan_signals", **result)

    scheduler.add_job(
        run_scan_signals,
        "cron",
        hour=3,
        minute=0,
        id="scan_signals",
    )
    # Same trap as issue #283: /cron/check-alerts said "called every 15 minutes
    # by external scheduler", but no external scheduler exists — alerts never
    # fired. Run the check in-process like the signal scan.
    scheduler.add_job(
        check_alerts,
        "interval",
        minutes=15,
        id="check_alerts",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    return scheduler
