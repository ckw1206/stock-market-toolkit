"""Tests for market breadth aggregation and the /api/market/breadth endpoint."""

from datetime import date, datetime, timezone

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


def _result(price, sma50=None, sma200=None, prev_close=None, pct_change_1d=None, breakout=False):
    """Build a minimal ScanResult for breadth tests."""
    return ScanResult(
        symbol="X",
        signal="NEUTRAL",
        score=0.0,
        confidence=0.0,
        price=price,
        sma50=sma50,
        sma200=sma200,
        prev_close=prev_close,
        pct_change_1d=pct_change_1d,
        breakout=breakout,
        reasons=[],
    )


class TestComputeBreadth:
    def test_empty_results(self):
        stats = compute_breadth([])
        assert stats == {
            "pct_above_50dma": None,
            "pct_above_200dma": None,
            "advancers": 0,
            "decliners": 0,
            "new_highs": 0,
            "new_lows": 0,
        }

    def test_pct_above_50dma_and_200dma(self):
        results = [
            _result(price=110, sma50=100, sma200=105, prev_close=108),   # below 50dma, above 200dma, decliner
            _result(price=95, sma50=100, sma200=90, prev_close=93),    # below 50dma, above 200dma, advancer
            _result(price=105, sma50=100, sma200=100, prev_close=100), # above 50dma, above 200dma, flat
        ]
        stats = compute_breadth(results)
        assert stats["pct_above_50dma"] == 66.7  # 2/3 above 50-DMA
        assert stats["pct_above_200dma"] == 100.0  # all 3 above 200-DMA
        assert stats["advancers"] == 3
        assert stats["decliners"] == 0
        assert stats["new_highs"] == 0
        assert stats["new_lows"] == 0

    def test_advancers_decliners_from_prev_close(self):
        results = [
            _result(price=110, prev_close=100),   # advancer
            _result(price=90, prev_close=100),    # decliner
            _result(price=100, prev_close=100),   # flat (neither)
        ]
        stats = compute_breadth(results)
        assert stats["advancers"] == 1
        assert stats["decliners"] == 1

    def test_breakout_counts_as_new_high(self):
        results = [
            _result(price=200, breakout=True),
            _result(price=150, breakout=False),
        ]
        stats = compute_breadth(results)
        assert stats["new_highs"] == 1

    def test_missing_sma50_excluded_from_50dma_denominator(self):
        results = [
            _result(price=110, sma50=100),
            _result(price=50, sma50=None),  # no sma50 -> excluded from pct_above_50dma
        ]
        stats = compute_breadth(results)
        assert stats["pct_above_50dma"] == 100.0  # only the one with sma50 counts

    def test_all_missing_sma50_returns_none(self):
        results = [_result(price=110, sma50=None), _result(price=90, sma50=None)]
        stats = compute_breadth(results)
        assert stats["pct_above_50dma"] is None

    def test_prev_close_zero_skipped(self):
        """prev_close=0 would be a division error; such rows are excluded."""
        results = [
            _result(price=110, prev_close=0),
            _result(price=90, prev_close=100),
        ]
        stats = compute_breadth(results)
        assert stats["advancers"] == 0  # 0-close is excluded
        assert stats["decliners"] == 1


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
        db.add(MarketBreadth(
            date=date(2026, 6, 30),
            scan_id=older_scan.id,
            pct_above_50dma=40.0,
            pct_above_200dma=30.0,
            advancers=3,
            decliners=6,
            new_highs=0,
            new_lows=1,
        ))
        db.add(MarketBreadth(
            date=date(2026, 7, 1),
            scan_id=newer_scan.id,
            pct_above_50dma=70.0,
            pct_above_200dma=55.0,
            advancers=7,
            decliners=2,
            new_highs=2,
            new_lows=0,
        ))
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

        assert result["pct_above_50dma"] == 70.0
        assert result["pct_above_200dma"] == 55.0
        assert result["advancers"] == 7
        assert result["decliners"] == 2
        assert result["new_highs"] == 2
        assert result["new_lows"] == 0
        assert result["regime"] == "risk_on"
        assert len(result["history"]) == 2
        assert result["history"][0]["pct_above_50dma"] == 40.0
        assert result["history"][1]["pct_above_50dma"] == 70.0

    @pytest.mark.asyncio
    async def test_empty_when_no_scan(self, empty_sessionmaker):
        async with empty_sessionmaker() as db:
            result = await get_market_breadth(db)

        assert result["date"] is None
        assert result["regime"] == "neutral"
        assert result["history"] == []

    @pytest.mark.asyncio
    async def test_date_filter_returns_single_row(self, seeded_sessionmaker):
        async with seeded_sessionmaker() as db:
            result = await get_market_breadth(db, breadth_date=date(2026, 6, 30))

        assert result["date"] == "2026-06-30"
        assert result["pct_above_50dma"] == 40.0
        assert result["regime"] == "neutral"

    @pytest.mark.asyncio
    async def test_date_filter_missing_returns_error_dict(self, empty_sessionmaker):
        async with empty_sessionmaker() as db:
            result = await get_market_breadth(db, breadth_date=date(2026, 7, 1))

        assert result["error"] == "No breadth data for 2026-07-01"


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
        assert data["pct_above_50dma"] == 70.0
        assert data["pct_above_200dma"] == 55.0
        assert data["regime"] == "risk_on"
        assert len(data["history"]) == 2

    @pytest.mark.asyncio
    async def test_route_with_date_filter(self, client):
        resp = await client.get("/api/market/breadth", params={"breadth_date": "2026-06-30"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["date"] == "2026-06-30"
        assert data["pct_above_50dma"] == 40.0
        assert data["regime"] == "neutral"

    @pytest.mark.asyncio
    async def test_route_missing_date_returns_404_style_error(self, client):
        resp = await client.get("/api/market/breadth", params={"breadth_date": "2020-01-01"})
        assert resp.status_code == 200  # endpoint returns error dict, not HTTP error
        data = resp.json()
        assert "error" in data