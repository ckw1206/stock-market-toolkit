"""Tests for market breadth aggregation and the /api/market/breadth endpoint."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from unittest.mock import patch

from app.database import Base
from app.models import MarketBreadth, ScanResult, SignalScan, User
from app.routes import market
from app.auth import get_current_user
from app.services.market_breadth import classify_regime, compute_breadth, get_market_breadth


def _result(price, sma50, pct_change_1d, breakout=False):
    return ScanResult(
        symbol="X", signal="NEUTRAL", score=0.0, confidence=0.0,
        price=price, sma50=sma50, pct_change_1d=pct_change_1d, breakout=breakout,
        reasons=[],
    )


class TestComputeBreadth:
    def test_empty_results(self):
        stats = compute_breadth([])
        assert stats == {
            "total_symbols": 0,
            "pct_above_sma50": None,
            "advancers": 0,
            "decliners": 0,
            "new_highs": 0,
        }

    def test_pct_above_sma50_and_advance_decline(self):
        results = [
            _result(110, 100, 1.5),   # above sma50, advancer
            _result(90, 100, -0.5),   # below sma50, decliner
            _result(105, 100, 0.0),   # above sma50, flat (neither advancer nor decliner)
            _result(95, 100, 2.0, breakout=True),  # below sma50, advancer, breakout
        ]
        stats = compute_breadth(results)
        assert stats["total_symbols"] == 4
        assert stats["pct_above_sma50"] == 50.0
        assert stats["advancers"] == 2
        assert stats["decliners"] == 1
        assert stats["new_highs"] == 1

    def test_missing_sma50_excluded_from_denominator(self):
        results = [
            _result(110, 100, 1.0),
            _result(50, None, 1.0),  # no sma50 -> excluded from pct_above_sma50
        ]
        stats = compute_breadth(results)
        assert stats["pct_above_sma50"] == 100.0
        assert stats["total_symbols"] == 2

    def test_all_missing_sma50_returns_none(self):
        results = [_result(110, None, 1.0), _result(90, None, -1.0)]
        stats = compute_breadth(results)
        assert stats["pct_above_sma50"] is None


class TestClassifyRegime:
    def test_risk_on_above_threshold(self):
        assert classify_regime(75.0) == "risk_on"

    def test_risk_off_below_threshold(self):
        assert classify_regime(25.0) == "risk_off"

    def test_neutral_in_between(self):
        assert classify_regime(50.0) == "neutral"

    def test_none_is_neutral(self):
        assert classify_regime(None) == "neutral"


@pytest_asyncio.fixture
async def seeded_sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as db:
        older_scan = SignalScan(scanned_at=datetime(2026, 6, 30, tzinfo=timezone.utc))
        newer_scan = SignalScan(scanned_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
        db.add(older_scan)
        db.add(newer_scan)
        await db.flush()
        db.add(MarketBreadth(scan=older_scan, total_symbols=10, pct_above_sma50=40.0, advancers=3, decliners=6, new_highs=0))
        db.add(MarketBreadth(scan=newer_scan, total_symbols=10, pct_above_sma50=70.0, advancers=7, decliners=2, new_highs=2))
        await db.commit()

    yield maker
    await engine.dispose()


@pytest_asyncio.fixture
async def empty_sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


class TestGetMarketBreadth:
    @pytest.mark.asyncio
    async def test_returns_latest_snapshot_and_history_oldest_first(self, seeded_sessionmaker):
        async with seeded_sessionmaker() as db:
            result = await get_market_breadth(db)

        assert result["pct_above_sma50"] == 70.0
        assert result["advancers"] == 7
        assert result["regime"] == "risk_on"
        assert len(result["history"]) == 2
        assert result["history"][0]["pct_above_sma50"] == 40.0
        assert result["history"][1]["pct_above_sma50"] == 70.0

    @pytest.mark.asyncio
    async def test_empty_when_no_scan(self, empty_sessionmaker):
        async with empty_sessionmaker() as db:
            result = await get_market_breadth(db)

        assert result["scanned_at"] is None
        assert result["regime"] == "neutral"
        assert result["history"] == []


@pytest_asyncio.fixture
async def client(seeded_sessionmaker):
    app = FastAPI()
    app.include_router(market.router)
    app.dependency_overrides[get_current_user] = lambda: User(id="u1", email="t@example.com")
    with patch("app.routes.market.AsyncSessionLocal", seeded_sessionmaker):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


class TestBreadthRoute:
    @pytest.mark.asyncio
    async def test_route_returns_latest_breadth(self, client):
        resp = await client.get("/api/market/breadth")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pct_above_sma50"] == 70.0
        assert data["regime"] == "risk_on"
        assert len(data["history"]) == 2
