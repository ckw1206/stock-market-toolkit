"""Tests for the Discord alert embed content (multi-condition display, links)."""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.services.notification.discord import _build_discord_embed, describe_condition
from app.services.notification.email import _build_email_body

TRIGGERED_AT = datetime(2026, 7, 16, 4, 28, tzinfo=timezone.utc)


class TestDiscordEmbed:
    def test_multi_condition_embed_shows_matched_condition(self):
        embed = _build_discord_embed(
            symbol="00631L.TW",
            condition_type="multi",
            current_price=37.23,
            threshold=0.0,
            triggered_at=TRIGGERED_AT,
            pct_change_today=2.1,
            conditions_text="% Change crosses above 2.0%",
        )
        assert embed["title"] == "🔔 Price Alert: 00631L.TW"  # no raw "multi"
        field_names = [f["name"] for f in embed["fields"]]
        assert "Threshold" not in field_names  # no bogus 0.0%
        condition_field = next(f for f in embed["fields"] if f["name"] == "Condition")
        assert condition_field["value"] == "% Change crosses above 2.0%"

    def test_legacy_embed_unchanged(self):
        embed = _build_discord_embed(
            symbol="AAPL",
            condition_type="above",
            current_price=200.0,
            threshold=195.0,
            triggered_at=TRIGGERED_AT,
            pct_change_today=None,
        )
        assert "Above" in embed["title"]
        assert {"name": "Threshold", "value": "$195.00", "inline": True} in embed["fields"]

    def test_alert_url_points_to_frontend(self):
        embed = _build_discord_embed(None, None, None, None, None, None)
        assert embed["url"] == "https://stock.kylelabs.site/alerts"

    def test_describe_condition(self):
        assert describe_condition("pct_change", "crosses_above", 2.0) == "% Change crosses above 2.0%"
        assert describe_condition("price", "gt", 38.0) == "Price > $38"


class TestEmailMultiCondition:
    def test_email_body_lists_conditions(self):
        alert = SimpleNamespace(
            condition_type="multi",
            threshold=0.0,
            combinator="any",
            conditions=[
                SimpleNamespace(metric="price", operator="gt", value=38.0),
                SimpleNamespace(metric="pct_change", operator="crosses_above", value=2.0),
            ],
        )
        body = _build_email_body("00631L.TW", alert, 37.23, TRIGGERED_AT)
        assert "Price > $38 OR % Change crosses above 2.0%" in body
        assert "multi" not in body
        assert "stock.kylelabs.site/alerts" in body
