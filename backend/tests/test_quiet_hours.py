"""Tests for the quiet-hours window logic."""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.quiet_hours import in_quiet_hours


def _settings(quiet_start=None, quiet_end=None, tz="UTC"):
    return SimpleNamespace(quiet_start=quiet_start, quiet_end=quiet_end, timezone=tz)


class TestInQuietHours:
    def test_no_settings_never_quiet(self):
        assert in_quiet_hours(None, datetime(2026, 7, 4, 2, 0, tzinfo=timezone.utc)) is False

    def test_unset_window_never_quiet(self):
        s = _settings()
        assert in_quiet_hours(s, datetime(2026, 7, 4, 2, 0, tzinfo=timezone.utc)) is False

    def test_simple_window_inside(self):
        s = _settings(quiet_start="09:00", quiet_end="17:00")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)) is True

    def test_simple_window_outside(self):
        s = _settings(quiet_start="09:00", quiet_end="17:00")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 20, 0, tzinfo=timezone.utc)) is False

    def test_simple_window_boundary_start_inclusive(self):
        s = _settings(quiet_start="09:00", quiet_end="17:00")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 9, 0, tzinfo=timezone.utc)) is True

    def test_simple_window_boundary_end_exclusive(self):
        s = _settings(quiet_start="09:00", quiet_end="17:00")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 17, 0, tzinfo=timezone.utc)) is False

    def test_wraparound_window_late_night(self):
        s = _settings(quiet_start="23:00", quiet_end="07:00")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 23, 30, tzinfo=timezone.utc)) is True

    def test_wraparound_window_early_morning(self):
        s = _settings(quiet_start="23:00", quiet_end="07:00")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 6, 30, tzinfo=timezone.utc)) is True

    def test_wraparound_window_daytime_not_quiet(self):
        s = _settings(quiet_start="23:00", quiet_end="07:00")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)) is False

    def test_invalid_format_disables_quiet_hours(self):
        s = _settings(quiet_start="bad", quiet_end="17:00")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)) is False

    def test_respects_user_timezone(self):
        # 09:00 UTC = 17:00 Asia/Taipei (UTC+8) — outside a 09:00-17:00 Taipei window.
        s = _settings(quiet_start="09:00", quiet_end="17:00", tz="Asia/Taipei")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 9, 0, tzinfo=timezone.utc)) is False
        # 09:00 UTC = 17:00 Taipei... let's use a value clearly inside instead:
        # 01:00 UTC = 09:00 Taipei — inside the window.
        assert in_quiet_hours(s, datetime(2026, 7, 4, 1, 0, tzinfo=timezone.utc)) is True

    def test_unknown_timezone_falls_back_to_utc(self):
        s = _settings(quiet_start="09:00", quiet_end="17:00", tz="Not/ARealZone")
        assert in_quiet_hours(s, datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc)) is True
