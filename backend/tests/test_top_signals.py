"""Unit tests for app.services.top_signals and /api/signals/top endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import SignalScan, ScanResult


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute = AsyncMock()
    db.execute.return_value = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    return db


def _mock_signal_result(symbol: str, signal: str, score: float) -> dict:
    return {
        "symbol": symbol,
        "period": "3mo",
        "signal": signal,
        "score": score,
        "confidence": min(abs(score), 1.0),
        "reasons": [f"Test reason for {symbol}"],
        "price": 100.0 + (hash(symbol) % 100),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "indicators": {
            "rvol": 1.5 + (hash(symbol) % 10) * 0.1,
        },
        "volume_spike": False,
        "breakout": False,
    }


@pytest.mark.asyncio
async def test_run_signal_scan_ranks_buys_and_sells():
    from app.services.top_signals import run_signal_scan

    mock_results = [
        _mock_signal_result("AAPL", "BUY", 0.5),
        _mock_signal_result("MSFT", "BUY", 0.9),
        _mock_signal_result("GOOGL", "SELL", -0.3),
        _mock_signal_result("AMZN", "SELL", -0.8),
    ]

    with (
        patch("app.services.top_signals.AsyncSessionLocal") as mock_session,
        patch("app.services.top_signals.get_scan_universe", AsyncMock(return_value=["AAPL", "MSFT", "GOOGL", "AMZN"])),
        patch("app.services.top_signals.compute_signal_for_symbol", AsyncMock(side_effect=mock_results)),
        patch("app.services.top_signals.get_settings") as mock_settings,
        patch("app.services.top_signals.get_sector", AsyncMock(return_value="Technology")),
    ):
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.execute.return_value = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_db
        mock_settings.return_value.INGEST_DELAY_SECONDS = 0

        result = await run_signal_scan()

    assert result["symbols_processed"] == 4
    assert result["buys"] == 2
    assert result["sells"] == 2


@pytest.mark.asyncio
async def test_run_signal_scan_tolerates_provider_failure():
    from app.services.top_signals import run_signal_scan

    async def mock_signal(symbol, period="3mo"):
        if symbol == "FAIL":
            raise RuntimeError("Provider unavailable")
        return _mock_signal_result(symbol, "BUY", 0.5)

    with (
        patch("app.services.top_signals.AsyncSessionLocal") as mock_session,
        patch("app.services.top_signals.get_scan_universe", AsyncMock(return_value=["AAPL", "FAIL", "GOOGL"])),
        patch("app.services.top_signals.compute_signal_for_symbol", mock_signal),
        patch("app.services.top_signals.get_settings") as mock_settings,
        patch("app.services.top_signals.get_sector", AsyncMock(return_value="Technology")),
    ):
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        mock_db.execute.return_value = MagicMock()
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.__aenter__ = AsyncMock(return_value=mock_db)
        mock_db.__aexit__ = AsyncMock(return_value=None)
        mock_session.return_value = mock_db
        mock_settings.return_value.INGEST_DELAY_SECONDS = 0

        result = await run_signal_scan()

    assert result["symbols_processed"] == 2
    assert result["errors"] == 1


@pytest.mark.asyncio
async def test_get_top_signals_returns_empty_when_no_scan(mock_db):
    from app.services.top_signals import get_top_signals

    mock_db.execute.return_value.scalar_one_or_none.return_value = None

    result = await get_top_signals(mock_db)

    assert result["scanned_at"] is None
    assert result["buys"] == []
    assert result["sells"] == []


@pytest.mark.asyncio
async def test_get_top_signals_returns_latest_scan(mock_db):
    from app.services.top_signals import get_top_signals

    scan = SignalScan(id=1, scanned_at=datetime.now(timezone.utc))
    scan_results = [
        ScanResult(id=1, scan_id=1, symbol="AAPL", signal="BUY", score=0.8, confidence=0.8, price=150.0, rvol=1.5, breakout=False, volume_spike=False, reasons=["Reason"], rank=1),
        ScanResult(id=2, scan_id=1, symbol="MSFT", signal="SELL", score=-0.6, confidence=0.6, price=300.0, rvol=2.0, breakout=True, volume_spike=True, reasons=["Reason"], rank=1),
    ]

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = scan_results

    mock_results_result = MagicMock()
    mock_results_result.scalars.return_value = mock_scalars

    mock_scan_result = MagicMock()
    mock_scan_result.scalar_one_or_none.return_value = scan

    mock_db.execute.side_effect = [mock_scan_result, mock_results_result]

    result = await get_top_signals(mock_db, limit=10)

    assert result["scanned_at"] is not None
    assert len(result["buys"]) == 1
    assert len(result["sells"]) == 1


@pytest_asyncio.fixture
async def sessionmaker():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_top_signals_ignores_empty_later_scan(sessionmaker):
    """A newer scan that persisted zero results must not mask the last good scan.

    Regression: a nightly run where every provider is rate-limited still writes a
    SignalScan row (fresh scanned_at) with no ScanResults. get_latest_scan used to
    return it, so the dashboard showed "no signal data" despite the prior scan
    having buys/sells.
    """
    from app.services.top_signals import get_top_signals

    async with sessionmaker() as db:
        good = SignalScan(scanned_at=datetime(2026, 7, 9, tzinfo=timezone.utc))
        db.add(good)
        await db.flush()
        db.add(ScanResult(scan_id=good.id, symbol="AAPL", signal="BUY", score=0.8, confidence=0.8, price=150.0, rank=1))
        # Newer, but empty (no results).
        db.add(SignalScan(scanned_at=datetime(2026, 7, 10, tzinfo=timezone.utc)))
        await db.commit()

        result = await get_top_signals(db, limit=10)

    assert len(result["buys"]) == 1
    assert result["buys"][0]["symbol"] == "AAPL"
    assert result["scanned_at"].startswith("2026-07-09")


@pytest.mark.asyncio
async def test_cron_scan_signals_dedupe():
    """When a signal_scan job is already running, the endpoint should skip."""
    from app.routes.cron import cron_scan_signals

    existing_job = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_job

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("app.database.AsyncSessionLocal") as mock_session,
    ):
        mock_session.return_value = mock_db
        response = await cron_scan_signals()

    assert response == {"status": "skipped", "message": "Signal scan already running"}


@pytest.mark.asyncio
async def test_cron_scan_signals_success():
    """When no job is running, a new scan should be started."""
    from app.routes.cron import cron_scan_signals

    mock_scan_result = MagicMock()
    mock_scan_result.scalar_one_or_none.return_value = None

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_scan_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("app.database.AsyncSessionLocal") as mock_session,
        patch("app.services.top_signals.run_signal_scan", AsyncMock(return_value={"scan_id": 1, "symbols_processed": 5, "total_symbols": 5, "errors": 0, "buys": 3, "sells": 2})),
    ):
        mock_session.return_value = mock_db
        response = await cron_scan_signals()

    assert response["status"] == "ok"
    assert response["symbols_processed"] == 5


@pytest.mark.asyncio
async def test_compute_signal_for_symbol_returns_score_key():
    """Test that compute_signal_for_symbol returns a dict with 'score' key.

    This is a regression test for the bug where build_signal_result did not
    include 'score' in its output, causing KeyError when run_signal_scan
    tried to read signal_data['score'].
    """
    from app.services.top_signals import compute_signal_for_symbol
    from app.providers.chain import FallbackChain, TaggedValue

    import pandas as pd

    n = 60
    df = pd.DataFrame({
        "Open":   [150.0 + i * 0.1 for i in range(n)],
        "High":   [152.0 + i * 0.1 for i in range(n)],
        "Low":    [149.0 + i * 0.1 for i in range(n)],
        "Close":  [151.0 + i * 0.1 for i in range(n)],
        "Volume": [1_000_000 + i * 10_000 for i in range(n)],
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

    async def mock_get_history(symbol, period, interval):
        return TaggedValue(df, "yfinance", datetime.utcnow())

    with patch("app.services.signals.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(side_effect=mock_get_history)

        result = await compute_signal_for_symbol("AAPL", period="3mo")

    assert result is not None
    assert "score" in result, "build_signal_result must return 'score' key"
    assert "signal" in result
    assert "confidence" in result
    assert "price" in result
    assert "indicators" in result
    assert result["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_cron_scan_signals_marks_failed_on_exception():
    """When run_signal_scan raises, the JobRun should be marked as failed."""
    from app.routes.cron import cron_scan_signals

    mock_scan_result = MagicMock()
    mock_scan_result.scalar_one_or_none.return_value = None

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_scan_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("app.database.AsyncSessionLocal") as mock_session,
        patch("app.services.top_signals.run_signal_scan", AsyncMock(side_effect=RuntimeError("Scan failed"))),
    ):
        mock_session.return_value = mock_db
        response = await cron_scan_signals()

    assert response["status"] == "error"
    assert "Scan failed" in response["message"]