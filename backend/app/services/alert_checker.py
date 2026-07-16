"""
Alert checker service - runs periodically to check price alerts and send notifications.
"""

from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import logging

from app.database import AsyncSessionLocal
import yfinance as yf
from app.models import (
    Alert,
    AlertCondition,
    NotificationSettings,
    TriggeredAlert,
    NotificationDelivery,
)
from app.providers import market_provider
from app.services.cache import cached, cache_key
from app.services.mailer import send_email
from app.services.notification.discord import (
    _send_discord_notification,
    describe_condition,
)
from app.services.notification.email import render_alert_email
from app.services.quiet_hours import in_quiet_hours
from app.utils.numeric import _clean
from app.services.signals import signal_to_numeric

log = logging.getLogger(__name__)

COOLDOWN_MINUTES = 60


def _is_future(value: datetime | None, now: datetime) -> bool:
    """Whether a DB-read timestamp is still in the future relative to `now`.

    SQLite (the project's own default local-dev DATABASE_URL) doesn't
    preserve tzinfo across a write/read round-trip for DateTime(timezone=True)
    columns, so a value read back can be naive even though it was always
    written as UTC-aware. Comparing that directly against an aware `now`
    raises TypeError; treat a naive value as UTC instead of crashing.
    """
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value > now

# yfinance period mapping for short intervals
PERIOD_MAP = {
    "5m": ("5d", "5m"),
    "15m": ("5d", "15m"),
    "30m": ("5d", "30m"),
    "1h": ("1mo", "1h"),
    "4h": ("1mo", "4h"),
    "1d": ("1y", "1d"),
}

async def _get_current_price(symbol: str, period: str) -> float | None:
    """Fetch current/recent price for a symbol using specified period."""
    if period not in PERIOD_MAP:
        period = "1h"
    hist_period, interval = PERIOD_MAP[period]

    try:
        result = await market_provider.get_history(
            symbol, period=hist_period, interval=interval
        )
        df = result.value
        if df.empty:
            return None
        return float(df["Close"].iloc[-1])
    except Exception as e:
        log.warning(f"Failed to fetch price for {symbol}: {e}")
        return None


async def _get_period_start_price(symbol: str, period: str) -> float | None:
    """Get price at the start of the period for percentage change calculation."""
    if period not in PERIOD_MAP:
        period = "1h"
    hist_period, interval = PERIOD_MAP[period]

    try:
        result = await market_provider.get_history(
            symbol, period=hist_period, interval=interval
        )
        df = result.value
        if df.empty or len(df) < 2:
            return None
        return float(df["Close"].iloc[0])
    except Exception as e:
        log.warning(f"Failed to fetch period start price for {symbol}: {e}")
        return None


async def _get_ohlcv_df(symbol: str, period: str):
    """Fetch OHLCV dataframe for a symbol, cached via BE-2."""
    if period not in PERIOD_MAP:
        period = "1h"
    hist_period, interval = PERIOD_MAP[period]

    async def _load():
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=hist_period, interval=interval, auto_adjust=True)
        return df

    key = cache_key("ohlcv", symbol, period)
    return await cached(key, ttl=120, loader=_load)


