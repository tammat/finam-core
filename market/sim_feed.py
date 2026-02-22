# market/sim_feed.py

import random
from datetime import datetime, timezone
from uuid import uuid4

from domain.events import MarketEvent, SignalEvent


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