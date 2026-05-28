from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from finam_core.notifications.notification_dedup_cache_v1 import NotificationDedupCacheV1
from finam_core.notifications.notification_policy_layer_v1 import NotificationPolicyLayerV1
from finam_core.notifications.telegram_notifier_v1 import TelegramNotifierV1


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
    Центральный router уведомлений:
    policy, severity filter, quiet mode, dedup и transport dispatch.
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
        dedup_cache: NotificationDedupCacheV1 | None = None,
        policy_layer: NotificationPolicyLayerV1 | None = None,
    ) -> None:
        self.notifier = notifier or TelegramNotifierV1()
        self.dedup_cache = dedup_cache or NotificationDedupCacheV1()
        self.policy_layer = policy_layer or NotificationPolicyLayerV1()
        self.quiet_mode = quiet_mode

        if allowed_severities is None:
            allowed_severities = {
                "CRITICAL",
                "WARNING",
                "INFO",
            }

        self.allowed_severities = set(allowed_severities)

    def route(self, event: NotificationEventV1) -> NotificationRouterResultV1:
        if event.severity not in self.ALLOWED_SEVERITIES:
            print(
                "NOTIFICATION_ROUTER_SKIP",
                "reason=invalid_severity",
                f"severity={event.severity}",
                f"symbol={event.symbol}",
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

        if self.quiet_mode and event.severity not in {"CRITICAL", "WARNING"}:
            print(
                "NOTIFICATION_ROUTER_SKIP",
                "reason=quiet_mode",
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
                "reason=severity_filtered",
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

        policy_decision = self.policy_layer.evaluate(
            severity=event.severity,
            category=event.category,
        )

        if not policy_decision.allowed:
            print(
                "NOTIFICATION_ROUTER_SKIP",
                f"reason={policy_decision.reason}",
                f"severity={event.severity}",
                f"symbol={event.symbol}",
                f"quiet_hours_active={policy_decision.quiet_hours_active}",
                f"aggregate_only={policy_decision.aggregate_only}",
                flush=True,
            )
            return NotificationRouterResultV1(
                accepted=True,
                routed=False,
                skipped_reason=policy_decision.reason,
                channel="NONE",
                severity=event.severity,
                symbol=event.symbol,
            )

        dedup_decision = self.dedup_cache.allows(
            category=event.category,
            severity=event.severity,
            symbol=event.symbol,
            title=event.title,
        )

        if not dedup_decision.allowed:
            print(
                "NOTIFICATION_ROUTER_SKIP",
                f"reason={dedup_decision.reason}",
                f"severity={event.severity}",
                f"symbol={event.symbol}",
                f"cooldown_sec={dedup_decision.cooldown_sec}",
                f"elapsed_sec={dedup_decision.elapsed_sec}",
                flush=True,
            )
            return NotificationRouterResultV1(
                accepted=True,
                routed=False,
                skipped_reason=dedup_decision.reason,
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
            "channel=TELEGRAM",
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
