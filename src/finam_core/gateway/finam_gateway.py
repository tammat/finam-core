from __future__ import annotations

from finam_core.auth.token_manager import FinamTokenManager
from finam_core.adapters.rest.rest_client import FinamRestClient
from finam_core.adapters.grpc.market_data import FinamMarketDataClient


class FinamGateway:
    def __init__(self, event_bus=None):
        self.event_bus = event_bus
        self.token_manager = FinamTokenManager()
        self.rest = FinamRestClient(self.token_manager)

        # MarketDataClient требует EventBus; без него gateway остаётся REST-only.
        self.marketdata = (
            FinamMarketDataClient(event_bus=self.event_bus)
            if self.event_bus is not None
            else None
        )

        print("FinamGateway initialized")

    def get_assets(self):
        return self.rest.get("/v1/assets")

    def subscribe_bars(self, symbol):
        if self.marketdata is None:
            raise RuntimeError("MarketData client requires event_bus")
        return self.marketdata.subscribe_bars(symbol, timeframe=1)
