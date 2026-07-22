"""
Discord notification delivery for alert triggers.
"""

from datetime import datetime
import logging

import httpx

from app.config import get_settings

log = logging.getLogger(__name__)

DISCORD_COLOR_ABOVE = 5763719  # green — "above"-style triggers
DISCORD_COLOR_BELOW = 15548905  # red — everything else

CONDITION_LABELS = {
    "above": "🔼 Above",
    "below": "🔽 Below",
    "pct_change_up": "📈 +% Up",
    "pct_change_down": "📉 -% Down",
}

METRIC_LABELS = {
    "price": "Price",
    "pct_change": "% Change",
    "rsi": "RSI",
    "macd_hist": "MACD Hist",
    "signal": "Signal",
}

OPERATOR_LABELS = {
    "gt": ">",
    "lt": "<",
    "eq": "=",
    "crosses_above": "crosses above",
}


def describe_condition(metric: str, operator: str, value: float) -> str:
    """Human-readable text for one AlertCondition, e.g. '% Change crosses above 2.0%'."""
    if metric == "pct_change":
        value_str = f"{value:.1f}%"
    elif metric == "price":
        value_str = f"${value:g}"
    else:
        value_str = f"{value:g}"
    return (
        f"{METRIC_LABELS.get(metric, metric)} "
        f"{OPERATOR_LABELS.get(operator, operator)} {value_str}"
    )


def _alerts_url() -> str | None:
    base = get_settings().FRONTEND_URL.rstrip("/")
    return f"{base}/alerts" if base else None


def _build_discord_embed(
    symbol: str | None,
    condition_type: str | None,
    current_price: float | None,
    threshold: float | None,
    triggered_at: datetime | None,
    pct_change_today: float | None,
    conditions_text: str | None = None,
) -> dict:
    """Build a Discord embed dict. When symbol is None, builds a test notification embed.

    conditions_text: for multi-condition alerts, the pre-formatted description of
    the condition(s) that matched — shown instead of the raw condition_type and
    the meaningless 0.0 threshold.
    """
    url = _alerts_url()

    if symbol is None:
        # Test notification
        embed = {
            "title": "🔔 Test notification",
            "description": "Your Discord webhook is configured correctly.",
            "color": 0x2ECC71,
        }
        if url:
            embed["url"] = url
        return embed

    color = DISCORD_COLOR_ABOVE if condition_type == "above" else DISCORD_COLOR_BELOW
    price_str = f"${current_price:.2f}"

    if pct_change_today is not None:
        price_change_str = f"({pct_change_today:+.1f}% today)"
    else:
        price_change_str = ""

    price_line = f"Current price: {price_str} {price_change_str}"

    if conditions_text is not None:
        title = f"🔔 Price Alert: {symbol}"
        # Bold, full-width condition line(s) at the top — the reason the alert fired
        # should be the most prominent thing after the title.
        highlighted = "\n".join(f"🎯 **{line}**" for line in conditions_text.split("\n"))
        description = f"{highlighted}\n{price_line}"
        condition_fields = []
    else:
        condition_label = CONDITION_LABELS.get(condition_type, condition_type)
        threshold_str = (
            f"${threshold:.2f}"
            if condition_type in ("above", "below")
            else f"{threshold:.1f}%"
        )
        title = f"🔔 Price Alert: {symbol} {condition_label}"
        description = price_line
        condition_fields = [
            {"name": "Condition", "value": condition_type, "inline": True},
            {"name": "Threshold", "value": threshold_str, "inline": True},
        ]

    embed = {
        "title": title,
        "description": description,
        "color": color,
        "fields": condition_fields
        + [
            {
                "name": "Triggered At",
                "value": triggered_at.strftime("%Y-%m-%d %H:%M UTC"),
                "inline": True,
            },
        ],
    }
    if url:
        embed["url"] = url
    return embed


async def _send_discord_notification(
    webhook_url: str,
    symbol: str | None = None,
    condition_type: str | None = None,
    current_price: float | None = None,
    threshold: float | None = None,
    triggered_at: datetime | None = None,
    pct_change_today: float | None = None,
    conditions_text: str | None = None,
) -> tuple[bool, int | None, str | None]:
    """Send notification to Discord webhook. Returns (success, http_status, error)."""
    embed = _build_discord_embed(
        symbol,
        condition_type,
        current_price,
        threshold,
        triggered_at,
        pct_change_today,
        conditions_text,
    )

    # Embed only — a plain-text "content" line would just duplicate the embed title.
    payload = {"embeds": [embed]}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code >= 200 and resp.status_code < 300:
                log.info(f"Discord notification sent (symbol={symbol or 'test'})")
                return (True, resp.status_code, None)
            else:
                log.warning(
                    f"Discord notification failed (symbol={symbol or 'test'}): {resp.status_code}"
                )
                return (False, resp.status_code, f"HTTP {resp.status_code}")
    except Exception as e:
        log.error(f"Failed to send Discord notification: {e}")
        return (False, None, str(e))