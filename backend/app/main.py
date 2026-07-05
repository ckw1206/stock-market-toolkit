"""
Stock Market Toolkit — FastAPI Backend (Production)
"""

from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
import logging
from logging.handlers import RotatingFileHandler

from app import __version__
from app.config import get_settings
from app.routes import (
    auth,
    stocks,
    stock_info,
    search,
    news,
    alerts,
    mcp,
    analysis,
    admin,
    watchlist,
    cron,
    signals,
    screener,
    market,
    paper,
)
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.access_log import AccessLogMiddleware

settings = get_settings()
log = structlog.get_logger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


def setup_logging() -> None:
    log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    SECRET_WORDS = {"password", "token", "secret", "key", "authorization"}

    def scrub_secrets(logger, method_name, event_dict):
        for key in list(event_dict.keys()):
            if isinstance(key, str):
                key_lower = key.lower()
                if any(w in key_lower for w in SECRET_WORDS):
                    event_dict[key] = "***"
        return event_dict

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            scrub_secrets,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    file_handler = RotatingFileHandler(
        log_dir / "app.json",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
    )
    file_handler.setLevel(logging.DEBUG)

    json_formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
    )
    file_handler.setFormatter(json_formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    log.info("Running database migrations...")
    from alembic import command
    from alembic.config import Config

    # Run Alembic in-process (no dependency on the `alembic` binary being on
    # PATH or on the working directory). A failed migration must abort startup
    # rather than let the app boot against a missing/half-applied schema.
    backend_dir = Path(__file__).parent.parent
    alembic_cfg = Config(str(backend_dir / "alembic.ini"))
    try:
        command.upgrade(alembic_cfg, "heads")
    except Exception:
        log.exception("Alembic migration failed; aborting startup")
        raise
    log.info("Migrations complete. Stock Market Toolkit API started.")

    from app.scheduler import start_scheduler, scheduler

    start_scheduler()
    yield
    scheduler.shutdown()
    log.info("Shutting down Stock Market Toolkit API...")


app = FastAPI(
    title="Stock Market Toolkit API",
    description="Production stock market analysis API with user authentication",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,
    lifespan=lifespan,
)

# ─── Middleware ───
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware)
app.add_middleware(AccessLogMiddleware)

# Rate limit exceeded handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ─── Routes ───
app.include_router(auth.router)
app.include_router(stocks.router)
app.include_router(stock_info.router)
app.include_router(search.router)
app.include_router(news.router)
app.include_router(alerts.router)
app.include_router(mcp.router)
app.include_router(analysis.router)
app.include_router(watchlist.router)
app.include_router(admin.router)
app.include_router(cron.router)
app.include_router(signals.router)
app.include_router(screener.router)
app.include_router(market.router)
app.include_router(paper.router)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "stock-market-toolkit-api",
        "version": __version__,
    }


@app.get("/")
async def root():
    return {
        "name": "Stock Market Toolkit API",
        "version": __version__,
        "docs": "/docs",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )



