class BaseStrategy:
    def __init__(self, event_bus):
        self.event_bus = event_bus

    def on_market(self, event):
        raise NotImplementedError