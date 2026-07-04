"""Regression guard for the models package split (Issue #214)."""
from app.database import Base
from app import models

EXPECTED_MODELS = [
    "User", "Watchlist", "Alert", "AlertCondition", "NotificationSettings",
    "TriggeredAlert", "NotificationDelivery", "InviteCode", "FinancialStatement",
    "Dividend", "SymbolScore", "MonthlyRevenue", "JobRun", "SmtpSettings", "AuditLog",
    "SignalScan", "ScanResult", "MarketBreadth", "PaperPortfolio", "PaperTrade",
]
EXPECTED_TABLES = [
    "users", "watchlists", "alerts", "alert_conditions", "notification_settings",
    "triggered_alerts", "notification_deliveries", "invite_codes",
    "financial_statements", "dividends", "symbol_scores", "monthly_revenue",
    "job_runs", "smtp_settings", "audit_logs",
    "signal_scans", "scan_results", "market_breadth",
    "paper_portfolios", "paper_trades",
]

def test_all_models_importable():
    for name in EXPECTED_MODELS:
        assert hasattr(models, name), f"app.models missing {name}"

def test_package_exports_match_expected():
    # __all__ minus the re-exported Base must equal the expected model set;
    # catches a model added to a submodule but forgotten in models/__init__.py.
    exported = [name for name in models.__all__ if name != "Base"]
    assert set(exported) == set(EXPECTED_MODELS)
    assert len(exported) == 20

def test_tables_registered_and_no_drift():
    assert set(Base.metadata.tables.keys()) == set(EXPECTED_TABLES)
