from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc as md_grpc


class FinamGrpcMarketData:

    def __init__(self, channel):
        self.stub = md_grpc.MarketDataServiceStub(channel)

    def subscribe_quotes(self, symbol: str):

        req = md_pb2.SubscribeQuoteRequest(
            symbol=symbol
        )

        stream = self.stub.SubscribeQuote(req)

        for quote in stream:
            yield quote