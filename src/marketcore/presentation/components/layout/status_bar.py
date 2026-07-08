from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from marketcore.presentation.components.common.html import h


DEFAULT_TZ = "Europe/Moscow"
DEFAULT_CURRENCY = "RUB"
DEFAULT_BROKER = "Finam"


def render_status_bar(
    timezone: str = DEFAULT_TZ,
    currency: str = DEFAULT_CURRENCY,
    broker: str = DEFAULT_BROKER,
) -> str:
    now = datetime.now(ZoneInfo(timezone)).strftime("%d-%m-%y %H:%M")

    return f"""
    <div class="marketcore-status-bar">
        <span class="status-bar-item">TZ: {h(timezone)}</span>
        <span class="status-bar-item">Currency: {h(currency)}</span>
        <span class="status-bar-item">Broker: {h(broker)}</span>
        <span class="status-bar-item">{h(now)}</span>
    </div>
    """
