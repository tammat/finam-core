# src/scripts/live_bars.py

from core.memory_bar_buffer import MemoryBarBuffer, Bar
from ingestion.live_bars_feed import LiveBarsFeed
import os
from finam_proto.grpc.tradeapi.v1.marketdata import marketdata_service_pb2 as md_pb2

from ingestion.live_bars_feed import LiveBarsFeed
from storage.postgres_storage import PostgresStorage
from datetime import datetime, timezone
def create_storage():
    dsn = os.getenv("POSTGRES_DSN")

    if dsn:
        return PostgresStorage(dsn=dsn)

    return PostgresStorage(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 5432)),
        username=os.getenv("DB_USERNAME"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_BASE"),
        min_conn=int(os.getenv("DB_MIN_CONN", 1)),
        max_conn=int(os.getenv("DB_MAX_CONN", 5)),
    )


storage = create_storage()
def run_bars_pipeline(feed, storage, buffer, symbol, timeframe):

    for msg in feed.subscribe_bars(symbol, timeframe):

        if not msg.bar:
            continue

        bar = msg.bar

        ts = datetime.fromtimestamp(
            bar.timestamp.seconds,
            tz=timezone.utc,
        )

        bar_obj = Bar(
            symbol=symbol,
            timeframe=str(timeframe),
            ts=ts,
            open=float(bar.open.value),
            high=float(bar.high.value),
            low=float(bar.low.value),
            close=float(bar.close.value),
            volume=float(bar.volume.value),
        )

        added = buffer.append(bar_obj)

        if not added:
            continue

        storage.append_bar(
            symbol=symbol,
            timeframe=str(timeframe),
            ts=ts,
            open=bar_obj.open,
            high=bar_obj.high,
            low=bar_obj.low,
            close=bar_obj.close,
            volume=bar_obj.volume,
        )

        print("BAR:", ts, bar_obj.close)

def main():
    feed = LiveBarsFeed()
    storage = PostgresStorage(...)  # твой класс
    buffer = MemoryBarBuffer(maxlen=1000)

    run_bars_pipeline(
        feed=feed,
        storage=storage,
        buffer=buffer,
        symbol="SBER@MISX",
        timeframe=md_pb2.TimeFrame.TIME_FRAME_M1,
    )

if __name__ == "__main__":
    main()