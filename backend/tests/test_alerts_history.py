"""Tests for GET /api/alerts/history — CSV export and pagination (issue #266)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth import get_current_user
from app.database import get_db
from app.models import User, TriggeredAlert


@pytest.fixture
def mock_user():
    return User(id="user-1", email="a@b.com", username="test", hashed_password="x")


@pytest.fixture
def client(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


def _make_triggered(id, symbol, triggered_at=None, **kwargs) -> TriggeredAlert:
    return TriggeredAlert(
        id=id,
        alert_id=1,
        user_id="user-1",
        symbol=symbol,
        condition_type="above",
        trigger_price=150.0,
        threshold_value=100.0,
        triggered_at=triggered_at or datetime(2026, 6, 1, tzinfo=timezone.utc),
        notified=True,
        read=False,
        **kwargs,
    )


def _mock_execute(rows):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = rows
    return AsyncMock(return_value=mock_result)


class TestAlertHistoryJSON:
    def test_returns_items_and_total(self, client):
        rows = [_make_triggered(1, "AAPL"), _make_triggered(2, "MSFT")]

        def override_get_db():
            count_result = MagicMock()
            count_result.scalar.return_value = 2
            return MagicMock(
                execute=AsyncMock(
                    side_effect=[
                        _mock_execute(rows),
                        AsyncMock(return_value=count_result),
                    ]
                )
            )

        app.dependency_overrides[get_db] = override_get_db
        try:
            res = client.get("/api/alerts/history")
        finally:
            del app.dependency_overrides[get_db]

        assert res.status_code == 200
        body = res.json()
        assert "items" in body
        assert body["total"] == 2

    def test_pagination_params_passed(self, client):
        def override_get_db():
            count_result = MagicMock()
            count_result.scalar.return_value = 0
            return MagicMock(
                execute=AsyncMock(
                    side_effect=[
                        _mock_execute([]),
                        AsyncMock(return_value=count_result),
                    ]
                )
            )

        app.dependency_overrides[get_db] = override_get_db
        try:
            res = client.get("/api/alerts/history?limit=10&offset=20")
        finally:
            del app.dependency_overrides[get_db]

        body = res.json()
        assert body["limit"] == 10
        assert body["offset"] == 20


class TestAlertHistoryCSV:
    def test_csv_returns_text_csv_with_attachment_header(self, client):
        rows = [_make_triggered(1, "AAPL")]

        def override_get_db():
            return MagicMock(execute=AsyncMock(return_value=_mock_execute(rows)))

        app.dependency_overrides[get_db] = override_get_db
        try:
            res = client.get("/api/alerts/history?format=csv")
        finally:
            del app.dependency_overrides[get_db]

        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
        assert "attachment" in res.headers.get("content-disposition", "")
        assert "alert_history.csv" in res.headers["content-disposition"]

    def test_csv_contains_header_and_data_rows(self, client):
        rows = [_make_triggered(1, "AAPL"), _make_triggered(2, "MSFT")]

        def override_get_db():
            return MagicMock(execute=AsyncMock(return_value=_mock_execute(rows)))

        app.dependency_overrides[get_db] = override_get_db
        try:
            res = client.get("/api/alerts/history?format=csv")
        finally:
            del app.dependency_overrides[get_db]

        lines = res.text.strip().split("\n")
        assert len(lines) == 3
        assert "id" in lines[0]
        assert "symbol" in lines[0]
        assert "AAPL" in lines[1]

    def test_csv_empty_rows_still_returns_200(self, client):
        def override_get_db():
            return MagicMock(execute=AsyncMock(return_value=_mock_execute([])))

        app.dependency_overrides[get_db] = override_get_db
        try:
            res = client.get("/api/alerts/history?format=csv")
        finally:
            del app.dependency_overrides[get_db]

        assert res.status_code == 200
        assert res.headers["content-type"].startswith("text/csv")
