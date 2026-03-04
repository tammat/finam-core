import grpc

from finam_core.auth.token_manager import FinamTokenManager

from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc


def main():
    tm = FinamTokenManager()
    token = tm.get_token()

    channel = grpc.secure_channel(
        "api.finam.ru:443",
        grpc.ssl_channel_credentials()
    )

    stub = marketdata_service_pb2_grpc.MarketDataServiceStub(channel)

    metadata = [
        ("authorization", f"Bearer {token}")
    ]
    req = marketdata_service_pb2.SubscribeQuoteRequest(
        symbols=["GAZP@MISX"]
    )
    stream = stub.SubscribeQuote(req, metadata=metadata)
    for msg in stream:
        print(msg)

if __name__ == "__main__":
    main()