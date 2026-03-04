from finam_core.auth.token_manager import FinamTokenManager
from finam_core.adapters.rest.rest_client import FinamRestClient
from finam_core.adapters.grpc.market_data import FinamGrpcMarketData
class FinamGateway:

    def __init__(self):

        self.token_manager = FinamTokenManager()

        self.rest = FinamRestClient(self.token_manager)

        self.marketdata = FinamGrpcMarketData(self.token_manager)
        print("FinamGateway initialized")

    def get_assets(self):

        return self.rest.get("/v1/assets")

    def subscribe_bars(self, symbol):

        return self.marketdata.subscribe_bars(symbol, timeframe=1)