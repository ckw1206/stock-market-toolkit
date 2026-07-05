"""In-process job scheduler.

The backend is a long-running process, so nightly jobs are scheduled here
directly rather than relying on an external caller (e.g. a CI cron) to hit
the /cron/* endpoints — see issue #283, where the screener never scanned
because nothing external was ever wired up to trigger it.
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import structlog

log = structlog.get_logger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    from app.routes.cron import scan_signals_job

    async def run_scan_signals() -> None:
        result = await scan_signals_job()
        log.info("scheduled_scan_signals", **result)

    scheduler.add_job(
        run_scan_signals,
        "cron",
        hour=3,
        minute=0,
        id="scan_signals",
        replace_existing=True,
    )
    scheduler.start()
