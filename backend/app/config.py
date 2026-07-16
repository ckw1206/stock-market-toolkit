import os
from functools import lru_cache


def _get_env(key: str, default: str) -> str:
    return os.getenv(key, default)


class Settings:
    DATABASE_URL: str = _get_env(
        "DATABASE_URL",
        "sqlite+aiosqlite:///./stocktoolkit.db",  # SQLite for local dev
    )
    SECRET_KEY: str = _get_env(
        "SECRET_KEY",
        "dev-secret-stocktoolkit-change-in-production-use-openssl-rand-hex-64",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]
    # Public URL of the frontend; used for links in notifications. Empty = no links.
    FRONTEND_URL: str = _get_env("FRONTEND_URL", "")
    LOG_LEVEL: str = _get_env("LOG_LEVEL", "INFO")
    IS_DOCKER: bool = _get_env("IS_DOCKER", "false").lower() == "true"
    ADMIN_EMAIL: str = _get_env("ADMIN_EMAIL", "admin@stocktoolkit.local")
    ADMIN_USERNAME: str = _get_env("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = _get_env("ADMIN_PASSWORD", "Admin@1234")
    INGEST_DELAY_SECONDS: float = float(_get_env("INGEST_DELAY_SECONDS", "1.5"))
    INGEST_MAX_SYMBOLS: int = int(_get_env("INGEST_MAX_SYMBOLS", "200"))
    ENCRYPTION_KEY: str = _get_env(
        "ENCRYPTION_KEY",
        "dev-encryption-key-stocktoolkit-change-in-production-openssl-rand-hex-64",
    )
    FINMIND_TOKEN: str = _get_env("FINMIND_TOKEN", "")
    # Comma-separated symbols for the nightly signal scan (mix US and .TW/.TWO
    # freely, e.g. "AAPL,NVDA,2330.TW"). Empty = built-in default US list.
    # User watchlist symbols are always scanned in addition to this list.
    SCAN_UNIVERSE: str = _get_env("SCAN_UNIVERSE", "")

    # ── Provider chain configuration ──────────────────────────────────
    PROVIDER_CHAIN: str = _get_env("PROVIDER_CHAIN", "default")
    PROVIDER_MAX_FAILURES: int = int(_get_env("PROVIDER_MAX_FAILURES", "3"))
    PROVIDER_COOLDOWN_SECONDS: float = float(
        _get_env("PROVIDER_COOLDOWN_SECONDS", "60")
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
