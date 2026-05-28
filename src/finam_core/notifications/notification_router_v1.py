from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from finam_core.notifications.telegram_notifier_v1 import (
    TelegramNotifierV1,
    TelegramNotifyResultV1,
)


@dataclass(frozen=True)
class NotificationEventV1:
    category: str
    severity: str
    symbol: str
    title: str
    body: str


@dataclass(frozen=True)
class NotificationRouterResultV1:
    accepted: bool
    routed: bool
    skipped_reason: str | None
    channel: str
    severity: str
    symbol: str


class NotificationRouterV1:
    """
    Русский комментарий:
    Центральный router уведомлений.

    Задачи:
    - severity filtering
    - anti-spam filtering
    - routing policy
    - единая точка dispatch
    """

    ALLOWED_SEVERITIES = {
        "CRITICAL",
        "WARNING",
        "INFO",
        "NORMAL",
    }

    def __init__(
        self,
        *,
        notifier: TelegramNotifierV1 | None = None,
        allowed_severities: Iterable[str] | None = None,
        quiet_mode: bool = False,
    ) -> None:

        self.notifier = notifier or TelegramNotifierV1()

        if allowed_severities is None:
            allowed_severities = {
                "CRITICAL",
                "WARNING",
                "INFO",
            }

        self.allowed_severities = set(allowed_severities)
        self.quiet_mode = quiet_mode

    def route(
        self,
        event: NotificationEventV1,
    ) -> NotificationRouterResultV1:

        if event.severity not in self.ALLOWED_SEVERITIES:
            print(
                "NOTIFICATION_ROUTER_SKIP",
                f"reason=invalid_severity",
                f"severity={event.severity}",
                flush=True,
            )

            return NotificationRouterResultV1(
                accepted=False,
                routed=False,
                skipped_reason="invalid_severity",
                channel="NONE",
                severity=event.severity,
                symbol=event.symbol,
            )

        if self.quiet_mode and event.severity not in {
            "CRITICAL",
            "WARNING",
        }:
            print(
                "NOTIFICATION_ROUTER_SKIP",
                f"reason=quiet_mode",
                f"severity={event.severity}",
                f"symbol={event.symbol}",
                flush=True,
            )

            return NotificationRouterResultV1(
                accepted=True,
                routed=False,
                skipped_reason="quiet_mode",
                channel="NONE",
                severity=event.severity,
                symbol=event.symbol,
            )

        if event.severity not in self.allowed_severities:
            print(
                "NOTIFICATION_ROUTER_SKIP",
                f"reason=severity_filtered",
                f"severity={event.severity}",
                f"symbol={event.symbol}",
                flush=True,
            )

            return NotificationRouterResultV1(
                accepted=True,
                routed=False,
                skipped_reason="severity_filtered",
                channel="NONE",
                severity=event.severity,
                symbol=event.symbol,
            )

        text = "\n".join(
            [
                event.title,
                "",
                event.body,
            ]
        )

        notify_result = self.notifier.send_text(text)

        print(
            "NOTIFICATION_ROUTER_ROUTE_OK",
            f"channel=TELEGRAM",
            f"severity={event.severity}",
            f"symbol={event.symbol}",
            f"dry_run={notify_result.dry_run}",
            flush=True,
        )

        return NotificationRouterResultV1(
            accepted=True,
            routed=True,
            skipped_reason=None,
            channel="TELEGRAM",
            severity=event.severity,
            symbol=event.symbol,
        )