async def _get_indicators(symbol: str, period: str) -> dict:
    """Fetch latest indicator values for a symbol, cached via BE-2."""
    async def _load():
        import pandas_ta as ta
        from app.services.signals import compute_indicators, score_signals, signal_from_score

        df = await _get_ohlcv_df(symbol, period)
        result = {"price": None, "rsi": None, "macd_hist": None, "macd_signal": None, "pct_change": None, "signal": None, "rvol": None}
        if df.empty:
            return result

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        n = len(close)
        price = float(close.iloc[-1])
        result["price"] = price

        if len(close) >= 14:
            rsi_series = ta.rsi(close, length=14)
            if rsi_series is not None and not rsi_series.empty:
                result["rsi"] = float(rsi_series.iloc[-1])

        macd_df = None
        if len(close) >= 26:
            macd_df = ta.macd(close, fast=12, slow=26, signal=9)
            if macd_df is not None and not macd_df.empty:
                result["macd_hist"] = _clean(float(macd_df["MACDh_12_26_9"].iloc[-1]))
                result["macd_signal"] = _clean(float(macd_df["MACDs_12_26_9"].iloc[-1]))

        # pct_change (漲跌幅) = today's change vs the previous trading day's
        # close — the % every quote page shows. Anchor to the DAILY feed, not
        # the intraday frame: Yahoo's intraday history can contain bars for
        # days the daily feed (and quote pages) treat as non-trading days
        # (seen live on 00631L.TW 2026-07-15), which would silently shift the
        # anchor. Earlier anchors (previous bar, window start) were both wrong.
        daily_df = await _get_ohlcv_df(symbol, "1d")
        if not daily_df.empty:
            daily_close = daily_df["Close"]
            prior = daily_close[daily_close.index.normalize() < close.index[-1].normalize()]
            if not prior.empty and float(prior.iloc[-1]):
                prev_close = float(prior.iloc[-1])
                result["pct_change"] = ((price - prev_close) / prev_close) * 100

        if len(close) >= 20:
            indicators = compute_indicators(close, high, low, volume, n, macd_df)
            result["rvol"] = indicators.get("rvol")
            score, _ = score_signals(
                bias=indicators.get("bias"),
                macd_hist=indicators.get("macd_histogram"),
                kdj_k=indicators.get("kdj_k"),
                kdj_d=indicators.get("kdj_d"),
                vol_ratio=indicators.get("volume_ratio"),
                rvol=indicators.get("rvol"),
                breakout=False,
                high_52w=None,
            )
            result["signal"] = signal_to_numeric(signal_from_score(score))

        return result

    key = cache_key("indicators", symbol, period)
    return await cached(key, ttl=120, loader=_load)


def _evaluate_condition(condition: AlertCondition, indicators: dict) -> bool:
    """Evaluate a single AlertCondition against current indicator values."""
    metric = condition.metric
    op = condition.operator
    value = condition.value

    current_val = indicators.get(metric)
    if current_val is None:
        return False

    if op == "gt":
        return current_val > value
    elif op == "lt":
        return current_val < value
    elif op == "eq":
        return abs(current_val - value) < 0.001
    elif op == "crosses_above":
        # Check if current > value (already satisfied for crossing)
        # For a proper cross check we'd need previous value too
        return current_val > value
    return False


def _should_trigger(
    condition_type: str,
    current_price: float,
    threshold: float,
    period_start_price: float | None,
) -> bool:
    """Check if legacy alert condition is met."""
    if condition_type == "above":
        return current_price > threshold
    elif condition_type == "below":
        return current_price < threshold
    elif condition_type == "pct_change_up":
        if period_start_price is None or period_start_price == 0:
            return False
        pct_change = ((current_price - period_start_price) / period_start_price) * 100
        return pct_change > threshold
    elif condition_type == "pct_change_down":
        if period_start_price is None or period_start_price == 0:
            return False
        pct_change = ((current_price - period_start_price) / period_start_price) * 100
        return pct_change < -threshold
    return False


def _check_multi_condition(
    alert: Alert, indicators: dict
) -> tuple[bool, list[AlertCondition]]:
    """Evaluate all conditions of an alert using its combinator.

    Returns (triggered, matched_conditions) so notifications can say WHICH
    condition(s) fired instead of the opaque 'multi' + 0.0 threshold.
    """
    conditions = alert.conditions or []
    if not conditions:
        return False, []

    combinator = alert.combinator or "all"
    matched = [c for c in conditions if _evaluate_condition(c, indicators)]

    if combinator == "all":
        return len(matched) == len(conditions), matched
    else:
        return bool(matched), matched


def _conditions_text(conditions: list[AlertCondition]) -> str | None:
    if not conditions:
        return None
    return "\n".join(describe_condition(c.metric, c.operator, c.value) for c in conditions)


