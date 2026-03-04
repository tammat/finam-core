import grpc
import threading

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc


class FinamMarketDataClient:

    def __init__(self, event_bus):

        self.event_bus = event_bus
        self.state = {}
        tm = FinamTokenManager()
        self.token = tm.get_token()

        self.channel = grpc.secure_channel(
            "api.finam.ru:443",
            grpc.ssl_channel_credentials()
        )

        self.stub = marketdata_service_pb2_grpc.MarketDataServiceStub(self.channel)

    def subscribe_quotes(self, symbols):

        metadata = [
            ("authorization", f"Bearer {self.token}")
        ]

        req = marketdata_service_pb2.SubscribeQuoteRequest(
            symbols=symbols
        )

        stream = self.stub.SubscribeQuote(req, metadata=metadata)

        for msg in stream:

            for quote in msg.quote:

                symbol = quote.symbol

                state = self.state.setdefault(symbol, {
                    "bid": None,
                    "ask": None,
                    "last": None,
                    "volume": None
                })

                if quote.bid.value:
                    state["bid"] = float(quote.bid.value)

                if quote.ask.value:
                    state["ask"] = float(quote.ask.value)

                if quote.last.value:
                    state["last"] = float(quote.last.value)

                if quote.volume.value:
                    state["volume"] = float(quote.volume.value)

                event = {
                    "type": "QUOTE",
                    "symbol": symbol,
                    **state
                }

                self.event_bus.publish(event)

                self.event_bus.publish(event)
    def start(self, symbols):

        t = threading.Thread(
            target=self.subscribe_quotes,
            args=(symbols,),
            daemon=True
        )

        t.start()