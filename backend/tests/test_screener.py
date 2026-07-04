"""Tests for /api/screener and /api/heatmap over the latest scan."""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import ScanResult, SignalScan, User
from app.routes import screener
from app.auth import get_current_user


SEED = [
    # symbol, signal, score, price, rsi, rvol, breakout, sma50, pct_52w, pct_1d, sector
    ("AAPL", "BUY", 1.0, 200.0, 65.0, 2.5, True, 190.0, -1.0, 1.2, "Technology"),
    ("MSFT", "BUY", 0.75, 400.0, 55.0, 1.1, False, 410.0, -5.0, 0.4, "Technology"),
    ("XOM", "SELL", -0.75, 100.0, 35.0, 1.8, False, 110.0, -20.0, -2.1, "Energy"),
    ("JPM", "NEUTRAL", 0.25, 150.0, 50.0, 0.9, False, 140.0, -8.0, 0.0, "Financials"),
    ("NEWCO", "BUY", 0.8, 10.0, 70.0, 3.0, True, 9.0, -0.5, 5.0, None),
]


def _make_result(scan, row):
    (symbol, signal, score, price, rsi, rvol, breakout, sma50, pct_52w, pct_1d, sector) = row
    return ScanResult(
        scan=scan,
        symbol=symbol,
        signal=signal,
        score=score,
        confidence=min(abs(score), 1.0),
        price=price,
        rsi=rsi,
        rvol=rvol,
        breakout=breakout,
        volume_spike=rvol > 2.0,
        sma20=price * 0.99,
        sma50=sma50,
        volume_ratio=rvol,
        pct_from_52w_high=pct_52w,
        pct_change_1d=pct_1d,
        sector=sector,
        reasons=[],
        rank=1,
    )


@pytest_asyncio.fixture
async def seeded_sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async with maker() as db:
        scan = SignalScan(scanned_at=datetime(2026, 7, 1, tzinfo=timezone.utc))
        for row in SEED:
            db.add(_make_result(scan, row))
        db.add(scan)
        await db.commit()

    yield maker
    await engine.dispose()


@pytest_asyncio.fixture
async def client(seeded_sessionmaker):
    app = FastAPI()
    app.include_router(screener.router)
    app.dependency_overrides[get_current_user] = lambda: User(
        id="u1", email="t@example.com"
    )
    with (
        patch("app.routes.screener.AsyncSessionLocal", seeded_sessionmaker),
        patch("app.services.top_signals.AsyncSessionLocal", seeded_sessionmaker),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c


@pytest_asyncio.fixture
async def empty_client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    app = FastAPI()
    app.include_router(screener.router)
    app.dependency_overrides[get_current_user] = lambda: User(
        id="u1", email="t@example.com"
    )
    with (
        patch("app.routes.screener.AsyncSessionLocal", maker),
        patch("app.services.top_signals.AsyncSessionLocal", maker),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
    await engine.dispose()


@pytest.mark.asyncio
async def test_screener_no_filters_returns_all_sorted_by_score_desc(client):
    resp = await client.get("/api/screener")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scanned_at"] is not None
    assert data["count"] == 5
    scores = [r["score"] for r in data["results"]]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_screener_combined_filters(client):
    resp = await client.get(
        "/api/screener", params={"signal": "BUY", "rvol_min": 2.0, "breakout": True}
    )
    data = resp.json()
    assert {r["symbol"] for r in data["results"]} == {"AAPL", "NEWCO"}


@pytest.mark.asyncio
async def test_screener_rsi_range_and_price(client):
    resp = await client.get(
        "/api/screener", params={"rsi_min": 40, "rsi_max": 60, "price_min": 120}
    )
    data = resp.json()
    assert {r["symbol"] for r in data["results"]} == {"MSFT", "JPM"}


@pytest.mark.asyncio
async def test_screener_above_sma50_both_directions(client):
    above = (await client.get("/api/screener", params={"above_sma50": True})).json()
    below = (await client.get("/api/screener", params={"above_sma50": False})).json()
    assert {r["symbol"] for r in above["results"]} == {"AAPL", "JPM", "NEWCO"}
    assert {r["symbol"] for r in below["results"]} == {"MSFT", "XOM"}


@pytest.mark.asyncio
async def test_screener_sector_and_52w_proximity(client):
    resp = await client.get(
        "/api/screener",
        params={"sector": "Technology", "pct_from_52w_high_min": -2.0},
    )
    data = resp.json()
    assert [r["symbol"] for r in data["results"]] == ["AAPL"]


@pytest.mark.asyncio
async def test_screener_sort_order_and_limit(client):
    resp = await client.get(
        "/api/screener", params={"sort": "rvol", "order": "asc", "limit": 2}
    )
    data = resp.json()
    assert [r["symbol"] for r in data["results"]] == ["JPM", "MSFT"]


@pytest.mark.asyncio
async def test_screener_gap_min_filters_by_pct_change_1d(client):
    resp = await client.get("/api/screener", params={"gap_min": 1.0})
    data = resp.json()
    # AAPL=1.2, NEWCO=5.0 clear the bar; MSFT=0.4, XOM=-2.1, JPM=0.0 don't.
    assert {r["symbol"] for r in data["results"]} == {"AAPL", "NEWCO"}


@pytest.mark.asyncio
async def test_screener_gap_max_filters_gap_downs(client):
    resp = await client.get("/api/screener", params={"gap_max": -1.0})
    data = resp.json()
    assert {r["symbol"] for r in data["results"]} == {"XOM"}


@pytest.mark.asyncio
async def test_screener_gap_and_go_requires_both_gap_and_rvol(client):
    resp = await client.get("/api/screener", params={"gap_and_go": True})
    data = resp.json()
    # Only NEWCO clears |gap|>=3% AND rvol>=2x (pct_1d=5.0, rvol=3.0).
    # AAPL has rvol=2.5 but gap=1.2 (< 3%); XOM has gap=-2.1 (< 3% abs).
    assert {r["symbol"] for r in data["results"]} == {"NEWCO"}


@pytest.mark.asyncio
async def test_screener_gap_and_go_flag_present_per_row(client):
    resp = await client.get("/api/screener", params={"sort": "pct_change_1d", "order": "desc"})
    data = resp.json()
    by_symbol = {r["symbol"]: r["gap_and_go"] for r in data["results"]}
    assert by_symbol["NEWCO"] is True
    assert by_symbol["AAPL"] is False
    assert by_symbol["XOM"] is False


@pytest.mark.asyncio
async def test_screener_invalid_sort_is_422(client):
    resp = await client.get("/api/screener", params={"sort": "market_cap"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_screener_empty_when_no_scan(empty_client):
    resp = await empty_client.get("/api/screener")
    assert resp.status_code == 200
    assert resp.json() == {"scanned_at": None, "count": 0, "results": []}


@pytest.mark.asyncio
async def test_heatmap_groups_by_sector_with_other_bucket_last(client):
    resp = await client.get("/api/heatmap")
    assert resp.status_code == 200
    data = resp.json()
    names = [s["sector"] for s in data["sectors"]]
    assert names == ["Energy", "Financials", "Technology", "Other"]
    other = data["sectors"][-1]
    assert [s["symbol"] for s in other["symbols"]] == ["NEWCO"]
    tech = data["sectors"][2]
    # tiles sorted by |pct_change_1d| desc
    assert [s["symbol"] for s in tech["symbols"]] == ["AAPL", "MSFT"]


@pytest.mark.asyncio
async def test_heatmap_empty_when_no_scan(empty_client):
    resp = await empty_client.get("/api/heatmap")
    assert resp.json() == {"scanned_at": None, "sectors": []}
