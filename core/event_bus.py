from collections import defaultdict
from typing import Callable, Type


class EventBus:
    """
    Central synchronous event dispatcher.
    """

    def __init__(self):
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type: Type, handler: Callable):
        """
        Register handler for specific event type.
        """
        self._subscribers[event_type].append(handler)

    def publish(self, event):
        """
        Dispatch event to all subscribed handlers.
        """
        handlers = self._subscribers.get(type(event), [])

        for handler in handlers:
            handler(event)