"""Quiet-hours window logic — used by the alert checker to hold notification
dispatch during a user's configured quiet window and catch up afterward.
"""

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def _parse_hhmm(value: str | None) -> time | None:
    if not value:
        return None
    try:
        hh, mm = value.split(":")
        return time(hour=int(hh), minute=int(mm))
    except (ValueError, AttributeError):
        return None


def _local_time(settings, when_utc: datetime) -> time:
    tz_name = getattr(settings, "timezone", None) or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        tz = ZoneInfo("UTC")
    # SQLite doesn't preserve tzinfo across a write/read round-trip for
    # DateTime(timezone=True) columns, so a naive `when_utc` can arrive here
    # even though it was always written as UTC. `naive.astimezone(tz)` would
    # otherwise (wrongly) assume the *system's local* zone as the source.
    if when_utc.tzinfo is None:
        when_utc = when_utc.replace(tzinfo=timezone.utc)
    return when_utc.astimezone(tz).time()


def in_quiet_hours(settings, when_utc: datetime) -> bool:
    """Whether `when_utc` falls within `settings`' configured quiet-hours
    window, interpreted in the user's own timezone.

    A window where quiet_start > quiet_end wraps past midnight (e.g.
    23:00-07:00). No settings, or either bound unset/unparseable, means quiet
    hours are disabled (never quiet).
    """
    if settings is None:
        return False

    start = _parse_hhmm(getattr(settings, "quiet_start", None))
    end = _parse_hhmm(getattr(settings, "quiet_end", None))
    if start is None or end is None:
        return False

    t = _local_time(settings, when_utc)
    if start <= end:
        return start <= t < end
    return t >= start or t < end
