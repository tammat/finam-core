from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.notifications.notification_dispatch_service_v1 import (
    NotificationDispatchResultV1,
    NotificationDispatchServiceV1,
)
from finam_core.notifications.notification_router_v1 import NotificationEventV1
from finam_core.notifications.risk_event_audit_storage_v1 import (
    RiskEventAuditRecordV1,
    RiskEventAuditStorageV1,
)


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
    Мост RiskDecision/RiskEvent -> NotificationEventV1 -> audit storage.

    Не принимает risk decision.
    Не меняет execution flow.
    Не отправляет заявки.
    Только формирует operational alert, dispatch result и audit trail.
    """

    def __init__(
        self,
        *,
        dispatcher: NotificationDispatchServiceV1 | None = None,
        audit_storage: RiskEventAuditStorageV1 | None = None,
        audit_enabled: bool = True,
    ) -> None:
        self.dispatcher = dispatcher or NotificationDispatchServiceV1()
        self.audit_storage = audit_storage or RiskEventAuditStorageV1()
        self.audit_enabled = audit_enabled

    def dispatch_risk_event(
        self,
        risk_event: RiskNotificationInputV1,
    ) -> NotificationDispatchResultV1:
        event = self.to_notification_event(risk_event)
        result = self.dispatcher.dispatch(event)

        if self.audit_enabled:
            self._save_audit(
                risk_event=risk_event,
                dispatch_result=result,
            )

        return result

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

    def _save_audit(
        self,
        *,
        risk_event: RiskNotificationInputV1,
        dispatch_result: NotificationDispatchResultV1,
    ) -> None:
        try:
            self.audit_storage.ensure_schema()

            inserted_id = self.audit_storage.insert_event(
                RiskEventAuditRecordV1(
                    category=dispatch_result.category,
                    severity=dispatch_result.severity,
                    symbol=risk_event.symbol,
                    strategy=risk_event.strategy,
                    timeframe=risk_event.timeframe,
                    decision=risk_event.decision,
                    reason=risk_event.reason,
                    value=risk_event.value,
                    exposure=risk_event.exposure,
                    risk_limit=risk_event.risk_limit,
                    routed=dispatch_result.routed,
                    channel=dispatch_result.channel,
                    skipped_reason=dispatch_result.skipped_reason,
                    raw={
                        "source": "risk_notification_bridge_v1",
                        "raw": risk_event.raw or {},
                    },
                )
            )

            print(
                "RISK_NOTIFICATION_AUDIT_SAVED",
                f"id={inserted_id}",
                f"symbol={risk_event.symbol}",
                f"severity={dispatch_result.severity}",
                f"routed={dispatch_result.routed}",
                flush=True,
            )

        except Exception as exc:
            print(
                "RISK_NOTIFICATION_AUDIT_FAILED",
                f"error={type(exc).__name__}:{exc}",
                f"symbol={risk_event.symbol}",
                flush=True,
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
