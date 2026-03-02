import os
import time
import grpc
from datetime import datetime, timezone

from finam_proto.grpc.tradeapi.v1.marketdata import (
    marketdata_service_pb2 as md_pb2,
    marketdata_service_pb2_grpc as md_grpc,
)


class LiveBarsFeed:
    def __init__(self, host=None, jwt=None):
        self.host = host or os.getenv("FINAM_GRPC_HOST") or os.getenv("FINAM_API_HOST")
        assert self.host, "Set FINAM_GRPC_HOST or FINAM_API_HOST"

        self.jwt = (
            jwt
            or os.getenv("FINAM_JWT")
            or os.getenv("FINAM_TOKEN")
            or os.getenv("JWT")
        )
        assert self.jwt, "Set FINAM_TOKEN / FINAM_JWT"

        self.jwt = self.jwt.strip().strip('"').strip("'")
        self.metadata = [("authorization", self.jwt)]

        self.channel = grpc.secure_channel(
            self.host,
            grpc.ssl_channel_credentials(),
        )
        self.stub = md_grpc.MarketDataServiceStub(self.channel)

    def subscribe_bars(self, symbol: str, timeframe):
        """
        symbol: "SBER@MISX"
        timeframe: md_pb2.TimeFrame.TIME_FRAME_M1 / H1 / etc.
        """

        req = md_pb2.SubscribeBarsRequest(
            symbol=symbol,
            timeframe=timeframe,
        )

        print(f"SUBSCRIBED BARS: {symbol}")

        while True:
            try:
                for msg in self.stub.SubscribeBars(
                    req,
                    metadata=self.metadata,
                ):
                    yield msg

            except grpc.RpcError as e:
                print("Stream error:", e.code(), e.details())
                print("Reconnecting in 3 sec...")
                time.sleep(3)