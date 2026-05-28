from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.notifications.notification_dispatch_service_v1 import (
    NotificationDispatchResultV1,
    NotificationDispatchServiceV1,
)
from finam_core.notifications.notification_router_v1 import NotificationEventV1


@dataclass(frozen=True)
class RiskNotificationInputV1:
    symbol: str
    strategy: str
    timeframe: str
    decision: str
    reason: str
    severity: str
    value: float | None = None
    exposure: float | None = None
    risk_limit: float | None = None
    raw: dict[str, Any] | None = None


class RiskNotificationBridgeV1:
    """
    Русский комментарий:
    Мост RiskDecision/RiskEvent -> NotificationEventV1.

    Не принимает risk decision.
    Не меняет execution flow.
    Не отправляет заявки.
    Только формирует operational alert и передает его в notification dispatcher.
    """

    def __init__(
        self,
        *,
        dispatcher: NotificationDispatchServiceV1 | None = None,
    ) -> None:
        self.dispatcher = dispatcher or NotificationDispatchServiceV1()

    def dispatch_risk_event(
        self,
        risk_event: RiskNotificationInputV1,
    ) -> NotificationDispatchResultV1:
        event = self.to_notification_event(risk_event)
        return self.dispatcher.dispatch(event)

    def to_notification_event(
        self,
        risk_event: RiskNotificationInputV1,
    ) -> NotificationEventV1:
        severity = self._normalize_severity(risk_event.severity)

        title = self._build_title(
            symbol=risk_event.symbol,
            decision=risk_event.decision,
            severity=severity,
        )

        body = self._build_body(risk_event)

        return NotificationEventV1(
            category="RISK",
            severity=severity,
            symbol=risk_event.symbol,
            title=title,
            body=body,
        )

    @staticmethod
    def _normalize_severity(severity: str) -> str:
        value = str(severity or "WARNING").upper()

        if value in {"CRITICAL", "WARNING", "INFO", "NORMAL"}:
            return value

        return "WARNING"

    @staticmethod
    def _build_title(
        *,
        symbol: str,
        decision: str,
        severity: str,
    ) -> str:
        if severity == "CRITICAL":
            emoji = "🚨"
        elif severity == "WARNING":
            emoji = "⚠️"
        elif severity == "INFO":
            emoji = "ℹ️"
        else:
            emoji = "•"

        return f"{emoji} RISK {symbol} | {decision}"

    @staticmethod
    def _build_body(risk_event: RiskNotificationInputV1) -> str:
        lines = [
            f"Инструмент: {risk_event.symbol}",
            f"Стратегия: {risk_event.strategy}",
            f"Таймфрейм: {risk_event.timeframe}",
            f"Решение риска: {risk_event.decision}",
            f"Причина: {risk_event.reason}",
        ]

        if risk_event.value is not None:
            lines.append(f"Значение: {risk_event.value}")

        if risk_event.exposure is not None:
            lines.append(f"Экспозиция: {risk_event.exposure}")

        if risk_event.risk_limit is not None:
            lines.append(f"Лимит риска: {risk_event.risk_limit}")

        return "\n".join(lines)
