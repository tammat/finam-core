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
        No handler runs before persistence.
        """

        # 1️⃣ Persist event first (consistency boundary)
        if self._event_store:
            self._event_store.append(
                stream=event.stream,
                event_type=event.type,
                payload=event.to_dict(),
            )

        # 2️⃣ Dispatch synchronously
        results = []
        event_cls = type(event)

        for subscribed_type, handlers in self._subscribers.items():
            if issubclass(event_cls, subscribed_type):
                for handler in handlers:
                    try:
                        results.append(handler(event))
                    except Exception as e:
                        raise RuntimeError(
                            f"[EventBus] handler_failure: "
                            f"{handler.__name__} -> {e}"
                        ) from e

        return results