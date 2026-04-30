# market/sim_feed.py

import random
from datetime import datetime, timezone
from uuid import uuid4

from finam_core.core.events import MarketEvent, SignalEvent


class SimMarketFeed:

    def __init__(self, symbol="TEST", start_price=100.0):
        self.symbol = symbol
        self.price = start_price

    def generate(self, steps=20):

        events = []

        for _ in range(steps):

            change = random.uniform(-1, 1)
            self.price += change

            ts = datetime.now(timezone.utc)

            market_event = MarketEvent(
                symbol=self.symbol,
                price=self.price,
                volume=100.0,
                timestamp=ts,
            )

            events.append(market_event)

            if change > 0.5:
                signal = SignalEvent(
                    event_id=str(uuid4()),
                    symbol=self.symbol,
                    signal_type="BUY",
                    strength=1.0,
                    features={},
                    timestamp=ts,
                )
                events.append(signal)

            elif change < -0.5:
                signal = SignalEvent(
                    event_id=str(uuid4()),
                    symbol=self.symbol,
                    signal_type="SELL",
                    strength=1.0,
                    features={},
                    timestamp=ts,
                )
                events.append(signal)

        return events


class SimFeed:
    """
    Простой симулятор котировок.
    Генерирует price и шлёт в EventBus.
    """

    def __init__(self, symbol: str, event_bus=None):
        self.symbol = symbol
        self.event_bus = event_bus
        self._running = False

    def start(self, symbols=None):
        import threading
        import time
        import random

        self._running = True

        def run():
            price = 100.0

            while self._running:
                price += random.uniform(-0.2, 0.2)

                # создаём простой event
                event = {
                    "type": "QUOTE",
                    "symbol": self.symbol,
                    "last": price,
                    "price": price,
                    "timestamp": time.time(),
                    "features": {},
                }
                if self.event_bus:
                    self.event_bus.publish(event)

                time.sleep(0.2)

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._running = False