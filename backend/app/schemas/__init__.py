"""Re-export all schemas from submodules for backward compatibility."""
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    TokenResponse,
    RefreshRequest,
    UserResponse,
)
from app.schemas.stock import (
    StockDataResponse,
    IndicatorsResponse,
    StockInfoResponse,
    CompareRequest,
    CompareStockData,
    CompareResponse,
)
from app.schemas.fundamentals import (
    ProfitabilityMetrics,
    DividendQualityDetails,
    FundamentalsResponse,
    YearlyDividend,
    DividendsResponse,
    FinancialStatementResponse,
    DividendResponse,
    SymbolScoreResponse,
    MonthlyRevenueResponse,
)
from app.schemas.news import (
    NewsArticle,
    NewsResponse,
)
from app.schemas.alert import (
    AlertConditionCreate,
    AlertConditionResponse,
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertSnoozeRequest,
    TriggeredAlertResponse,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    NotificationDeliveryResponse,
    DiscordTestRequest,
)
from app.schemas.admin import (
    InviteCodeCreate,
    InviteCodeResponse,
    InviteCodeListResponse,
    InviteSendRequest,
    InviteSendResponse,
    InviteRevokeRequest,
    AuditLogResponse,
    AuditLogListResponse,
    SmtpSettingsResponse,
    SmtpSettingsUpdate,
    SmtpTestRequest,
    SmtpTestResponse,
)
from app.schemas.watchlist import (
    WatchlistCreate,
    WatchlistUpdate,
    WatchlistResponse,
)
from app.schemas.ingestion import (
    JobRunResponse,
    IngestStatusResponse,
)
from app.schemas.paper import PaperTradeRequest, PaperPortfolioCreate

__all__ = [
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
    "AlertResponse", "AlertSnoozeRequest", "TriggeredAlertResponse", "NotificationSettingsResponse",
    "NotificationSettingsUpdate", "NotificationDeliveryResponse", "DiscordTestRequest",
    # admin
    "InviteCodeCreate", "InviteCodeResponse", "InviteCodeListResponse",
    "InviteSendRequest", "InviteSendResponse", "InviteRevokeRequest",
    "AuditLogResponse", "AuditLogListResponse", "SmtpSettingsResponse",
    "SmtpSettingsUpdate", "SmtpTestRequest", "SmtpTestResponse",
    # watchlist
    "WatchlistCreate", "WatchlistUpdate", "WatchlistResponse",
    # ingestion
    "JobRunResponse", "IngestStatusResponse",
    # paper trading
    "PaperTradeRequest", "PaperPortfolioCreate",
]
