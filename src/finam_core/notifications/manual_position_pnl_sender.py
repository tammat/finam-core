# -*- coding: utf-8 -*-

from __future__ import annotations

from finam_core.notifications.manual_position_pnl_formatter import (
    ManualPositionPnlAlert,
    format_manual_position_pnl_alert,
)
from finam_core.reconciliation.manual_position_pnl_analyzer import ManualPositionPnl
from finam_core.notifications.manual_position_alert_dedup import ManualPositionAlertDedup


def should_send_manual_position_pnl_alert(
    pnl: ManualPositionPnl,
    *,
    profit_threshold_pct: float = 1.0,
    loss_threshold_pct: float = -1.0,
) -> bool:
    if pnl.status == "PROFIT" and pnl.pnl_pct >= profit_threshold_pct:
        return True

    if pnl.status == "LOSS" and pnl.pnl_pct <= loss_threshold_pct:
        return True

    return False


def build_recommendation(pnl: ManualPositionPnl) -> str:
    if pnl.status == "PROFIT" and pnl.pnl_pct >= 1.0:
        return "позиция в прибыли; проверить возможность переноса стопа ближе к безубытку"

    if pnl.status == "LOSS" and pnl.pnl_pct <= -1.0:
        return "позиция в убытке; контролировать стоп и не усреднять без нового сигнала"

    return ""


def send_manual_position_pnl_alert(notifier, pnl: ManualPositionPnl) -> bool:
    if not should_send_manual_position_pnl_alert(pnl):
        return False

    dedup_key = (
        f"{pnl.symbol}|"
        f"{pnl.status}|"
        f"{round(pnl.pnl_pct, 1)}"
    )

    if not _DEDUP.should_send(dedup_key):
        return False

    alert = ManualPositionPnlAlert(
        symbol=pnl.symbol,
        qty=pnl.qty,
        average_price=pnl.average_price,
        current_price=pnl.current_price,
        price_delta=pnl.price_delta,
        pnl_pct=pnl.pnl_pct,
        status=pnl.status,
        recommendation=build_recommendation(pnl),
    )

    notifier.send(format_manual_position_pnl_alert(alert))
    return True


_DEDUP = ManualPositionAlertDedup(ttl_sec=3600.0)
