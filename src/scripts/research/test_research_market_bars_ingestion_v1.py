#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone

import os
import psycopg2

from finam_core.research.market_data_provider import ResearchBar
from finam_core.research.market_bars_ingestion import ResearchMarketBarsIngestor


def main() -> None:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")

    symbol = "TESTBTCUSD"
    timeframe = "M1"
    ts = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)

    bar = ResearchBar(
        symbol=symbol,
        timeframe=timeframe,
        ts=ts,
        open=100.0,
        high=110.0,
        low=90.0,
        close=105.0,
        volume=123.0,
        source="research_ingestion_test_v1",
        asset_class="crypto",
    )

    ingestor = ResearchMarketBarsIngestor()
    result = ingestor.ingest([bar])

    assert result.rows_seen == 1
    assert result.rows_written == 1
    assert result.source == "research_ingestion_test_v1"

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                select
                    symbol,
                    timeframe,
                    ts,
                    open::float8,
                    high::float8,
                    low::float8,
                    close::float8,
                    volume::float8,
                    source
                from market_bars
                where symbol=%s
                  and timeframe=%s
                  and ts=%s
                """,
                (symbol, timeframe, ts),
            )
            row = cur.fetchone()

    assert row is not None
    assert row[0] == symbol
    assert row[1] == timeframe
    assert row[3] == 100.0
    assert row[4] == 110.0
    assert row[5] == 90.0
    assert row[6] == 105.0
    assert row[7] == 123.0
    assert row[8] == "research_ingestion_test_v1"

    print("RESEARCH_MARKET_BARS_INGESTION_V1_OK")


if __name__ == "__main__":
    main()
