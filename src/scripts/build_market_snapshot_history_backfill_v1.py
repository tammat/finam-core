from __future__ import annotations

import argparse
import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKET_SNAPSHOT_HISTORY_BACKFILL_V1"

DEFAULT_MODE = os.getenv(
    "FEATURE_STORE_MODE",
    "incremental",
).strip().lower()

DEFAULT_OVERLAP_BARS = max(
    20,
    int(os.getenv("FEATURE_STORE_OVERLAP_BARS", "20")),
)

FULL_LIMIT = int(os.getenv("BACKFILL_LIMIT", "200000"))


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
                    "MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_SKIPPED"
                )
                return 0

            if args.mode == "full":
                cur.execute(
                    """
                    INSERT INTO marketcore.market_snapshot_v1 (
                        symbol,
                        display_name,
                        asset_class,
                        timeframe,
                        bar_ts,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        freshness_sec,
                        quality_status,
                        source_table,
                        source_version,
                        build_id,
                        refreshed_at
                    )
                    SELECT
                        mb.symbol,
                        '',
                        CASE
                            WHEN mb.symbol LIKE '%%@MISX'
                                THEN 'MOEX_SPOT'
                            WHEN mb.symbol LIKE '%%@RTSX'
                                THEN 'MOEX_FUTURES'
                            WHEN mb.symbol IN ('BTCUSD', 'ETHUSD')
                                THEN 'CRYPTO_PROXY'
                            WHEN mb.symbol IN ('IMOEX', 'IMOEX2')
                                THEN 'INDEX'
                            ELSE 'UNKNOWN'
                        END,
                        mb.timeframe,
                        mb.ts,
                        mb.open,
                        mb.high,
                        mb.low,
                        mb.close,
                        mb.volume,
                        EXTRACT(
                            EPOCH FROM (now() - mb.ts)
                        )::integer,
                        CASE
                            WHEN EXTRACT(
                                EPOCH FROM (now() - mb.ts)
                            )::integer < 86400
                            THEN 'FRESH'
                            ELSE 'STALE'
                        END,
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
                        freshness_sec = EXCLUDED.freshness_sec,
                        quality_status = EXCLUDED.quality_status,
                        source_version = EXCLUDED.source_version,
                        build_id = EXCLUDED.build_id,
                        refreshed_at = now()
                    """,
                    (
                        SOURCE_VERSION,
                        build_id,
                        FULL_LIMIT,
                    ),
                )
            else:
                cur.execute(
                    """
                    WITH watermark AS (
                        SELECT
                            symbol,
                            timeframe,
                            max(bar_ts) AS last_bar_ts
                        FROM marketcore.market_snapshot_v1
                        GROUP BY symbol, timeframe
                    ),
                    new_rows AS (
                        SELECT mb.*
                        FROM watermark w
                        JOIN public.market_bars mb
                          ON mb.symbol = w.symbol
                         AND mb.timeframe = w.timeframe
                         AND mb.ts > w.last_bar_ts
                        WHERE mb.close IS NOT NULL
                    ),
                    overlap_rows AS (
                        SELECT previous_bar.*
                        FROM watermark w
                        CROSS JOIN LATERAL (
                            SELECT mb.*
                            FROM public.market_bars mb
                            WHERE mb.symbol = w.symbol
                              AND mb.timeframe = w.timeframe
                              AND mb.ts <= w.last_bar_ts
                              AND mb.close IS NOT NULL
                            ORDER BY mb.ts DESC
                            LIMIT %s
                        ) previous_bar
                    ),
                    incremental_source AS (
                        SELECT * FROM new_rows
                        UNION
                        SELECT * FROM overlap_rows
                    )
                    INSERT INTO marketcore.market_snapshot_v1 (
                        symbol,
                        display_name,
                        asset_class,
                        timeframe,
                        bar_ts,
                        open,
                        high,
                        low,
                        close,
                        volume,
                        freshness_sec,
                        quality_status,
                        source_table,
                        source_version,
                        build_id,
                        refreshed_at
                    )
                    SELECT
                        mb.symbol,
                        '',
                        CASE
                            WHEN mb.symbol LIKE '%%@MISX'
                                THEN 'MOEX_SPOT'
                            WHEN mb.symbol LIKE '%%@RTSX'
                                THEN 'MOEX_FUTURES'
                            WHEN mb.symbol IN ('BTCUSD', 'ETHUSD')
                                THEN 'CRYPTO_PROXY'
                            WHEN mb.symbol IN ('IMOEX', 'IMOEX2')
                                THEN 'INDEX'
                            ELSE 'UNKNOWN'
                        END,
                        mb.timeframe,
                        mb.ts,
                        mb.open,
                        mb.high,
                        mb.low,
                        mb.close,
                        mb.volume,
                        EXTRACT(
                            EPOCH FROM (now() - mb.ts)
                        )::integer,
                        CASE
                            WHEN EXTRACT(
                                EPOCH FROM (now() - mb.ts)
                            )::integer < 86400
                            THEN 'FRESH'
                            ELSE 'STALE'
                        END,
                        'public.market_bars',
                        %s,
                        %s,
                        now()
                    FROM incremental_source mb
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
                        freshness_sec = EXCLUDED.freshness_sec,
                        quality_status = EXCLUDED.quality_status,
                        source_version = EXCLUDED.source_version,
                        build_id = EXCLUDED.build_id,
                        refreshed_at = now()
                    """,
                    (
                        overlap_bars,
                        SOURCE_VERSION,
                        build_id,
                    ),
                )

            processed_rows = max(cur.rowcount, 0)

            if args.dry_run:
                conn.rollback()
            else:
                conn.commit()

    print("=== MARKET_SNAPSHOT_HISTORY_BACKFILL_V1 ===")
    print(f"mode={args.mode}")
    print(f"overlap_bars={overlap_bars}")
    print(f"processed_rows={processed_rows}")
    print(f"dry_run={int(args.dry_run)}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
