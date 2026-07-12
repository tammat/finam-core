from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from marketcore.presentation.components.common.html import h
from marketcore.presentation.i18n.runtime import tr

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


def _money(value, currency: str) -> str:
    amount = Decimal(str(value if value is not None else "0")).quantize(Decimal("0.01"))
    text = f"{amount:,.2f}".replace(",", " ").replace(".", ",")
    symbol = {"RUB": "₽", "USD": "$", "EUR": "€"}.get(currency, currency)
    return f"{text} {symbol}"



def _money_signed(value, currency: str) -> str:
    amount = Decimal(str(value if value is not None else "0")).quantize(Decimal("0.01"))
    sign = "+" if amount > 0 else ""
    text = f"{abs(amount):,.2f}".replace(",", " ").replace(".", ",")
    symbol = {"RUB": "₽", "USD": "$", "EUR": "€"}.get(currency, currency)
    return f"{sign}{text} {symbol}"


def _pct(value) -> str:
    amount = Decimal(str(value if value is not None else "0")).quantize(Decimal("0.01"))
    return f"{amount:+.2f}".replace(".", ",") + " %"


def render_status_bar(
    timezone: str = DEFAULT_TZ,
    currency: str = DEFAULT_CURRENCY,
    broker: str = DEFAULT_BROKER,
    portfolio_value=0,
    daily_pnl=0,
    daily_pnl_pct=0,
    last_data_update: str = "",
    connection_status: str = "readonly",
) -> str:
    if timezone not in TZ_OPTIONS:
        timezone = DEFAULT_TZ
    if currency not in CURRENCY_OPTIONS:
        currency = DEFAULT_CURRENCY
    if broker not in BROKER_OPTIONS:
        broker = DEFAULT_BROKER

    now = datetime.now(ZoneInfo(timezone)).strftime("%d.%m.%Y, %H:%M")
    pnl_value = Decimal(str(daily_pnl if daily_pnl is not None else "0"))
    pnl_tone = "positive" if pnl_value > 0 else "negative" if pnl_value < 0 else "neutral"
    pnl_icon = "🟢" if pnl_value > 0 else "🔴" if pnl_value < 0 else "⚪"

    return f"""
    <div class="marketcore-status-bar">
        <span class="status-bar-brand">🧠 MarketCore</span>
        <span class="status-bar-item">{tr("statusbar.broker")}: {_select("broker", BROKER_OPTIONS, broker)}</span>
        <span class="status-bar-item">{tr("statusbar.connection")}: {h(connection_status)}</span>
        <span class="status-bar-item">{tr("statusbar.timezone")}: {_select("timezone", TZ_OPTIONS, timezone)}</span>
        <span class="status-bar-item">{tr("statusbar.currency")}: {_select("currency", CURRENCY_OPTIONS, currency)}</span>
        <span class="status-bar-item">{tr("statusbar.portfolio")}: {h(_money(portfolio_value, currency))}</span>
        <span class="status-bar-item status-bar-pnl status-bar-pnl-{h(pnl_tone)}">{tr("statusbar.daily_pnl")}: {pnl_icon} {h(_money_signed(daily_pnl, currency))} ({h(_pct(daily_pnl_pct))})</span>
        <span class="status-bar-item">{tr("statusbar.last_data_update")}: {h(last_data_update)}</span>
        <span class="status-bar-item status-bar-time">{tr("statusbar.local_time")}: {h(now)}</span>
    </div>
    """
