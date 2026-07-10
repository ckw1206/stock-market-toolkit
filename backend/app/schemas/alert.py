from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from datetime import datetime
from typing import Optional


class AlertConditionCreate(BaseModel):
    metric: str = Field(..., pattern="^(price|rsi|macd_hist|signal|pct_change|rvol)$")
    operator: str = Field(..., pattern="^(gt|lt|crosses_above|eq)$")
    value: float


class AlertConditionResponse(BaseModel):
    id: int
    alert_id: int
    metric: str
    operator: str
    value: float

    class Config:
        from_attributes = True


class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    symbol_name: Optional[str] = Field(None, max_length=200)
    condition_type: Optional[str] = Field(
        None, pattern="^(above|below|pct_change_up|pct_change_down)$"
    )
    threshold: Optional[float] = Field(
        None, description="Price threshold or percentage change threshold"
    )
    period: str = Field(default="1h", pattern="^(5m|15m|30m|1h|4h|1d)$")
    combinator: str = Field(default="all", pattern="^(all|any)$")
    conditions: list[AlertConditionCreate] = []

    @field_validator("symbol")
    @classmethod
    def symbol_upper(cls, v: str) -> str:
        return v.upper()


class AlertUpdate(BaseModel):
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    condition_type: Optional[str] = Field(
        None, pattern="^(above|below|pct_change_up|pct_change_down|multi)$"
    )
    threshold: Optional[float] = None
    period: Optional[str] = Field(None, pattern="^(5m|15m|30m|1h|4h|1d)$")
    enabled: Optional[bool] = None
    combinator: Optional[str] = Field(None, pattern="^(all|any)$")
    conditions: Optional[list[AlertConditionCreate]] = None


class AlertResponse(BaseModel):
    id: int
    user_id: str
    symbol: str
    symbol_name: Optional[str] = None
    condition_type: str
    threshold: float
    period: str
    enabled: bool
    combinator: Optional[str] = "all"
    conditions: list[AlertConditionResponse] = []
    cooldown_until: Optional[datetime] = None
    snoozed_until: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AlertSnoozeRequest(BaseModel):
    # Minutes to snooze for; 0 clears an existing snooze.
    minutes: int = Field(..., ge=0, le=43200)  # cap at 30 days


class TriggeredAlertResponse(BaseModel):
    id: int
    alert_id: Optional[int]
    user_id: str
    symbol: str
    symbol_name: Optional[str] = None
    condition_type: str
    trigger_price: float
    threshold_value: float
    triggered_at: datetime
    notified: bool
    read: bool

    class Config:
        from_attributes = True


class NotificationSettingsResponse(BaseModel):
    user_id: str
    discord_webhook_urls: list[str] = []
    email_address: Optional[str] = None
    email_enabled: bool
    discord_enabled: bool
    default_period: str
    timezone: str
    quiet_start: Optional[str] = None
    quiet_end: Optional[str] = None
    updated_at: Optional[datetime] = None
    email_subject: Optional[str] = None
    email_body: Optional[str] = None
    # Per-user SMTP fields
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_use_tls: Optional[bool] = None
    smtp_username: Optional[str] = None
    smtp_from_address: Optional[str] = None
    smtp_reply_to: Optional[str] = None
    smtp_password_set: bool = False  # never the actual password value

    # Internal field used only for reading from ORM; never serialized
    _smtp_password_encrypted: Optional[str] = None

    class Config:
        from_attributes = True

    @model_validator(mode="before")
    @classmethod
    def _read_smtp_password_set(cls, data):
        if isinstance(data, dict):
            # Set smtp_password_set from the encrypted field before validation
            encrypted = data.get("smtp_password_encrypted")
            data["smtp_password_set"] = bool(encrypted)
            # Remove the encrypted field so it never leaks into the response
            data.pop("smtp_password_encrypted", None)
        return data


class NotificationSettingsUpdate(BaseModel):
    discord_webhook_urls: Optional[list[str]] = None

    @field_validator("discord_webhook_urls")
    @classmethod
    def _drop_blank_webhooks(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return v
        # Strip blanks and dedupe (order-preserving) so one channel isn't pinged twice.
        return list(dict.fromkeys(url.strip() for url in v if url.strip()))
    email_address: Optional[EmailStr] = None
    email_enabled: bool = False
    discord_enabled: bool = True
    default_period: str = Field(default="1h", pattern="^(5m|15m|30m|1h|4h|1d)$")
    timezone: str = "UTC"
    quiet_start: Optional[str] = Field(default=None, pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    quiet_end: Optional[str] = Field(default=None, pattern="^([01]\\d|2[0-3]):[0-5]\\d$")
    email_subject: Optional[str] = Field(default=None, max_length=255)
    email_body: Optional[str] = None
    # Per-user SMTP fields
    smtp_host: Optional[str] = Field(default=None, max_length=255)
    smtp_port: Optional[int] = Field(default=None, ge=1, le=65535)
    smtp_use_tls: Optional[bool] = None
    smtp_username: Optional[str] = Field(default=None, max_length=255)
    smtp_password: Optional[str] = Field(default=None, max_length=500)  # null = keep existing
    smtp_from_address: Optional[str] = Field(default=None, max_length=255)
    smtp_reply_to: Optional[str] = Field(default=None, max_length=255)


class NotificationDeliveryResponse(BaseModel):
    id: int
    triggered_alert_id: Optional[int]
    user_id: str
    channel: str  # discord | email | webhook
    status: str  # success | failed
    http_status: Optional[int]
    error: Optional[str]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class DiscordTestRequest(BaseModel):
    webhook_url: str = Field(..., min_length=1)
