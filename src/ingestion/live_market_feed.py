# src/ingestion/live_market_feed.py
import os
import grpc
from finam_proto.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2 as md_pb2,
)
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc as md_grpc

class LiveMarketFeed:
    def __init__(self, host=None, jwt=None):

        self.host = host or os.getenv("FINAM_GRPC_HOST") or os.getenv("FINAM_API_HOST")
        assert self.host, "Set FINAM_GRPC_HOST or FINAM_API_HOST"

        self.jwt = (
                jwt
                or os.getenv("FINAM_JWT")
                or os.getenv("FINAM_TOKEN")
                or os.getenv("JWT")
        )

        assert self.jwt, "Set FINAM_JWT / FINAM_TOKEN"

        self.jwt = self.jwt.strip().strip('"').strip("'")

        # 🔥 ВАЖНО — без Bearer / JWT
        self.metadata = [
            ("authorization", self.jwt)
        ]

        # ---------- ЭТО У ТЕБЯ СЕЙЧАС ОТСУТСТВУЕТ ----------

        self.channel = grpc.secure_channel(
            self.host,
            grpc.ssl_channel_credentials()
        )

        self.stub = md_grpc.MarketDataServiceStub(self.channel)
    def subscribe_quotes(self, symbols: list[str]):
        # В твоём proto: SubscribeQuoteRequest имеет поле ['symbols']
        req = md_pb2.SubscribeQuoteRequest(symbols=symbols)

        print("SUBSCRIBED. Waiting for quotes... (Ctrl+C to stop)")
        print("Connected to:", self.host)
        print("Metadata:", self.metadata)
        try:
            for msg in self.stub.SubscribeQuote(req, metadata=self.metadata):
                print("RAW:", msg)
            for msg in self.stub.SubscribeQuote(req, metadata=self.metadata):
                print(msg)
        except grpc.RpcError as e:
            print("Stream error:", e)
            # Если будет UNAUTHENTICATED — поменяй Bearer -> JWT (см. ниже)
            raise

    def close(self):
        try:
            self.channel.close()
        except Exception:
            pass