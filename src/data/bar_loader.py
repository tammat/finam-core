# Логика загрузки баров из Finam API → PostgreSQL

from datetime import datetime
from storage.repositories.bars_repo import BarsRepository


class BarLoader:
    def __init__(self, repo: BarsRepository):
        self.repo = repo

    def process(self, symbol: str, raw_bars: list):
        """
        raw_bars: [{ts, close, volume}]
        """
        parsed = []

        for b in raw_bars:
            ts = datetime.fromtimestamp(b["timestamp"])
            close = float(b["close"])
            volume = float(b["volume"])

            parsed.append((ts, close, volume))

        self.repo.insert_bars(symbol, parsed)