# src/strategy/simple_ma_strategy.py

from dataclasses import dataclass
from typing import Optional, List

from core.memory_bar_buffer import Bar


@dataclass(frozen=True)
class Signal:
    symbol: str
    timeframe: str
    ts: object  # datetime
    side: str   # "BUY" | "SELL"
    reason: str


class SimpleMAStrategy:
    """
    SMA fast/slow crossover.
    - BUY: fast crosses above slow
    - SELL: fast crosses below slow
    """

    def __init__(self, fast: int = 9, slow: int = 21):
        assert fast > 1 and slow > fast
        self.fast = fast
        self.slow = slow

    def on_bar(self, bars: List[Bar]) -> Optional[Signal]:
        # Нужно минимум slow+1 бар, чтобы проверить пересечение на двух точках
        if len(bars) < self.slow + 1:
            return None

        # Берем последние (slow+1) баров
        w = bars[-(self.slow + 1):]
        closes = [b.close for b in w]

        # SMA на предыдущем баре
        prev_fast = sum(closes[-(self.fast + 1):-1]) / self.fast
        prev_slow = sum(closes[-(self.slow + 1):-1]) / self.slow

        # SMA на текущем баре
        cur_fast = sum(closes[-self.fast:]) / self.fast
        cur_slow = sum(closes[-self.slow:]) / self.slow

        last_bar = w[-1]

        # crossover вверх
        if prev_fast <= prev_s