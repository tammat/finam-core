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
        # Русский коммент: состояние симулятора (тренд + волатильность)
        self._state = {
            "trend": 1,      # 1 = uptrend, -1 = downtrend
            "vol": "normal"  # пока не используется, но под regime layer
        }

    def start(self, symbols=None):
        import threading
        import time
        import random

        self._running = True

        def run():
            price = 100.0

            while self._running:
                prev_price = price

                trend = self._state.get("trend", 1)  # 1 или -1

                # 🔹 иногда меняем тренд (редко)
                if random.random() < 0.02:
                    trend *= -1
                    self._state["trend"] = trend

                # 🔹 трендовая компонента
                drift = trend * 0.05

                # 🔹 шум
                noise = random.uniform(-0.02, 0.02)

                price += drift + noise

                # 🔥 тренд по накоплению
                window = self._state.setdefault("trend_window", [])
                window.append(price)

                if len(window) > 10:
                    window.pop(0)

                if len(window) >= 5:
                    if window[-1] > window[0]:
                        trend_label = "up"
                    elif window[-1] < window[0]:
                        trend_label = "down"
                    else:
                        trend_label = "flat"
                else:
                    trend_label = "flat"
                # 🔹 ATR (упрощённый, но стабильный)
                atr = abs(price - prev_price)
                if atr == 0:
                    atr = price * 0.003

                # 🔹 финальный event (ВАЖНО: структура полностью закрыта)
                event = {
                    "type": "QUOTE",
                    "symbol": self.symbol,
                    "last": price,
                    "price": price,
                    "timestamp": time.time(),
                    "features": {
                        "trend": trend_label,
                        "atr": atr,
                        "entry": price,
                    },
                }
                if self.event_bus:
                    self.event_bus.publish(event)

                time.sleep(0.2)

        threading.Thread(target=run, daemon=True).start()

    def stop(self):
        self._running = False