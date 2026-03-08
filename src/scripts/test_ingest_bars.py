import os
import grpc
from datetime import datetime, timedelta, timezone

from google.protobuf.timestamp_pb2 import Timestamp

from finam_proto.grpc.tradeapi.v1.auth import auth_service_pb2, auth_service_pb2_grpc
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2_grpc as md_grpc
from finam_proto.google.type import interval_pb2
from storage.postgres_storage import PostgresStorage
from storage.market_bar_repository import MarketBarRepository
from storage.market_sync_repository import MarketSyncRepository
print("SCRIPT STARTED")

# ---------------------------------------------------------
# CONFIG
# ---------------------------------------------------------

FINAM_HOST = "tradeapi.finam.ru:443"
PERSONAL_TOKEN = os.environ.get("FINAM_TOKEN")
POSTGRES_DSN = os.environ.get("POSTGRES_DSN")

# Русский коммент: SYMBOL из окружения; дефолт — NGH6@RTSX
SYMBOL = os.getenv("SYMBOL") or "NGH6@RTSX"
TIMEFRAME = md_pb2.TimeFrame.TIME_FRAME_H1
TIMEFRAME_STR = "H1"
DAYS_BACK = 5


if not PERSONAL_TOKEN:
    raise RuntimeError("FINAM_TOKEN not set in environment")

if not POSTGRES_DSN:
    raise RuntimeError("POSTGRES_DSN not set in environment")

# ---------------------------------------------------------
# INIT STORAGE
# ---------------------------------------------------------

storage = PostgresStorage(POSTGRES_DSN)
sync_repo = MarketSyncRepository(storage)
repo = MarketBarRepository(storage)
# ---------------------------------------------------------
# 1. AUTH -> JWT
# ---------------------------------------------------------

channel = grpc.secure_channel(FINAM_HOST, grpc.ssl_channel_credentials())

auth_stub = auth_service_pb2_grpc.AuthServiceStub(channel)

auth_response = auth_stub.Auth(
    auth_service_pb2.AuthRequest(secret=PERSONAL_TOKEN)
)

jwt_token = auth_response.token

print("JWT OK:", jwt_token.count("."))


# ---------------------------------------------------------
# 2. LOAD BARS
# ---------------------------------------------------------

market_stub = md_grpc.MarketDataServiceStub(channel)

now = datetime.now(timezone.utc)
sync_repo = MarketSyncRepository(storage)
last_synced = sync_repo.get_last_ts(SYMBOL, TIMEFRAME_STR)
if last_synced:
    # +1 timeframe шаг
    start_time = last_synced + timedelta(hours=1)
    print("Incremental from:", start_time)
else:
    start_time = now - timedelta(days=DAYS_BACK)
    print("Initial load from:", start_time)
# Normalize to UTC
start_time = start_time.astimezone(timezone.utc)
now_utc = datetime.now(timezone.utc)

# Prevent invalid or future range
if start_time >= now_utc:
    print("Nothing to sync. Start >= now.")
    channel.close()
    exit(0)

# Optional: trim to last closed bar
if TIMEFRAME_STR == "H1":
    now_utc = now_utc.replace(minute=0, second=0, microsecond=0)

end_time = now_utc
start_ts = Timestamp()
start_ts.FromDatetime(start_time)

end_ts = Timestamp()
end_ts.FromDatetime(now)

request = md_pb2.BarsRequest(
    symbol=SYMBOL,
    timeframe=TIMEFRAME,
    interval=interval_pb2.Interval(
        start_time=start_ts,
        end_time=end_ts
    )
)
metadata = [("authorization", f"Bearer {jwt_token}")]

response = market_stub.Bars(request, metadata=metadata)

print("Bars received:", len(response.bars))


# ---------------------------------------------------------
# 3. SAVE TO POSTGRES
# ---------------------------------------------------------


rows = []

for bar in response.bars:
    ts = datetime.fromtimestamp(bar.timestamp.seconds, tz=timezone.utc)

    rows.append(
        {
            "symbol": SYMBOL,
            "timeframe": "H1",
            "ts": ts,
            "open": float(bar.open.value),
            "high": float(bar.high.value),
            "low": float(bar.low.value),
            "close": float(bar.close.value),
            "volume": float(bar.volume.value),
            "source": "FINAM",
        }
    )

inserted = repo.upsert_many(rows)
# Persist sync cursor (max ts we have ingested)
if rows:
    # rows are dicts
    max_ts = max(r["ts"] for r in rows)
    sync_repo = MarketSyncRepository(storage)
    sync_repo.upsert_last_ts(SYMBOL, TIMEFRAME_STR, max_ts)
print("Inserted rows:", inserted)

channel.close()