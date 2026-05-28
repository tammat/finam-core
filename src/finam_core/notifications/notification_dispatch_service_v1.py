from __future__ import annotations

from dataclasses import dataclass

from finam_core.notifications.notification_router_v1 import (
    NotificationEventV1,
    NotificationRouterResultV1,
    NotificationRouterV1,
)


@dataclass(frozen=True)
class NotificationDispatchResultV1:
    accepted: bool
    routed: bool
    skipped_reason: str | None
    channel: str
    severity: str
    symbol: str
    category: str


class NotificationDispatchServiceV1:
    """
    Русский комментарий:
    Единый dispatch service для notification stack.

    Назначение:
    - принимать NotificationEventV1;
    - передавать событие в NotificationRouterV1;
    - вернуть унифицированный результат;
    - не выполнять бизнес-логику стратегий, риска или исполнения.
    """

    def __init__(self, *, router: NotificationRouterV1 | None = None) -> None:
        self.router = router or NotificationRouterV1()

    def dispatch(self, event: NotificationEventV1) -> NotificationDispatchResultV1:
        router_result: NotificationRouterResultV1 = self.router.route(event)

        print(
            "NOTIFICATION_DISPATCH_RESULT",
            f"accepted={router_result.accepted}",
            f"routed={router_result.routed}",
            f"reason={router_result.skipped_reason}",
            f"channel={router_result.channel}",
            f"severity={router_result.severity}",
            f"symbol={router_result.symbol}",
            f"category={event.category}",
            flush=True,
        )

        return NotificationDispatchResultV1(
            accepted=router_result.accepted,
            routed=router_result.routed,
            skipped_reason=router_result.skipped_reason,
            channel=router_result.channel,
            severity=router_result.severity,
            symbol=router_result.symbol,
            category=event.category,
        )