async def _send_notifications(
    settings: NotificationSettings,
    alert: Alert,
    symbol: str,
    condition_type: str,
    price: float,
    threshold: float,
    triggered_at: datetime,
    conditions_text: str | None = None,
) -> tuple[list[NotificationDelivery], bool]:
    """Dispatch Discord/email for one triggered alert. Returns (deliveries, notified).

    Shared by the live per-symbol check and the quiet-hours catch-up so both
    paths record delivery attempts identically. For multi-condition alerts,
    conditions_text describes the matched condition(s); the catch-up path
    doesn't know which matched, so it falls back to all of the alert's
    conditions.
    """
    if conditions_text is None and alert.conditions:
        conditions_text = _conditions_text(alert.conditions)

    delivery_records: list[NotificationDelivery] = []
    notified = False

    if settings.discord_enabled and settings.discord_webhook_urls:
        for webhook_url in settings.discord_webhook_urls:
            success, http_status, error = await _send_discord_notification(
                webhook_url,
                symbol,
                condition_type,
                price,
                threshold,
                triggered_at,
                conditions_text=conditions_text,
            )
            delivery_records.append(
                NotificationDelivery(
                    triggered_alert_id=None,  # filled after flush
                    user_id=alert.user_id,
                    channel="discord",
                    status="success" if success else "failed",
                    http_status=http_status,
                    error=error,
                )
            )
            if success:
                notified = True

    if settings.email_enabled and settings.email_address:
        if not settings.smtp_host:
            delivery_records.append(
                NotificationDelivery(
                    triggered_alert_id=None,
                    user_id=alert.user_id,
                    channel="email",
                    status="failed",
                    error="Email enabled but no SMTP configured",
                )
            )
        else:
            email_subject, email_body = render_alert_email(
                settings, symbol, alert, price, triggered_at
            )
            email_success = await send_email(
                settings,
                settings.email_address,
                email_subject,
                html_body=email_body,
            )
            delivery_records.append(
                NotificationDelivery(
                    triggered_alert_id=None,
                    user_id=alert.user_id,
                    channel="email",
                    status="success" if email_success else "failed",
                    error=None if email_success else "Email send failed",
                )
            )
            if email_success:
                notified = True

    return delivery_records, notified


async def _dispatch_quiet_hours_catchup(db, now: datetime) -> int:
    """Catch up on notifications held back during a user's quiet hours.

    For every user whose quiet hours are configured and are NOT active right
    now, find their un-notified TriggeredAlert rows that fired *during* a
    quiet window (checked against each record's own triggered_at, not just
    "unnotified" — a delivery that failed outside quiet hours for an
    unrelated reason must not be swept into this catch-up) and re-attempt
    delivery once per alert.

    Returns the number of triggered alerts caught up.
    """
    settings_result = await db.execute(
        select(NotificationSettings).where(
            NotificationSettings.quiet_start.isnot(None),
            NotificationSettings.quiet_end.isnot(None),
        )
    )
    all_settings = settings_result.scalars().all()

    caught_up = 0
    for settings in all_settings:
        if in_quiet_hours(settings, now):
            continue  # still quiet for this user — nothing to catch up yet

        pending_result = await db.execute(
            select(TriggeredAlert).where(
                TriggeredAlert.user_id == settings.user_id,
                TriggeredAlert.notified.is_(False),
            )
        )
        pending = pending_result.scalars().all()
        held = [t for t in pending if in_quiet_hours(settings, t.triggered_at)]
        if not held:
            continue

        for triggered_record in held:
            alert = None
            if triggered_record.alert_id is not None:
                alert = await db.get(Alert, triggered_record.alert_id)
            if alert is None:
                # Alert was deleted since — nothing left to notify from.
                continue

            delivery_records, notified = await _send_notifications(
                settings,
                alert,
                triggered_record.symbol,
                triggered_record.condition_type,
                triggered_record.trigger_price,
                triggered_record.threshold_value,
                triggered_record.triggered_at,
            )
            if notified:
                triggered_record.notified = True
            await db.flush()
            for dr in delivery_records:
                dr.triggered_alert_id = triggered_record.id
                db.add(dr)
            caught_up += 1

        await db.commit()

    if caught_up:
        log.info("Quiet-hours catch-up delivered %d held alert(s)", caught_up)
    return caught_up


