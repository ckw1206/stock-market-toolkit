from fastapi import APIRouter

router = APIRouter(tags=["cron"])


async def scan_signals_job() -> dict:
    """Run the nightly signal scan across the universe, recording a JobRun.

    Shared by the /cron/scan-signals HTTP endpoint (manual/debug trigger) and
    the in-process scheduler (app/scheduler.py), so both paths get identical
    already-running/failure bookkeeping.
    """
    from datetime import datetime, timezone
    from app.database import AsyncSessionLocal
    from app.models import JobRun
    from sqlalchemy import select, update

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(JobRun)
            .where(JobRun.job_type == "signal_scan", JobRun.status == "running")
            .limit(1)
        )
        if result.scalar_one_or_none():
            return {"status": "skipped", "message": "Signal scan already running"}

        job = JobRun(
            job_type="signal_scan",
            status="running",
            total_symbols=0,
        )
        db.add(job)
        await db.commit()
        job_run_id = job.id

    from app.services.top_signals import run_signal_scan

    try:
        counts = await run_signal_scan(job_run_id=job_run_id)
    except Exception as exc:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(JobRun)
                .where(JobRun.id == job_run_id)
                .values(
                    status="failed",
                    error_details=str(exc),
                    completed_at=datetime.now(timezone.utc),
                )
            )
            await db.commit()
        return {"status": "error", "message": f"Signal scan failed: {exc}"}

    async with AsyncSessionLocal() as db:
        await db.execute(
            update(JobRun)
            .where(JobRun.id == job_run_id)
            .values(
                status="completed",
                symbols_processed=counts["symbols_processed"],
                total_symbols=counts["total_symbols"],
                errors=counts["errors"],
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()

    return {"status": "ok", **counts}


@router.post("/cron/scan-signals")
async def cron_scan_signals():
    """Manual/debug trigger for the nightly signal scan. The scan itself now
    runs on its own via app/scheduler.py; this endpoint is kept for on-demand
    reruns without needing to restart the process."""
    return await scan_signals_job()


@router.get("/cron/scan-signals/status")
async def cron_scan_signals_status():
    """Return status of the last signal scan run."""
    from app.database import AsyncSessionLocal
    from app.models import JobRun
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(JobRun)
            .where(JobRun.job_type == "signal_scan")
            .order_by(JobRun.started_at.desc())
            .limit(1)
        )
        last_run = result.scalar_one_or_none()

    if last_run is None:
        return {"last_run": None, "is_running": False}

    return {
        "last_run": {
            "id": last_run.id,
            "job_type": last_run.job_type,
            "status": last_run.status,
            "symbols_processed": last_run.symbols_processed or 0,
            "total_symbols": last_run.total_symbols or 0,
            "errors": last_run.errors or 0,
            "error_details": last_run.error_details,
            "started_at": (
                last_run.started_at.isoformat() if last_run.started_at else None
            ),
            "completed_at": (
                last_run.completed_at.isoformat() if last_run.completed_at else None
            ),
        },
        "is_running": last_run.status == "running" if last_run else False,
    }


@router.post("/cron/check-alerts")
async def cron_check_alerts():
    """Cron endpoint to check all price alerts. Called every 15 minutes by external scheduler."""
    from app.services.alert_checker import check_alerts

    await check_alerts()
    return {"status": "ok", "message": "Alerts checked"}


@router.post("/cron/ingest")
async def cron_ingest():
    """Cron endpoint to trigger nightly fundamentals ingestion."""
    from app.database import AsyncSessionLocal
    from app.models import JobRun
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(JobRun)
            .where(JobRun.job_type == "nightly_ingest", JobRun.status == "running")
            .limit(1)
        )
        if result.scalar_one_or_none():
            return {"status": "skipped", "message": "Ingestion already running"}

        job = JobRun(
            job_type="nightly_ingest",
            status="running",
            total_symbols=0,
        )
        db.add(job)
        await db.commit()
        job_run_id = job.id

    from app.services.ingestion import run_nightly_ingest

    processed = await run_nightly_ingest(job_run_id=job_run_id)
    return {"status": "ok", "symbols_processed": processed}


@router.get("/cron/ingest/status")
async def cron_ingest_status():
    """Return status of the last nightly ingestion run."""
    from app.database import AsyncSessionLocal
    from app.services.ingestion import get_latest_job_run

    async with AsyncSessionLocal() as db:
        last_run = await get_latest_job_run(db)

    if last_run is None:
        return {"last_run": None, "is_running": False}

    return {
        "last_run": {
            "id": last_run.id,
            "job_type": last_run.job_type,
            "status": last_run.status,
            "symbols_processed": last_run.symbols_processed or 0,
            "total_symbols": last_run.total_symbols or 0,
            "errors": last_run.errors or 0,
            "error_details": last_run.error_details,
            "started_at": (
                last_run.started_at.isoformat() if last_run.started_at else None
            ),
            "completed_at": (
                last_run.completed_at.isoformat() if last_run.completed_at else None
            ),
        },
        "is_running": last_run.status == "running" if last_run else False,
    }
