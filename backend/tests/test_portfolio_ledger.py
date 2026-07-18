# backend/tests/test_portfolio_ledger.py
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from app.services.portfolio_ledger import ZERO, replay

_ids = iter(range(1, 10_000))


def txn(type_, trade_date, **kw):
    return SimpleNamespace(
        id=kw.pop("id", next(_ids)),
        type=type_,
        trade_date=date.fromisoformat(trade_date),
        symbol=kw.get("symbol"),
        qty=kw.get("qty"),
        price=kw.get("price"),
        amount=kw.get("amount"),
        fee=kw.get("fee", "0"),
        currency=kw.get("currency", "USD"),
    )


def test_buy_avg_cost_includes_fee():
    state = replay([txn("buy", "2026-01-05", symbol="AAPL", qty="10", price="100", fee="5")])
    pos = state.positions["AAPL"]
    assert pos.qty == Decimal("10")
    assert pos.avg_cost == Decimal("100.5")           # (10*100 + 5) / 10
    assert state.cash["USD"] == Decimal("-1005")


def test_second_buy_pools_avg_cost():
    state = replay([
        txn("buy", "2026-01-05", symbol="AAPL", qty="10", price="100", fee="5"),
        txn("buy", "2026-01-06", symbol="AAPL", qty="10", price="110"),
    ])
    assert state.positions["AAPL"].avg_cost == Decimal("105.25")  # (1005+1100)/20


def test_sell_realizes_pnl_and_keeps_avg():
    state = replay([
        txn("buy", "2026-01-05", symbol="AAPL", qty="20", price="100"),
        txn("sell", "2026-02-01", symbol="AAPL", qty="5", price="120", fee="3"),
    ])
    pos = state.positions["AAPL"]
    assert pos.qty == Decimal("15")
    assert pos.avg_cost == Decimal("100")
    assert pos.realized_pnl == Decimal("97")          # 5*(120-100) - 3
    assert state.cash["USD"] == Decimal("-2000") + Decimal("597")


def test_sell_to_zero_clears_avg_cost():
    state = replay([
        txn("buy", "2026-01-05", symbol="AAPL", qty="10", price="100"),
        txn("sell", "2026-02-01", symbol="AAPL", qty="10", price="110"),
    ])
    pos = state.positions["AAPL"]
    assert pos.qty == ZERO
    assert pos.avg_cost is None


def test_dividend_adds_cash_and_counter():
    state = replay([
        txn("buy", "2026-01-05", symbol="2330.TW", qty="1000", price="600", currency="TWD"),
        txn("dividend", "2026-03-10", symbol="2330.TW", amount="3500", currency="TWD"),
    ])
    assert state.positions["2330.TW"].dividends == Decimal("3500")
    assert state.cash["TWD"] == Decimal("-600000") + Decimal("3500")


def test_deposit_and_withdrawal():
    state = replay([
        txn("deposit", "2026-01-01", amount="10000", currency="USD"),
        txn("withdrawal", "2026-01-15", amount="2500", currency="USD"),
    ])
    assert state.cash["USD"] == Decimal("7500")


def test_split_scales_qty_and_avg():
    state = replay([
        txn("buy", "2026-01-05", symbol="NVDA", qty="10", price="1200"),
        txn("split", "2026-06-10", symbol="NVDA", qty="4"),
    ])
    pos = state.positions["NVDA"]
    assert pos.qty == Decimal("40")
    assert pos.avg_cost == Decimal("300")


def test_buy_from_oversold_resets_basis_no_zero_division():
    state = replay([
        txn("sell", "2026-01-05", symbol="AAPL", qty="10", price="100"),
        txn("buy", "2026-01-06", symbol="AAPL", qty="10", price="100"),
    ])
    pos = state.positions["AAPL"]
    assert pos.qty == ZERO
    assert pos.avg_cost is None
    state2 = replay([
        txn("sell", "2026-01-05", symbol="AAPL", qty="5", price="100"),
        txn("buy", "2026-01-06", symbol="AAPL", qty="10", price="50", fee="10"),
    ])
    pos2 = state2.positions["AAPL"]
    assert pos2.qty == Decimal("5")
    assert pos2.avg_cost == Decimal("51")             # (10*50 + 10) / 10


