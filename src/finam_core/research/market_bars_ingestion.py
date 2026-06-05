from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, Optional

import psycopg2

from finam_core.research.market_data_provider import ResearchBar


@dataclass(frozen=True, slots=True)
class MarketBarsIngestionResult:
    rows_seen: int
    rows_written: int
    source: str


class ResearchMarketBarsIngestor:
    def __init__(self, dsn: Optional[str] = None):
        self.dsn = dsn or os.getenv("DATABASE_URL")
        if not self.dsn:
            raise RuntimeError("DATABASE_URL is not set")

    def ingest(self, bars: Iterable[ResearchBar]) -> MarketBarsIngestionResult:
        rows = list(bars)
        if not rows:
            return MarketBarsIngestionResult(rows_seen=0, rows_written=0, source="none")

        source = rows[0].source

        sql = """
            insert into market_bars (
                symbol,
                timeframe,
                ts,
                open,
                high,
                low,
                close,
                volume,
                source
            )
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            on conflict (symbol, timeframe, ts)
            do update set
                open = excluded.open,
                high = excluded.high,
                low = excluded.low,
                close = excluded.close,
                volume = excluded.volume,
                source = excluded.source
        """

        payload = [
            (
                b.symbol,
                b.timeframe,
                b.ts,
                b.open,
                b.high,
                b.low,
                b.close,
                b.volume,
                b.source,
            )
            for b in rows
        ]

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.executemany(sql, payload)

        return MarketBarsIngestionResult(
            rows_seen=len(rows),
            rows_written=len(rows),
            source=source,
        )
