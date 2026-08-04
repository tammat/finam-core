from __future__ import annotations

import argparse
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FEATURE_STORE_HISTORY_BACKFILL_V1"

DEFAULT_MODE = os.getenv(
    "FEATURE_STORE_MODE",
    "incremental",
).strip().lower()

DEFAULT_OVERLAP_BARS = max(
    20,
    int(os.getenv("FEATURE_STORE_OVERLAP_BARS", "20")),
)

FEATURE_CONTEXT_BARS = 20


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--mode",
        choices=("incremental", "full"),
        default=DEFAULT_MODE,
    )
    parser.add_argument(
        "--overlap-bars",
        type=int,
        default=DEFAULT_OVERLAP_BARS,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    overlap_bars = max(20, args.overlap_bars)
    context_bars = overlap_bars + FEATURE_CONTEXT_BARS
    build_id = str(uuid.uuid4())

    processed_rows = 0

    with psycopg2.connect(DB) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT pg_try_advisory_xact_lock(
                    hashtext(%s)
                ) AS acquired
                """,
                (SOURCE_VERSION,),
            )

            if not cur.fetchone()["acquired"]:
                print("status=SKIPPED_ALREADY_RUNNING")
                print(
                    "VERDICT="
                    "FEATURE_STORE_HISTORY_BACKFILL_V1_SKIPPED"
                )
                return 0

            if args.mode == "full":
                source_sql = """
                    SELECT
                        ms.*,
                        true AS output_row
                    FROM marketcore.market_snapshot_v1 ms
                    WHERE ms.close IS NOT NULL
                """
                source_params: tuple[object, ...] = ()
            else:
                source_sql = """
                    WITH watermark AS (
                        SELECT
                            symbol,
                            timeframe,
                            feature_snapshot_last_ts AS last_feature_ts
                        FROM analytics.feature_store_watermark_v1
                        WHERE feature_snapshot_last_ts IS NOT NULL
                    ),
                    new_rows AS (
                        SELECT
                            ms.*,
                            true AS output_row
                        FROM watermark w
                        JOIN marketcore.market_snapshot_v1 ms
                          ON ms.symbol = w.symbol
                         AND ms.timeframe = w.timeframe
                         AND ms.bar_ts > w.last_feature_ts
                        WHERE ms.close IS NOT NULL
                    ),
                    historical_context AS (
                        SELECT
                            previous_row.symbol,
                            previous_row.display_name,
                            previous_row.asset_class,
                            previous_row.timeframe,
                            previous_row.bar_ts,
                            previous_row.open,
                            previous_row.high,
                            previous_row.low,
                            previous_row.close,
                            previous_row.volume,
                            previous_row.freshness_sec,
                            previous_row.quality_status,
                            previous_row.source_table,
                            previous_row.source_version,
                            previous_row.build_id,
                            previous_row.refreshed_at,
                            (
                                previous_row.context_rank <= %s
                            ) AS output_row
                        FROM watermark w
                        CROSS JOIN LATERAL (
                            SELECT
                                ms.*,
                                row_number() OVER (
                                    ORDER BY ms.bar_ts DESC
                                ) AS context_rank
                            FROM (
                                SELECT candidate.*
                                FROM marketcore.market_snapshot_v1
                                    candidate
                                WHERE candidate.symbol = w.symbol
                                  AND candidate.timeframe =
                                      w.timeframe
                                  AND candidate.bar_ts <=
                                      w.last_feature_ts
                                  AND candidate.close IS NOT NULL
                                ORDER BY candidate.bar_ts DESC
                                LIMIT %s
                            ) ms
                        ) previous_row
                    )
                    SELECT * FROM new_rows
                    UNION ALL
                    SELECT * FROM historical_context
                """
                source_params = (
                    overlap_bars,
                    context_bars,
                )

            sql = f"""
                INSERT INTO analytics.feature_snapshot_v1 (
                    symbol,
                    asset_class,
                    timeframe,
                    bar_ts,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    range_abs,
                    range_pct,
                    body_abs,
                    body_pct,
                    upper_wick_pct,
                    lower_wick_pct,
                    hour_msk,
                    weekday_msk,
                    freshness_sec,
                    market_quality_status,
                    feature_quality_score,
                    return1_pct,
                    return5_pct,
                    volume_sma20,
                    volume_ratio20,
                    source_table,
                    source_version,
                    build_id,
                    refreshed_at
                )
                WITH source_rows AS (
                    {source_sql}
                ),
                calculated AS (
                    SELECT
                        source_rows.*,
                        lag(close, 1) OVER (
                            PARTITION BY symbol, timeframe
                            ORDER BY bar_ts
                        ) AS close_lag1,
                        lag(close, 5) OVER (
                            PARTITION BY symbol, timeframe
                            ORDER BY bar_ts
                        ) AS close_lag5,
                        avg(volume) OVER (
                            PARTITION BY symbol, timeframe
                            ORDER BY bar_ts
                            ROWS BETWEEN 19 PRECEDING
                                     AND CURRENT ROW
                        ) AS vol_sma20
                    FROM source_rows
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
                    high - low,
                    CASE
                        WHEN close <> 0
                        THEN ((high - low) / close) * 100
                        ELSE NULL
                    END,
                    abs(close - open),
                    CASE
                        WHEN close <> 0
                        THEN (
                            abs(close - open) / close
                        ) * 100
                        ELSE NULL
                    END,
                    CASE
                        WHEN close <> 0
                        THEN (
                            (
                                high - greatest(open, close)
                            ) / close
                        ) * 100
                        ELSE NULL
                    END,
                    CASE
                        WHEN close <> 0
                        THEN (
                            (
                                least(open, close) - low
                            ) / close
                        ) * 100
                        ELSE NULL
                    END,
                    EXTRACT(
                        HOUR FROM
                        bar_ts AT TIME ZONE 'Europe/Moscow'
                    )::integer,
                    EXTRACT(
                        ISODOW FROM
                        bar_ts AT TIME ZONE 'Europe/Moscow'
                    )::integer,
                    freshness_sec,
                    quality_status,
                    CASE
                        WHEN quality_status = 'FRESH'
                         AND freshness_sec <= 300
                            THEN 1.0000
                        WHEN quality_status = 'FRESH'
                         AND freshness_sec <= 900
                            THEN 0.8500
                        WHEN quality_status = 'FRESH'
                            THEN 0.7000
                        ELSE 0.2500
                    END,
                    CASE
                        WHEN close_lag1 IS NOT NULL
                         AND close_lag1 <> 0
                        THEN (
                            (close - close_lag1) /
                            close_lag1
                        ) * 100
                        ELSE NULL
                    END,
                    CASE
                        WHEN close_lag5 IS NOT NULL
                         AND close_lag5 <> 0
                        THEN (
                            (close - close_lag5) /
                            close_lag5
                        ) * 100
                        ELSE NULL
                    END,
                    vol_sma20,
                    CASE
                        WHEN vol_sma20 IS NOT NULL
                         AND vol_sma20 <> 0
                        THEN volume / vol_sma20
                        ELSE NULL
                    END,
                    'marketcore.market_snapshot_v1',
                    %s,
                    %s,
                    now()
                FROM calculated
                WHERE output_row
                ON CONFLICT (
                    symbol,
                    timeframe,
                    bar_ts
                ) DO UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close = EXCLUDED.close,
                    volume = EXCLUDED.volume,
                    range_abs = EXCLUDED.range_abs,
                    range_pct = EXCLUDED.range_pct,
                    body_abs = EXCLUDED.body_abs,
                    body_pct = EXCLUDED.body_pct,
                    upper_wick_pct =
                        EXCLUDED.upper_wick_pct,
                    lower_wick_pct =
                        EXCLUDED.lower_wick_pct,
                    return1_pct = EXCLUDED.return1_pct,
                    return5_pct = EXCLUDED.return5_pct,
                    volume_sma20 = EXCLUDED.volume_sma20,
                    volume_ratio20 =
                        EXCLUDED.volume_ratio20,
                    freshness_sec =
                        EXCLUDED.freshness_sec,
                    market_quality_status =
                        EXCLUDED.market_quality_status,
                    feature_quality_score =
                        EXCLUDED.feature_quality_score,
                    source_version =
                        EXCLUDED.source_version,
                    build_id = EXCLUDED.build_id,
                    refreshed_at = now()
                WHERE
                    feature_snapshot_v1.open
                        IS DISTINCT FROM EXCLUDED.open
                    OR feature_snapshot_v1.high
                        IS DISTINCT FROM EXCLUDED.high
                    OR feature_snapshot_v1.low
                        IS DISTINCT FROM EXCLUDED.low
                    OR feature_snapshot_v1.close
                        IS DISTINCT FROM EXCLUDED.close
                    OR feature_snapshot_v1.volume
                        IS DISTINCT FROM EXCLUDED.volume
                    OR feature_snapshot_v1.range_abs
                        IS DISTINCT FROM EXCLUDED.range_abs
                    OR feature_snapshot_v1.range_pct
                        IS DISTINCT FROM EXCLUDED.range_pct
                    OR feature_snapshot_v1.body_abs
                        IS DISTINCT FROM EXCLUDED.body_abs
                    OR feature_snapshot_v1.body_pct
                        IS DISTINCT FROM EXCLUDED.body_pct
                    OR feature_snapshot_v1.upper_wick_pct
                        IS DISTINCT FROM EXCLUDED.upper_wick_pct
                    OR feature_snapshot_v1.lower_wick_pct
                        IS DISTINCT FROM EXCLUDED.lower_wick_pct
                    OR feature_snapshot_v1.return1_pct
                        IS DISTINCT FROM EXCLUDED.return1_pct
                    OR feature_snapshot_v1.return5_pct
                        IS DISTINCT FROM EXCLUDED.return5_pct
                    OR feature_snapshot_v1.volume_sma20
                        IS DISTINCT FROM EXCLUDED.volume_sma20
                    OR feature_snapshot_v1.volume_ratio20
                        IS DISTINCT FROM EXCLUDED.volume_ratio20
            """

            cur.execute(
                sql,
                source_params + (
                    SOURCE_VERSION,
                    build_id,
                ),
            )

            processed_rows = max(cur.rowcount, 0)

            if args.mode == "incremental":
                cur.execute(
                    """
                    UPDATE analytics.feature_store_watermark_v1
                    SET
                        feature_snapshot_last_ts =
                            market_snapshot_last_ts,
                        source_version = %s,
                        updated_at = now()
                    WHERE market_snapshot_last_ts IS NOT NULL
                      AND feature_snapshot_last_ts
                          IS DISTINCT FROM
                          market_snapshot_last_ts
                    """,
                    (SOURCE_VERSION,),
                )

            if args.dry_run:
                conn.rollback()
            else:
                conn.commit()

    print("=== FEATURE_STORE_HISTORY_BACKFILL_V1 ===")
    print(f"mode={args.mode}")
    print(f"overlap_bars={overlap_bars}")
    print(f"context_bars={context_bars}")
    print(f"processed_rows={processed_rows}")
    print(f"dry_run={int(args.dry_run)}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FEATURE_STORE_HISTORY_BACKFILL_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
