class EventBus:

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, handler):

        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)

    def publish(self, event):

        handlers = self.subscribers.get(event["type"], [])

        for h in handlers:
            h(event)