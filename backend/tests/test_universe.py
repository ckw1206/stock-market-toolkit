"""Unit tests for app.services.universe."""

from unittest.mock import MagicMock, patch

from app.services.universe import DEFAULT_TRACKED_SYMBOLS, get_tracked_universe


def _settings_with(scan_universe: str) -> MagicMock:
    settings = MagicMock()
    settings.SCAN_UNIVERSE = scan_universe
    return settings


def test_default_universe_when_env_unset():
    with patch("app.services.universe.get_settings", return_value=_settings_with("")):
        assert get_tracked_universe() == DEFAULT_TRACKED_SYMBOLS


def test_scan_universe_override_mixed_markets():
    with patch(
        "app.services.universe.get_settings",
        return_value=_settings_with("aapl, NVDA ,2330.tw,,2317.TW"),
    ):
        assert get_tracked_universe() == ["AAPL", "NVDA", "2330.TW", "2317.TW"]


def test_whitespace_only_override_falls_back_to_default():
    with patch("app.services.universe.get_settings", return_value=_settings_with("  ,  ")):
        assert get_tracked_universe() == DEFAULT_TRACKED_SYMBOLS
