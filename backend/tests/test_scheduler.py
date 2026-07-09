"""Regression: the in-process scheduler must register the alert check.

check_alerts was documented as "called every 15 minutes by external
scheduler", but no external scheduler exists — so alerts never fired
(same failure mode as issue #283 for the signal scan).
"""

import pytest

from app.scheduler import start_scheduler


@pytest.mark.asyncio
async def test_scheduler_registers_alert_check_and_signal_scan():
    scheduler = start_scheduler()
    try:
        job_ids = {job.id for job in scheduler.get_jobs()}
        assert "check_alerts" in job_ids
        assert "scan_signals" in job_ids
        # every 15 minutes
        check_job = scheduler.get_job("check_alerts")
        assert check_job.trigger.interval.total_seconds() == 15 * 60
    finally:
        scheduler.shutdown(wait=False)
