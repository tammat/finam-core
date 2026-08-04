from __future__ import annotations

import os

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FEATURE_STORE_WATERMARK_V1"

DDL = """
CREATE TABLE IF NOT EXISTS analytics.feature_store_watermark_v1 (
    symbol text NOT NULL,
    timeframe text NOT NULL,
    market_snapshot_last_ts timestamptz,
    feature_snapshot_last_ts timestamptz,
    source_version text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, timeframe)
);
"""


def main() -> int:
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
                print("VERDICT=FEATURE_STORE_WATERMARK_V1_SKIPPED")
                return 0

            cur.execute(DDL)

            cur.execute(
                """
                WITH market_state AS (
                    SELECT
                        symbol,
                        timeframe,
                        max(bar_ts) AS market_snapshot_last_ts
                    FROM marketcore.market_snapshot_v1
                    GROUP BY symbol, timeframe
                ),
                feature_state AS (
                    SELECT
                        symbol,
                        timeframe,
                        max(bar_ts) AS feature_snapshot_last_ts
                    FROM analytics.feature_snapshot_v1
                    GROUP BY symbol, timeframe
                ),
                combined AS (
                    SELECT
                        coalesce(m.symbol, f.symbol) AS symbol,
                        coalesce(m.timeframe, f.timeframe) AS timeframe,
                        m.market_snapshot_last_ts,
                        f.feature_snapshot_last_ts
                    FROM market_state m
                    FULL OUTER JOIN feature_state f
                      ON f.symbol = m.symbol
                     AND f.timeframe = m.timeframe
                )
                INSERT INTO analytics.feature_store_watermark_v1 (
                    symbol,
                    timeframe,
                    market_snapshot_last_ts,
                    feature_snapshot_last_ts,
                    source_version,
                    updated_at
                )
                SELECT
                    symbol,
                    timeframe,
                    market_snapshot_last_ts,
                    feature_snapshot_last_ts,
                    %s,
                    now()
                FROM combined
                ON CONFLICT (symbol, timeframe) DO UPDATE SET
                    market_snapshot_last_ts =
                        EXCLUDED.market_snapshot_last_ts,
                    feature_snapshot_last_ts =
                        EXCLUDED.feature_snapshot_last_ts,
                    source_version = EXCLUDED.source_version,
                    updated_at = now()
                WHERE
                    feature_store_watermark_v1
                        .market_snapshot_last_ts
                        IS DISTINCT FROM
                        EXCLUDED.market_snapshot_last_ts
                    OR feature_store_watermark_v1
                        .feature_snapshot_last_ts
                        IS DISTINCT FROM
                        EXCLUDED.feature_snapshot_last_ts
                """,
                (SOURCE_VERSION,),
            )

            changed_rows = max(cur.rowcount, 0)

            cur.execute(
                """
                SELECT
                    count(*)::integer AS rows,
                    count(*) FILTER (
                        WHERE market_snapshot_last_ts IS NULL
                    )::integer AS missing_market,
                    count(*) FILTER (
                        WHERE feature_snapshot_last_ts IS NULL
                    )::integer AS missing_feature
                FROM analytics.feature_store_watermark_v1
                """
            )
            state = cur.fetchone()

    print("=== FEATURE_STORE_WATERMARK_V1 ===")
    print(f"rows={state['rows']}")
    print(f"changed_rows={changed_rows}")
    print(f"missing_market={state['missing_market']}")
    print(f"missing_feature={state['missing_feature']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_STORE_WATERMARK_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
