# storage/market_sync_repository.py

from __future__ import annotations
from datetime import datetime


class MarketSyncRepository:
    """Stores last successful sync timestamp per (symbol, timeframe)."""

    def __init__(self, storage):
        self.storage = storage

    def get_last_ts(self, symbol: str, timeframe: str) -> datetime | None:
        row = self.storage.fetch_one(
            """
            SELECT last_synced_ts
            FROM market_sync_state
            WHERE symbol = %s AND timeframe = %s
            """,
            (symbol, timeframe),
        )
        return row[0] if row else None

    def upsert_last_ts(self, symbol: str, timeframe: str, ts: datetime) -> None:
        self.storage.execute(
            """
            INSERT INTO market_sync_state (symbol, timeframe, last_synced_ts)
            VALUES (%s, %s, %s)
            ON CONFLICT (symbol, timeframe)
            DO UPDATE SET
                last_synced_ts = EXCLUDED.last_synced_ts,
                updated_at = now()
            """,
            (symbol, timeframe, ts),
        )