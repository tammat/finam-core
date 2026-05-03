import random
from datetime import datetime, timezone
from core.events import MarketEvent


class DummyMarketData:
    """
    Минимальный источник данных.
    Публикует 3 цены и завершает поток.
    """

    def __init__(self, event_bus, symbol="NGH6@RTSX"):
        self.event_bus = event_bus
        self.symbol = symbol
        self._i = 0
        self._prices = [3.10, 3.12, 3.18]

    def stream_step(self):
        if self._i >= len(self._prices):
            return False

        price = float(self._prices[self._i])
        self._i += 1

        self.event_bus.publish(
            MarketEvent(
                symbol=self.symbol,
                price=price,
                volume=1.0,
                timestamp=datetime.now(timezone.utc)
            )
        )
        return True

    import random

    def stream(self):
        price = 100.0

        for _ in range(60):
            price += random.uniform(-1, 1)

            self.event_bus.publish(
                MarketEvent(
                    symbol="NGH6@RTSX",
                    price=price,
                    volume=1.0,
                    timestamp=datetime.now(timezone.utc),
                )
            )