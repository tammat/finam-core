from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.events.event_store import StoredEvent
from finam_core.projections.realtime_projection_subscriber import (
    ProjectionSubscriberResult,
    RealtimeProjectionSubscriber,
)


@dataclass(frozen=True)
class EventProjectionBridgeResult:
    subscribed: bool
    mode: str


class EventProjectionBridge:
    """Русский комментарий: связывает EventBus и RealtimeProjectionSubscriber."""

    EVENT_TYPE = "EVENT_STORE_APPENDED"

    def __init__(
        self,
        *,
        event_bus: Any,
        subscriber: RealtimeProjectionSubscriber | None = None,
    ) -> None:
        self.event_bus = event_bus
        self.subscriber = subscriber or RealtimeProjectionSubscriber()

    def handle_event(self, *args, **kwargs) -> ProjectionSubscriberResult | None:
        """
        Русский комментарий:
        Поддерживает разные варианты EventBus:
        - handler(event)
        - handler(event_type, event)
        - handler(event=event)
        """
        event = kwargs.get("event")

        if event is None and len(args) == 1:
            event = args[0]

        if event is None and len(args) >= 2:
            event = args[1]

        if not isinstance(event, StoredEvent):
            return None

        return self.subscriber.process_event(event)

    def attach(self) -> EventProjectionBridgeResult:
        """
        Русский комментарий:
        Подписывает bridge на EventBus с учётом возможных разных API subscribe().
        """
        if not hasattr(self.event_bus, "subscribe"):
            raise RuntimeError("event_bus does not support subscribe()")

        try:
            self.event_bus.subscribe(self.EVENT_TYPE, self.handle_event)
            return EventProjectionBridgeResult(subscribed=True, mode="typed")
        except TypeError:
            self.event_bus.subscribe(self.handle_event)
            return EventProjectionBridgeResult(subscribed=True, mode="untyped")
