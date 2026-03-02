import grpc
from datetime import datetime, timezone
from google.protobuf.timestamp_pb2 import Timestamp
from finam_proto.google.type import interval_pb2
from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2, auth_service_pb2_grpc
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc as md_grpc


class FinamClient:

    def __init__(self, host: str, personal_token: str):
        self.host = host
        self.personal_token = personal_token
        self.channel = grpc.secure_channel(host, grpc.ssl_channel_credentials())
        self.jwt = self._auth()

        self.market_stub = md_grpc.MarketDataServiceStub(self.channel)

    def _auth(self):
        auth_stub = auth_service_pb2_grpc.AuthServiceStub(self.channel)
        response = auth_stub.Auth(
            auth_service_pb2.AuthRequest(secret=self.personal_token)
        )
        return response.token

    def get_bars(self, symbol, timeframe, start_time, end_time):
        start_ts = Timestamp()
        start_ts.FromDatetime(start_time)

        end_ts = Timestamp()
        end_ts.FromDatetime(end_time)

        request = md_pb2.BarsRequest(
            symbol=symbol,
            timeframe=timeframe,
            interval=interval_pb2.Interval(
                start_time=start_ts,
                end_time=end_ts,
            )
        )

        metadata = [("authorization", f"Bearer {self.jwt}")]

        return self.market_stub.Bars(request, metadata=metadata)