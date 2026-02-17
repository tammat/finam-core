# gRPC client для загрузки исторических свечей из Finam

from datetime import datetime
from finam_client import FinamClient


class FinamHistoryClient:

    def __init__(self):
        self.client = FinamClient()

    def get_candles(self, symbol, interval, start, end):

        # interval: M1, M5, M15, H1, D1

        candles = self.client.get_candles(
            symbol=symbol,
            interval=interval,
            start=start,
            end=end
        )

        normalized = []

        for c in candles:
            normalized.append({
                "timestamp": c.timestamp,
                "close": float(c.close.value),
                "volume": float(c.volume.value)
            })

        return normalized