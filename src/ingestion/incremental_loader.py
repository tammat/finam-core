from datetime import datetime, timedelta, timezone
from google.protobuf.timestamp_pb2 import Timestamp
from finam_proto.google.type import interval_pb2


class IncrementalBarLoader:

    def __init__(self, market_stub, bar_repo, sync_repo):
        self.market_stub = market_stub
        self.bar_repo = bar_repo
        self.sync_repo = sync_repo

    def load(self, symbol: str, timeframe_enum, timeframe_str: str, jwt_token: str):

        last_ts = self.sync_repo.get_last_ts(symbol, timeframe_str)

        now = datetime.now(timezone.utc)

        if last_ts is None:
            start_time = now - timedelta(days=90)
        else:
            start_time = last_ts

        start_ts = Timestamp()
        start_ts.FromDatetime(start_time)

        end_ts = Timestamp()
        end_ts.FromDatetime(now)

        request = md_pb2.BarsRequest(
            symbol=symbol,
            timeframe=timeframe_enum,
            interval=interval_pb2.Interval(
                start_time=start_ts,
                end_time=end_ts
            )
        )

        metadata = [("authorization", f"Bearer {jwt_token}")]
        response = self.market_stub.Bars(request, metadata=metadata)

        rows = []
        max_ts = None

        for bar in response.bars:
            ts = datetime.fromtimestamp(bar.timestamp.seconds, tz=timezone.utc)

            rows.append({
                "symbol": symbol,
                "timeframe": timeframe_str,
                "ts": ts,
                "open": float(bar.open.value),
                "high": float(bar.high.value),
                "low": float(bar.low.value),
                "close": float(bar.close.value),
                "volume": float(bar.volume.value),
                "source": "FINAM"
            })

            if max_ts is None or ts > max_ts:
                max_ts = ts

        if rows:
            self.bar_repo.upsert_many(rows)
            self.sync_repo.update_last_ts(symbol, timeframe_str, max_ts)

        return len(rows)