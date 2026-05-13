# -*- coding: utf-8 -*-
"""
Отправка в Telegram только торговой точки:
вход, стоп-лосс, тейк-профит.
Сделки, fill и order_id сюда не передаются.
"""

from __future__ import annotations

import time

from finam_core.notifications.signal_alert_formatter import SignalAlert, format_signal_alert


_SENT_SIGNAL_KEYS = {}
DEFAULT_SIGNAL_ALERT_TTL_SEC = 900


def _get(obj, name, default=None):
    # Русский комментарий: intent в pipeline может быть dict или объектом.
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def send_signal_alert_from_intent(notifier, intent) -> None:
    symbol = _get(intent, "symbol", "")
    side = _get(intent, "side", "")
    timeframe = _get(intent, "timeframe", "M5")
    horizon = _get(intent, "horizon", None) or _get(intent, "signal_horizon", None) or "INTRADAY"

    entry_price = (
        _get(intent, "entry_price")
        or _get(intent, "price")
        or _get(intent, "limit_price")
    )

    stop_loss = (
        _get(intent, "stop_loss")
        or _get(intent, "stop_price")
        or _get(intent, "sl_price")
    )

    take_profit = (
        _get(intent, "take_profit")
        or _get(intent, "take_price")
        or _get(intent, "tp_price")
    )

    if entry_price is None or stop_loss is None or take_profit is None:
        return

    entry_price = float(entry_price)
    stop_loss = float(stop_loss)
    take_profit = float(take_profit)

    key = (
        str(symbol),
        str(side),
        round(entry_price, 4),
        round(stop_loss, 4),
        round(take_profit, 4),
    )

    now = time.time()
    ttl = DEFAULT_SIGNAL_ALERT_TTL_SEC

    last_sent = _SENT_SIGNAL_KEYS.get(key)
    if last_sent is not None and now - last_sent < ttl:
        return

    _SENT_SIGNAL_KEYS[key] = now

    alert = SignalAlert(
        symbol=str(symbol),
        side=str(side),
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        timeframe=str(timeframe),
        horizon=str(horizon).upper(),
        reason=str(_get(intent, "reason", "") or ""),
        confidence=_get(intent, "confidence"),
        risk_rub=_get(intent, "risk_rub"),
    )

    notifier.send(format_signal_alert(alert))