async def check_alerts():
    """
    Main function to check all enabled alerts and trigger notifications.
    Called by the cron job every 15 minutes.
    """
    log.info("Starting alert check...")

    async with AsyncSessionLocal() as db:
        # Fetch all enabled alerts with their notification settings
        result = await db.execute(
            select(Alert, NotificationSettings)
            .options(selectinload(Alert.conditions))
            .join(
                NotificationSettings,
                Alert.user_id == NotificationSettings.user_id,
                isouter=True,
            )
            .where(Alert.enabled)
        )
        rows = result.all()

        if not rows:
            log.info("No enabled alerts to check")
            await _dispatch_quiet_hours_catchup(db, datetime.now(timezone.utc))
            return

        log.info(f"Checking {len(rows)} enabled alerts")

        # Group alerts by symbol for batch fetching
        symbol_alerts: dict[str, list[tuple[Alert, NotificationSettings | None]]] = {}
        for alert, settings in rows:
            sym = alert.symbol.upper()
            if sym not in symbol_alerts:
                symbol_alerts[sym] = []
            symbol_alerts[sym].append((alert, settings))

        # Process each symbol's alerts
        now = datetime.now(timezone.utc)
        from app.services.market_hours import is_market_open

        for symbol, alert_settings_list in symbol_alerts.items():
            if not is_market_open(symbol, now):
                log.info(f"Skipping {symbol}: market closed")
                continue
            current_price = await _get_current_price(symbol, "1h")
            if current_price is None:
                log.warning(f"Could not fetch price for {symbol}, skipping")
                continue

            # Fetch indicators once per symbol for multi-condition alerts
            has_multi = any(a.conditions for a, _ in alert_settings_list)
            indicators = None
            if has_multi:
                # Use the shortest period among multi-condition alerts
                period = "1h"
                for a, _ in alert_settings_list:
                    if a.conditions:
                        period = a.period
                        break
                indicators = await _get_indicators(symbol, period)

            # Get period start prices for pct_change alerts
            period_prices: dict[str, float | None] = {}
            pct_change_alerts = [
                (a, s)
                for a, s in alert_settings_list
                if a.condition_type in ("pct_change_up", "pct_change_down")
            ]
            if pct_change_alerts:
                for alert, _ in pct_change_alerts:
                    if alert.period not in period_prices:
                        period_prices[alert.period] = await _get_period_start_price(
                            symbol, alert.period
                        )

            for alert, settings in alert_settings_list:
                try:
                    # Check cooldown
                    if _is_future(alert.cooldown_until, now):
                        continue

                    # Check snooze
                    if _is_future(alert.snoozed_until, now):
                        continue

                    # Check if alert should trigger
                    triggered = False
                    trigger_condition_type = alert.condition_type
                    trigger_threshold = alert.threshold

                    matched_text: str | None = None
                    if alert.conditions:
                        # Multi-condition evaluation
                        triggered, matched = _check_multi_condition(alert, indicators)
                        matched_text = _conditions_text(matched)
                    else:
                        # Legacy single-condition evaluation
                        period_start_price = None
                        if alert.condition_type in ("pct_change_up", "pct_change_down"):
                            period_start_price = period_prices.get(alert.period)

                        triggered = _should_trigger(
                            alert.condition_type,
                            current_price,
                            alert.threshold,
                            period_start_price,
                        )

                    if triggered:
                        # Create triggered alert record
                        triggered_record = TriggeredAlert(
                            alert_id=alert.id,
                            user_id=alert.user_id,
                            symbol=symbol,
                            condition_type=trigger_condition_type,
                            trigger_price=current_price,
                            threshold_value=trigger_threshold,
                            triggered_at=now,
                            notified=False,
                            read=False,
                        )
                        db.add(triggered_record)

                        # Set cooldown
                        alert.cooldown_until = now + timedelta(minutes=COOLDOWN_MINUTES)

                        # Send notifications if settings exist, are enabled,
                        # and the user isn't in their configured quiet hours —
                        # quiet-hours holds are caught up after the main loop.
                        delivery_records: list[NotificationDelivery] = []
                        if settings and not in_quiet_hours(settings, now):
                            delivery_records, notified = await _send_notifications(
                                settings,
                                alert,
                                symbol,
                                trigger_condition_type,
                                current_price,
                                trigger_threshold,
                                now,
                                conditions_text=matched_text,
                            )
                            if notified:
                                triggered_record.notified = True

                        # Flush to get triggered_record.id, then link deliveries
                        await db.flush()
                        for dr in delivery_records:
                            dr.triggered_alert_id = triggered_record.id
                            db.add(dr)

                        await db.commit()
                        log.info(
                            f"Alert triggered: {symbol} {trigger_condition_type} at ${current_price:.2f}"
                        )

                except Exception as e:
                    log.error(f"Error processing alert {alert.id}: {e}")
                    await db.rollback()

        await _dispatch_quiet_hours_catchup(db, now)

        log.info("Alert check completed")


async def check_alerts_endpoint():
    """Synchronous wrapper for calling check_alerts from an API endpoint."""
    await check_alerts()
    return {"status": "ok", "message": "Alerts checked"}


if __name__ == "__main__":
    import asyncio

    asyncio.run(check_alerts())
