# src/finam_core/events/event_bus.py

class EventBus:
    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type: str, handler):
        # handler(event: dict) -> None
        self.subscribers.setdefault(event_type, []).append(handler)

    def publish(self, event: dict):
        # event must contain "type"
        et = event.get("type")
        if not et:
            return
        for h in self.subscribers.get(et, []):
            h(event)