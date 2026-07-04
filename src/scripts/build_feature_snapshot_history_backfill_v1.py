from __future__ import annotations

import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FEATURE_STORE_HISTORY_BACKFILL_V1"

def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO analytics.feature_snapshot_v1 (
                    symbol, asset_class, timeframe, bar_ts,
                    open, high, low, close, volume,
                    range_abs, range_pct,
                    body_abs, body_pct,
                    upper_wick_pct, lower_wick_pct,
                    hour_msk, weekday_msk,
                    freshness_sec, market_quality_status, feature_quality_score,
                    return1_pct, return5_pct, volume_sma20, volume_ratio20,
                    source_table, source_version, build_id, refreshed_at
                )
                WITH src AS (
                    SELECT
                        ms.*,
                        lag(close, 1) OVER (PARTITION BY symbol, timeframe ORDER BY bar_ts) AS close_lag1,
                        lag(close, 5) OVER (PARTITION BY symbol, timeframe ORDER BY bar_ts) AS close_lag5,
                        avg(volume) OVER (
                            PARTITION BY symbol, timeframe
                            ORDER BY bar_ts
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) AS vol_sma20
                    FROM marketcore.market_snapshot_v1 ms
                    WHERE close IS NOT NULL
                )
                SELECT
                    symbol, asset_class, timeframe, bar_ts,
                    open, high, low, close, volume,

                    (high - low),
                    CASE WHEN close <> 0 THEN ((high - low) / close) * 100 ELSE NULL END,

                    abs(close - open),
                    CASE WHEN close <> 0 THEN (abs(close - open) / close) * 100 ELSE NULL END,

                    CASE WHEN close <> 0 THEN ((high - greatest(open, close)) / close) * 100 ELSE NULL END,
                    CASE WHEN close <> 0 THEN ((least(open, close) - low) / close) * 100 ELSE NULL END,

                    EXTRACT(HOUR FROM bar_ts AT TIME ZONE 'Europe/Moscow')::int,
                    EXTRACT(ISODOW FROM bar_ts AT TIME ZONE 'Europe/Moscow')::int,

                    freshness_sec,
                    quality_status,
                    CASE
                        WHEN quality_status = 'FRESH' AND freshness_sec <= 300 THEN 1.0000
                        WHEN quality_status = 'FRESH' AND freshness_sec <= 900 THEN 0.8500
                        WHEN quality_status = 'FRESH' THEN 0.7000
                        ELSE 0.2500
                    END,

                    CASE WHEN close_lag1 IS NOT NULL AND close_lag1 <> 0 THEN ((close - close_lag1) / close_lag1) * 100 ELSE NULL END,
                    CASE WHEN close_lag5 IS NOT NULL AND close_lag5 <> 0 THEN ((close - close_lag5) / close_lag5) * 100 ELSE NULL END,
                    vol_sma20,
                    CASE WHEN vol_sma20 IS NOT NULL AND vol_sma20 <> 0 THEN volume / vol_sma20 ELSE NULL END,

                    'marketcore.market_snapshot_v1',
                    %s,
                    %s,
                    now()
                FROM src
                ON CONFLICT (symbol, timeframe, bar_ts) DO UPDATE SET
                    open=EXCLUDED.open,
                    high=EXCLUDED.high,
                    low=EXCLUDED.low,
                    close=EXCLUDED.close,
                    volume=EXCLUDED.volume,
                    range_abs=EXCLUDED.range_abs,
                    range_pct=EXCLUDED.range_pct,
                    body_abs=EXCLUDED.body_abs,
                    body_pct=EXCLUDED.body_pct,
                    upper_wick_pct=EXCLUDED.upper_wick_pct,
                    lower_wick_pct=EXCLUDED.lower_wick_pct,
                    return1_pct=EXCLUDED.return1_pct,
                    return5_pct=EXCLUDED.return5_pct,
                    volume_sma20=EXCLUDED.volume_sma20,
                    volume_ratio20=EXCLUDED.volume_ratio20,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (SOURCE_VERSION, build_id))

            cur.execute("SELECT count(*) AS rows FROM analytics.feature_snapshot_v1;")
            rows = int(cur.fetchone()["rows"])
            cur.execute("SELECT count(DISTINCT symbol) AS symbols FROM analytics.feature_snapshot_v1;")
            symbols = int(cur.fetchone()["symbols"])

    print("=== FEATURE_STORE_HISTORY_BACKFILL_V1 ===")
    print(f"feature_rows={rows}")
    print(f"feature_symbols={symbols}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_STORE_HISTORY_BACKFILL_V1_READY")

if __name__ == "__main__":
    main()
