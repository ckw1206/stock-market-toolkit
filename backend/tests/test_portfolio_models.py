from sqlalchemy import UniqueConstraint

import app.models  # noqa: F401  (imports register all models on Base)
from app.database import Base


def test_holdings_tables_registered():
    assert "portfolio_transactions" in Base.metadata.tables
    assert "portfolio_suggestion_dismissals" in Base.metadata.tables


def test_transactions_columns():
    cols = Base.metadata.tables["portfolio_transactions"].columns
    for name in ("id", "user_id", "type", "trade_date", "symbol", "qty",
                 "price", "amount", "fee", "currency", "note",
                 "created_at", "updated_at"):
        assert name in cols, f"missing column {name}"
    # Decimal-as-string: SQLite Numeric would round-trip through float
    assert str(cols["qty"].type) == "VARCHAR"
    assert str(cols["price"].type) == "VARCHAR"
    assert str(cols["amount"].type) == "VARCHAR"
    assert str(cols["fee"].type) == "VARCHAR"


def test_dismissal_unique_constraint():
    table = Base.metadata.tables["portfolio_suggestion_dismissals"]
    uqs = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    assert any(
        {col.name for col in c.columns} == {"user_id", "symbol", "type", "ex_date"}
        for c in uqs
    )
