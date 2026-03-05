import grpc
import threading
import time
from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc


class FinamMarketDataClient:

    def __init__(self, event_bus):

        self.event_bus = event_bus
        self.state = {}  # symbol -> last known fields        tm = FinamTokenManager()
        self.last_msg_ts = time.time()
        self.tm = FinamTokenManager()
        self.token = self.tm.get_token()
        self.channel = grpc.secure_channel(
            "api.finam.ru:443",
            grpc.ssl_channel_credentials()
        )

        self.stub = marketdata_service_pb2_grpc.MarketDataServiceStub(self.channel)

    def subscribe_quotes(self, symbols):

        while True:

            try:

                metadata = [
                    ("authorization", f"Bearer {self.token}")
                ]

                req = marketdata_service_pb2.SubscribeQuoteRequest(
                    symbols=symbols
                )

                stream = self.stub.SubscribeQuote(req, metadata=metadata)

                self._handle_stream(stream)

            except grpc.RpcError as e:

                code = e.code()

                if code == grpc.StatusCode.UNAUTHENTICATED:
                    print("MarketData: token expired, refreshing")
                    self.token = self.tm.get_token()
                else:
                    print("MarketData reconnect:", e)

                time.sleep(2)

    def start(self, symbols):

        t1 = threading.Thread(
            target=self.subscribe_quotes,
            args=(symbols,),
            daemon=True
        )

        t2 = threading.Thread(
            target=self._monitor_heartbeat,
            daemon=True
        )

        t1.start()
        t2.start()
    def _update_state_from_quote(self, quote):

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

        return symbol, state

    def _publish_quote(self, symbol, state):

        event = {
            "type": "QUOTE",
            "symbol": symbol,
            **state
        }

        self.event_bus.publish(event)

    def _handle_stream(self, stream):

        for msg in stream:

            for quote in msg.quote:
                symbol, state = self._update_state_from_quote(quote)

                self._publish_quote(symbol, state)

    def _handle_stream(self, stream):

        for msg in stream:

            self.last_msg_ts = time.time()

            for quote in msg.quote:
                symbol, state = self._update_state_from_quote(quote)

                self._publish_quote(symbol, state)

    def _monitor_heartbeat(self):

        while True:

            if time.time() - self.last_msg_ts > 10:

                print("MarketData heartbeat timeout — reconnecting")

                try:
                    self.channel.close()
                except:
                    pass

            time.sleep(3)