from sqlalchemy import Column, String, Float, Boolean, Integer, ForeignKey, Text, DateTime, JSON, text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    symbol_name = Column(String, nullable=True)
    condition_type = Column(
        String, nullable=False
    )  # above, below, pct_change_up, pct_change_down, multi
    threshold = Column(Float, nullable=False)
    period = Column(String, nullable=False, default="1h")  # 5m, 15m, 30m, 1h, 4h, 1d
    enabled = Column(Boolean, default=True)
    combinator = Column(String, default="all")  # all (AND) or any (OR)
    cooldown_until = Column(DateTime(timezone=True), nullable=True)
    snoozed_until = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="alerts")
    conditions = relationship(
        "AlertCondition",
        back_populates="alert",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    triggered = relationship(
        "TriggeredAlert", back_populates="alert", cascade="all, delete-orphan"
    )


class AlertCondition(Base):
    __tablename__ = "alert_conditions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(
        Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False
    )
    metric = Column(String, nullable=False)  # price, rsi, macd_hist, signal, pct_change
    operator = Column(String, nullable=False)  # gt, lt, crosses_above, eq
    value = Column(Float, nullable=False)

    alert = relationship("Alert", back_populates="conditions")


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    discord_webhook_urls = Column(
        JSON, nullable=False, default=list, server_default=text("'[]'")
    )
    # ponytail: legacy single-URL column, kept + dual-written (first URL) so a
    # code rollback past this release still works; drop in a later contract
    # migration once no deployed code reads it.
    discord_webhook_url = Column(Text, nullable=True)
    email_address = Column(String, nullable=True)
    email_enabled = Column(Boolean, default=False)
    email_subject = Column(String(length=255), nullable=True)
    email_body = Column(Text, nullable=True)
    discord_enabled = Column(Boolean, default=True)
    default_period = Column(String, default="1h")
    timezone = Column(String, default="UTC")
    # Quiet hours: "HH:MM" strings, interpreted in `timezone` above. A window
    # where quiet_start > quiet_end wraps past midnight (e.g. 23:00-07:00).
    # Either unset (None) means quiet hours are disabled.
    quiet_start = Column(String(5), nullable=True)
    quiet_end = Column(String(5), nullable=True)
    # Per-user SMTP configuration
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True, default=587)
    smtp_use_tls = Column(Boolean, nullable=True, default=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password_encrypted = Column(Text, nullable=True)
    smtp_from_address = Column(String(255), nullable=True)
    smtp_reply_to = Column(String(255), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="notification_settings")


class TriggeredAlert(Base):
    __tablename__ = "triggered_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    condition_type = Column(String, nullable=False)
    trigger_price = Column(Float, nullable=False)
    threshold_value = Column(Float, nullable=False)
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    notified = Column(Boolean, default=False)
    read = Column(Boolean, default=False)

    user = relationship("User", back_populates="triggered_alerts")
    alert = relationship("Alert", back_populates="triggered")
    deliveries = relationship(
        "NotificationDelivery",
        back_populates="triggered_alert",
        cascade="all, delete-orphan",
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    triggered_alert_id = Column(
        Integer, ForeignKey("triggered_alerts.id"), nullable=True
    )
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    channel = Column(String, nullable=False)  # discord | email | webhook
    status = Column(String, nullable=False)  # success | failed
    http_status = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    triggered_alert = relationship("TriggeredAlert", back_populates="deliveries")
