"""Regression guard for the schemas package split (Issue #2)."""
from app import schemas

EXPECTED_SCHEMAS = [
    # auth
    "UserRegister", "UserLogin", "TokenResponse", "RefreshRequest", "UserResponse",
    # stock
    "StockDataResponse", "IndicatorsResponse", "StockInfoResponse",
    "CompareRequest", "CompareStockData", "CompareResponse",
    # fundamentals
    "ProfitabilityMetrics", "DividendQualityDetails", "FundamentalsResponse",
    "YearlyDividend", "DividendsResponse", "FinancialStatementResponse",
    "DividendResponse", "SymbolScoreResponse", "MonthlyRevenueResponse",
    # news
    "NewsArticle", "NewsResponse",
    # alert
    "AlertConditionCreate", "AlertConditionResponse", "AlertCreate", "AlertUpdate",
    "AlertResponse", "TriggeredAlertResponse", "NotificationSettingsResponse",
    "NotificationSettingsUpdate", "NotificationDeliveryResponse", "DiscordTestRequest",
    # admin
    "InviteCodeCreate", "InviteCodeResponse", "InviteCodeListResponse",
    "InviteSendRequest", "InviteSendResponse", "InviteRevokeRequest",
    "AuditLogResponse", "AuditLogListResponse", "SmtpSettingsResponse",
    "SmtpSettingsUpdate", "SmtpTestRequest", "SmtpTestResponse",
    # watchlist
    "WatchlistCreate", "WatchlistResponse",
    # ingestion
    "JobRunResponse", "IngestStatusResponse",
    # paper trading
    "PaperTradeRequest",
]


def test_all_schemas_importable():
    for name in EXPECTED_SCHEMAS:
        assert hasattr(schemas, name), f"app.schemas missing {name}"


def test_package_exports_match_expected():
    assert set(schemas.__all__) == set(EXPECTED_SCHEMAS)
    assert len(EXPECTED_SCHEMAS) == 49
