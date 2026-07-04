from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FEATURE_STORE_V1"


def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("DELETE FROM analytics.feature_snapshot_v1;")

            cur.execute("""
                INSERT INTO analytics.feature_snapshot_v1 (
                    symbol, asset_class, timeframe, bar_ts,
                    open, high, low, close, volume,
                    range_abs, range_pct,
                    body_abs, body_pct,
                    upper_wick_pct, lower_wick_pct,
                    hour_msk, weekday_msk,
                    freshness_sec, market_quality_status, feature_quality_score,
                    source_table, source_version, build_id, refreshed_at
                )
                SELECT
                    symbol,
                    asset_class,
                    timeframe,
                    bar_ts,
                    open,
                    high,
                    low,
                    close,
                    volume,

                    (high - low) AS range_abs,
                    CASE WHEN close IS NOT NULL AND close <> 0
                         THEN ((high - low) / close) * 100 ELSE NULL END AS range_pct,

                    abs(close - open) AS body_abs,
                    CASE WHEN close IS NOT NULL AND close <> 0
                         THEN (abs(close - open) / close) * 100 ELSE NULL END AS body_pct,

                    CASE WHEN close IS NOT NULL AND close <> 0
                         THEN ((high - greatest(open, close)) / close) * 100 ELSE NULL END AS upper_wick_pct,

                    CASE WHEN close IS NOT NULL AND close <> 0
                         THEN ((least(open, close) - low) / close) * 100 ELSE NULL END AS lower_wick_pct,

                    EXTRACT(HOUR FROM bar_ts AT TIME ZONE 'Europe/Moscow')::int AS hour_msk,
                    EXTRACT(ISODOW FROM bar_ts AT TIME ZONE 'Europe/Moscow')::int AS weekday_msk,

                    freshness_sec,
                    quality_status,
                    CASE
                        WHEN quality_status = 'FRESH' AND freshness_sec <= 300 THEN 1.0000
                        WHEN quality_status = 'FRESH' AND freshness_sec <= 900 THEN 0.8500
                        WHEN quality_status = 'FRESH' THEN 0.7000
                        ELSE 0.2500
                    END AS feature_quality_score,

                    'marketcore.market_snapshot_v1',
                    %s,
                    %s,
                    now()
                FROM marketcore.market_snapshot_v1
                WHERE bar_ts IS NOT NULL
                  AND close IS NOT NULL
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
                    hour_msk=EXCLUDED.hour_msk,
                    weekday_msk=EXCLUDED.weekday_msk,
                    freshness_sec=EXCLUDED.freshness_sec,
                    market_quality_status=EXCLUDED.market_quality_status,
                    feature_quality_score=EXCLUDED.feature_quality_score,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (SOURCE_VERSION, build_id))

            cur.execute("SELECT count(*) AS rows FROM analytics.feature_snapshot_v1;")
            rows = int(cur.fetchone()["rows"])

            cur.execute("SELECT count(DISTINCT symbol) AS symbols FROM analytics.feature_snapshot_v1;")
            symbols = int(cur.fetchone()["symbols"])

    print("=== FEATURE_STORE_V1 ===")
    print(f"rows_written={rows}")
    print(f"symbols={symbols}")
    print(f"build_id={build_id}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_STORE_V1_READY")


if __name__ == "__main__":
    main()
