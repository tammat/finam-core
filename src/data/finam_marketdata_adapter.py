from datetime import datetime
from google.protobuf.timestamp_pb2 import Timestamp
from finam_proto.google.type import interval_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2


class FinamMarketDataAdapter:

    def __init__(self, marketdata_stub):
        self.stub = marketdata_stub

    def get_bars(self, symbol: str, timeframe: int,
                 start: datetime, end: datetime):

        start_ts = Timestamp()
        start_ts.FromDatetime(start)

        end_ts = Timestamp()
        end_ts.FromDatetime(end)

        interval = interval_pb2.Interval(
            start_time=start_ts,
            end_time=end_ts
        )

        return self.stub.Bars(
            md_pb2.BarsRequest(
                symbol=symbol,
                timeframe=timeframe,
                interval=interval
            )
        )