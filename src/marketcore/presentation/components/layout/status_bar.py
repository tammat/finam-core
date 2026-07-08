from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from marketcore.presentation.components.common.html import h

DEFAULT_TZ = "Europe/Moscow"
DEFAULT_CURRENCY = "RUB"
DEFAULT_BROKER = "Finam"

TZ_OPTIONS = ("Europe/Moscow", "UTC", "Europe/Helsinki")
CURRENCY_OPTIONS = ("RUB", "USD", "EUR")
BROKER_OPTIONS = ("Finam", "T-Bank", "QUIK", "Interactive Brokers")


def _select(name: str, values: tuple[str, ...], selected: str) -> str:
    options = []
    for value in values:
        marker = " selected" if value == selected else ""
        options.append(f'<option value="{h(value)}"{marker}>{h(value)}</option>')
    return f'<select class="status-bar-select" name="{h(name)}">{"".join(options)}</select>'


def render_status_bar(
    timezone: str = DEFAULT_TZ,
    currency: str = DEFAULT_CURRENCY,
    broker: str = DEFAULT_BROKER,
) -> str:
    if timezone not in TZ_OPTIONS:
        timezone = DEFAULT_TZ
    if currency not in CURRENCY_OPTIONS:
        currency = DEFAULT_CURRENCY
    if broker not in BROKER_OPTIONS:
        broker = DEFAULT_BROKER

    now = datetime.now(ZoneInfo(timezone)).strftime("%d-%m-%y %H:%M")

    return f"""
    <div class="marketcore-status-bar">
        <span class="status-bar-item">TZ: {_select("timezone", TZ_OPTIONS, timezone)}</span>
        <span class="status-bar-item">Currency: {_select("currency", CURRENCY_OPTIONS, currency)}</span>
        <span class="status-bar-item">Broker: {_select("broker", BROKER_OPTIONS, broker)}</span>
        <span class="status-bar-item status-bar-time">{h(now)}</span>
    </div>
    """
