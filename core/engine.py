# Комментарии:
# Engine работает через явный цикл обработки событий.
# Никакого subscribe/register.
# EventBus используется только для хранения очереди событий.

from core.events import MarketEvent, SignalEvent, OrderEvent


class Engine:

    def __init__(
        self,
        data,
        strategies,
        risk,
        execution,
        portfolio,
        storage,
    ):
        self.data = data
        self.strategies = strategies
        self.risk = risk
        self.execution = execution
        self.portfolio = portfolio
        self.storage = storage
        self.event_bus = data.event_bus

    # -------------------------
    # Main run loop
    # -------------------------

    def run(self):

        # stream market events
        self.data.stream()

        processed = 0

        while self.event_bus.has_events():

            event = self.event_bus.get()

            if isinstance(event, MarketEvent):
                self._handle_market(event)

            elif isinstance(event, SignalEvent):
                self._handle_signal(event)

            elif isinstance(event, OrderEvent):
                self._handle_order(event)

            processed += 1

        return processed

    # -------------------------
    # Handlers
    # -------------------------

    def _handle_market(self, event):

        self.storage.log_market_price(
            symbol=event.symbol,
            timestamp=event.timestamp,
            close_price=event.price,
            volume=event.volume,
        )

        for strategy in self.strategies:
            strategy.on_market(event)

    def _handle_signal(self, event):

        self.storage.log_signal(event)

        if event.features:
            self.storage.log_features(
                symbol=event.symbol,
                timestamp=event.timestamp,
                features=event.features,
            )

        self.risk.on_signal(event)

    def _handle_order(self, event):
        self.execution.execute(event)