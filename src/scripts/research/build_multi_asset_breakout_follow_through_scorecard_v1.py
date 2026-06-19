#!/usr/bin/env python3
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row


HORIZONS_MIN = (3, 5, 10, 15)


def pct_change(entry: Decimal | None, future: Decimal | None) -> Decimal | None:
    if entry is None or future is None or entry == 0:
        return None
    return (future - entry) / entry


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_multi_asset_breakout_follow_through_v1 (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                ready_row_id BIGINT NOT NULL,
                ready_snapshot_id BIGINT NOT NULL,
                symbol TEXT NOT NULL,
                asset_class TEXT,
                timeframe TEXT,
                role TEXT,
                ready_created_at TIMESTAMPTZ NOT NULL,
                ready_close NUMERIC,
                horizon_min INTEGER NOT NULL,
                future_row_id BIGINT,
                future_created_at TIMESTAMPTZ,
                future_close NUMERIC,
                return_pct NUMERIC,
                direction_ok BOOLEAN,
                status TEXT NOT NULL,
                UNIQUE (ready_row_id, horizon_min)
            )
            """
        )
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_breakout_follow_through_v1_symbol_time
            ON analytics_multi_asset_breakout_follow_through_v1(symbol, timeframe, ready_created_at DESC)
            """
        )
    conn.commit()


def fetch_ready_rows(conn: psycopg.Connection) -> list[dict[str, Any]]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                id,
                snapshot_id,
                created_at,
                symbol,
                asset_class,
                timeframe,
                role,
                close,
                status
            FROM analytics_multi_asset_breakout_row_v1
            WHERE status LIKE '%BREAKOUT_READY%'
            ORDER BY created_at
            """
        )
        return list(cur.fetchall())


def find_future_row(
    conn: psycopg.Connection,
    ready: dict[str, Any],
    horizon_min: int,
) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT
                id,
                created_at,
                close,
                status
            FROM analytics_multi_asset_breakout_row_v1
            WHERE symbol = %(symbol)s
              AND timeframe = %(timeframe)s
              AND created_at >= %(ready_created_at)s + (%(horizon_min)s || ' minutes')::interval
              AND close IS NOT NULL
            ORDER BY created_at
            LIMIT 1
            """,
            {
                "symbol": ready["symbol"],
                "timeframe": ready["timeframe"],
                "ready_created_at": ready["created_at"],
                "horizon_min": horizon_min,
            },
        )
        return cur.fetchone()


def save_follow_through(
    conn: psycopg.Connection,
    ready: dict[str, Any],
    horizon_min: int,
    future: dict[str, Any] | None,
) -> None:
    ready_close = ready["close"]
    future_close = future["close"] if future else None
    ret = pct_change(ready_close, future_close)

    if future is None:
        status = "WAITING_FUTURE_ROW"
        direction_ok = None
    elif ret is None:
        status = "NO_RETURN"
        direction_ok = None
    elif ret > 0:
        status = "FOLLOW_THROUGH_UP"
        direction_ok = True
    elif ret < 0:
        status = "FAILED_OR_REVERSED"
        direction_ok = False
    else:
        status = "FLAT"

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO analytics_multi_asset_breakout_follow_through_v1 (
                ready_row_id,
                ready_snapshot_id,
                symbol,
                asset_class,
                timeframe,
                role,
                ready_created_at,
                ready_close,
                horizon_min,
                future_row_id,
                future_created_at,
                future_close,
                return_pct,
                direction_ok,
                status
            )
            VALUES (
                %(ready_row_id)s,
                %(ready_snapshot_id)s,
                %(symbol)s,
                %(asset_class)s,
                %(timeframe)s,
                %(role)s,
                %(ready_created_at)s,
                %(ready_close)s,
                %(horizon_min)s,
                %(future_row_id)s,
                %(future_created_at)s,
                %(future_close)s,
                %(return_pct)s,
                %(direction_ok)s,
                %(status)s
            )
            ON CONFLICT (ready_row_id, horizon_min)
            DO UPDATE SET
                future_row_id = EXCLUDED.future_row_id,
                future_created_at = EXCLUDED.future_created_at,
                future_close = EXCLUDED.future_close,
                return_pct = EXCLUDED.return_pct,
                direction_ok = EXCLUDED.direction_ok,
                status = EXCLUDED.status,
                created_at = now()
            """,
            {
                "ready_row_id": ready["id"],
                "ready_snapshot_id": ready["snapshot_id"],
                "symbol": ready["symbol"],
                "asset_class": ready["asset_class"],
                "timeframe": ready["timeframe"],
                "role": ready["role"],
                "ready_created_at": ready["created_at"],
                "ready_close": ready_close,
                "horizon_min": horizon_min,
                "future_row_id": future["id"] if future else None,
                "future_created_at": future["created_at"] if future else None,
                "future_close": future_close,
                "return_pct": ret,
                "direction_ok": direction_ok,
                "status": status,
            },
        )


def main() -> int:
    print("=== MULTI ASSET BREAKOUT FOLLOW THROUGH SCORECARD V1 ===")
    print("mode=read_only_scorecard")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=1")
    print("real_execution=0")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(database_url) as conn:
        ensure_schema(conn)
        ready_rows = fetch_ready_rows(conn)

        generated = 0
        waiting = 0

        for ready in ready_rows:
            for horizon in HORIZONS_MIN:
                future = find_future_row(conn, ready, horizon)
                save_follow_through(conn, ready, horizon, future)
                generated += 1
                if future is None:
                    waiting += 1

        conn.commit()

        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT count(*)::int AS total
                FROM analytics_multi_asset_breakout_follow_through_v1
                """
            )
            total_rows = int(cur.fetchone()["total"] or 0)

            cur.execute(
                """
                SELECT
                    horizon_min,
                    count(*)::int AS rows,
                    sum(CASE WHEN direction_ok IS TRUE THEN 1 ELSE 0 END)::int AS wins,
                    sum(CASE WHEN direction_ok IS FALSE THEN 1 ELSE 0 END)::int AS losses,
                    avg(return_pct) AS avg_return_pct
                FROM analytics_multi_asset_breakout_follow_through_v1
                GROUP BY horizon_min
                ORDER BY horizon_min
                """
            )
            score_rows = list(cur.fetchall())

    print()
    print("MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_ROWS")
    if not ready_rows:
        print("MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_ROW status=NO_READY_SIGNALS_YET")

    for row in score_rows:
        print(
            "MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_ROW "
            f"horizon_min={row['horizon_min']} rows={row['rows']} "
            f"wins={row['wins']} losses={row['losses']} "
            f"avg_return_pct={row['avg_return_pct']}"
        )

    print()
    print("MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_SCORECARD_SUMMARY")
    print(f"ready_rows={len(ready_rows)}")
    print(f"horizons={','.join(str(x) for x in HORIZONS_MIN)}")
    print(f"generated_rows={generated}")
    print(f"waiting_rows={waiting}")
    print(f"scorecard_rows_total={total_rows}")
    print("db_update=1")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if not ready_rows:
        print("VERDICT=MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_NO_READY_SIGNALS_YET")
    elif generated > 0:
        print("VERDICT=MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_SCORECARD_UPDATED")
    else:
        print("VERDICT=MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_REVIEW_REQUIRED")

    print("MULTI_ASSET_BREAKOUT_FOLLOW_THROUGH_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