def test_multi_currency_cash_is_separate():
    state = replay([
        txn("deposit", "2026-01-01", amount="10000", currency="USD"),
        txn("deposit", "2026-01-01", amount="300000", currency="TWD"),
        txn("buy", "2026-01-05", symbol="2330.TW", qty="100", price="600", currency="TWD"),
    ])
    assert state.cash["USD"] == Decimal("10000")
    assert state.cash["TWD"] == Decimal("240000")


def test_decimal_precision_no_float_drift():
    state = replay([
        txn("buy", "2026-01-05", symbol="AAPL", qty="3", price="0.1"),
        txn("buy", "2026-01-06", symbol="AAPL", qty="3", price="0.2"),
    ])
    assert state.cash["USD"] == Decimal("-0.9")       # would fail with floats


def test_negative_cash_and_position_warnings():
    state = replay([
        txn("buy", "2026-01-05", symbol="AAPL", qty="10", price="100"),   # cash -1000
        txn("sell", "2026-01-06", symbol="AAPL", qty="15", price="50"),   # pos -5, cash -250
    ])
    assert state.cash["USD"] == Decimal("-250")  # ends negative -> warning kept
    kinds = {w.kind for w in state.warnings}
    assert "negative_cash" in kinds
    assert "negative_position" in kinds
    neg_pos = next(w for w in state.warnings if w.kind == "negative_position")
    assert neg_pos.symbol == "AAPL"
    assert neg_pos.trade_date == date(2026, 1, 6)


def test_negative_cash_cleared_when_balance_recovers():
    # Buy with no starting cash, then sell higher: the balance ends positive,
    # so the transient negative-cash warning is suppressed.
    state = replay([
        txn("buy", "2026-05-02", symbol="AAPL", qty="10", price="54"),    # cash -540
        txn("sell", "2026-06-01", symbol="AAPL", qty="10", price="67.5"),  # cash +135
    ])
    assert state.cash["USD"] == Decimal("135")
    assert not any(w.kind == "negative_cash" for w in state.warnings)


def test_adjust_position_overrides_and_resets_reporting():
    state = replay([
        txn("buy", "2026-01-05", symbol="AAPL", qty="10", price="100"),
        txn("sell", "2026-01-20", symbol="AAPL", qty="5", price="150"),   # realized 250
        txn("dividend", "2026-02-01", symbol="AAPL", amount="10"),
        txn("adjust", "2026-03-01", symbol="AAPL", qty="20", price="90"),
        txn("sell", "2026-04-01", symbol="AAPL", qty="5", price="100"),
    ])
    pos = state.positions["AAPL"]
    assert pos.qty == Decimal("15")
    assert pos.avg_cost == Decimal("90")
    assert pos.realized_pnl == Decimal("50")   # only the post-adjust sell
    assert pos.dividends == ZERO               # reset by the checkpoint


def test_adjust_cash_sets_balance():
    state = replay([
        txn("deposit", "2026-01-01", amount="1000", currency="USD"),
        txn("adjust", "2026-02-01", amount="9999", currency="USD"),
    ])
    assert state.cash["USD"] == Decimal("9999")


def test_warnings_before_adjust_are_suppressed():
    state = replay([
        txn("sell", "2026-01-05", symbol="AAPL", qty="10", price="100"),  # neg pos + cash ok? cash +1000
        txn("adjust", "2026-02-01", symbol="AAPL", qty="5", price="100"),
    ])
    assert not [w for w in state.warnings if w.kind == "negative_position"]


def test_warnings_after_adjust_survive():
    state = replay([
        txn("adjust", "2026-01-01", symbol="AAPL", qty="5", price="100"),
        txn("sell", "2026-02-01", symbol="AAPL", qty="10", price="100"),
    ])
    assert [w for w in state.warnings if w.kind == "negative_position"]


def test_adjust_sorts_last_within_its_date():
    # the adjust row was inserted FIRST (lower id) but dated same day as the
    # buy — it must still apply after the buy
    state = replay([
        txn("adjust", "2026-01-05", symbol="AAPL", qty="7", price="50", id=1),
        txn("buy", "2026-01-05", symbol="AAPL", qty="100", price="100", id=2),
    ])
    assert state.positions["AAPL"].qty == Decimal("7")


def test_mixed_currency_warning_and_latest_wins():
    state = replay([
        txn("buy", "2026-01-05", symbol="AAPL", qty="1", price="100", currency="USD"),
        txn("buy", "2026-01-06", symbol="AAPL", qty="1", price="100", currency="TWD"),
    ])
    assert [w for w in state.warnings if w.kind == "mixed_currency"]
    assert state.positions["AAPL"].currency == "TWD"