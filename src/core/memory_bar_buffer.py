from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class Bar:
    symbol: str
    timeframe: str
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MemoryBarBuffer:

    def __init__(self, maxlen: int = 500):
        self.maxlen = maxlen
        self._buffers = {}

    def append(self, bar: Bar):
        key = (bar.symbol, bar.timeframe)

        if key not in self._buffers:
            self._buffers[key] = deque(maxlen=self.maxlen)

        buf = self._buffers[key]

        # дедупликация по времени
        if buf and bar.ts <= buf[-1].ts:
            return False

        buf.append(bar)
        return True

    def get_last(self, symbol: str, timeframe: str, n: int = 1) -> List[Bar]:
        buf = self._buffers.get((symbol, timeframe))
        if not buf:
            return []
        return list(buf)[-n:]

    def get_all(self, symbol: str, timeframe: str) -> List[Bar]:
        return list(self._buffers.get((symbol, timeframe), []))