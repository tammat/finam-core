from collections import defaultdict
from typing import Callable, Type


class EventBus:
    """
    Central synchronous event dispatcher.
    Deterministic, in-process, no async.

    Event sourcing enabled:
    - Append to EventStore BEFORE dispatch
    - Strict failure propagation
    """

    def __init__(self, event_store=None):
        self._subscribers = defaultdict(list)
        self._event_store = event_store

    # ------------------------------------------------------------
    # Subscription
    # ------------------------------------------------------------

    def subscribe(self, event_type: Type, handler: Callable):
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: Type, handler: Callable):
        if handler in self._subscribers.get(event_type, []):
            self._subscribers[event_type].remove(handler)

    def has_subscribers(self, event_type: Type) -> bool:
        return bool(self._subscribers.get(event_type))

    # ------------------------------------------------------------
    # Publish
    # ------------------------------------------------------------

    def publish(self, event):
        """
        Append-first deterministic dispatch.
        """

        if self._event_store:

            if not hasattr(event, "stream"):
                raise RuntimeError("Event missing 'stream'")
            if not hasattr(event, "id"):
                raise RuntimeError("Event missing 'id'")
            if not hasattr(event, "type"):
                raise RuntimeError("Event missing 'type'")
            if not hasattr(event, "to_dict"):
                raise RuntimeError("Event missing 'to_dict()'")

            current_version = self._event_store.get_stream_version(event.stream)

            # ✅ ТОЛЬКО ИМЕНОВАННЫЕ АРГУМЕНТЫ
            self._event_store.append(
                stream=event.stream,
                event_id=str(event.id),
                event_type=event.type,
                payload=event.to_dict(),
                expected_version=current_version,
            )

        results = []

        for subscribed_type, handlers in self._subscribers.items():
            if issubclass(type(event), subscribed_type):
                for handler in handlers:
                    results.append(handler(event))

        return results