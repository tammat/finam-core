from datetime import datetime, timedelta, timezone
from storage.postgres import PostgresStorage
from data.finam_history_client import FinamHistoryClient


class HistoryLoader:

    def __init__(self):
        self.storage = PostgresStorage()
        self.client = FinamHistoryClient()

    def load(self, symbol, days=365, interval="M5"):

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        candles = self.client.get_candles(
            symbol=symbol,
            interval=interval,
            start=start,
            end=end
        )

        for c in candles:
            self.storage.log_market_price(
                symbol=symbol,
                timestamp=c["timestamp"],
                close_price=c["close"],
                volume=c["volume"]
            )

        print(f"Loaded {len(candles)} candles")