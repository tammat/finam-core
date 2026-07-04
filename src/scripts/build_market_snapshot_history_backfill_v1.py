from __future__ import annotations

import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("BACKFILL_LIMIT", "200000"))
SOURCE_VERSION = "MARKET_SNAPSHOT_HISTORY_BACKFILL_V1"

def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO marketcore.market_snapshot_v1 (
                    symbol, display_name, asset_class, timeframe, bar_ts,
                    open, high, low, close, volume,
                    freshness_sec, quality_status,
                    source_table, source_version, build_id, refreshed_at
                )
                SELECT
                    mb.symbol,
                    '',
                    CASE
                        WHEN mb.symbol LIKE '%%@MISX' THEN 'MOEX_SPOT'
                        WHEN mb.symbol LIKE '%%@RTSX' THEN 'MOEX_FUTURES'
                        WHEN mb.symbol IN ('BTCUSD','ETHUSD') THEN 'CRYPTO_PROXY'
                        WHEN mb.symbol='IMOEX' THEN 'INDEX'
                        ELSE 'UNKNOWN'
                    END,
                    mb.timeframe,
                    mb.ts,
                    mb.open,
                    mb.high,
                    mb.low,
                    mb.close,
                    mb.volume,
                    EXTRACT(EPOCH FROM (now() - mb.ts::timestamptz))::int,
                    CASE WHEN EXTRACT(EPOCH FROM (now() - mb.ts::timestamptz))::int < 86400 THEN 'FRESH' ELSE 'STALE' END,
                    'public.market_bars',
                    %s,
                    %s,
                    now()
                FROM (
                    SELECT *
                    FROM public.market_bars
                    WHERE ts IS NOT NULL
                      AND close IS NOT NULL
                    ORDER BY ts DESC
                    LIMIT %s
                ) mb
                ON CONFLICT (symbol, timeframe, bar_ts) DO UPDATE SET
                    open=EXCLUDED.open,
                    high=EXCLUDED.high,
                    low=EXCLUDED.low,
                    close=EXCLUDED.close,
                    volume=EXCLUDED.volume,
                    freshness_sec=EXCLUDED.freshness_sec,
                    quality_status=EXCLUDED.quality_status,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (SOURCE_VERSION, build_id, LIMIT))

            cur.execute("SELECT count(*) AS rows FROM marketcore.market_snapshot_v1;")
            rows = int(cur.fetchone()["rows"])

    print("=== MARKET_SNAPSHOT_HISTORY_BACKFILL_V1 ===")
    print(f"market_snapshot_rows={rows}")
    print(f"backfill_limit={LIMIT}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY")

if __name__ == "__main__":
    main()
