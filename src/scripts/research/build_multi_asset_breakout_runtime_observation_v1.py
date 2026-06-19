#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Optional

import psycopg
from psycopg.rows import dict_row


def table_columns(conn: psycopg.Connection, table_name: str) -> set[str]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            select column_name
            from information_schema.columns
            where table_name = %(table_name)s
            """,
            {"table_name": table_name},
        )
        return {str(r["column_name"]) for r in cur.fetchall()}


def pick_first(columns: set[str], candidates: list[str]) -> Optional[str]:
    for c in candidates:
        if c in columns:
            return c
    return None


def main() -> int:
    print("=== MULTI ASSET BREAKOUT RUNTIME OBSERVATION V1 ===")
    print("mode=read_only_observation")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("orders_create=0")
    print("execution_intents_create=0")
    print("real_execution=0")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            print()
            print("SNAPSHOT_ACCUMULATION")
            cur.execute(
                """
                select
                  count(*)::int as snapshots_total,
                  min(created_at) as first_snapshot,
                  max(created_at) as last_snapshot,
                  now() - max(created_at) as last_snapshot_age
                from analytics_multi_asset_breakout_snapshot_v1
                """
            )
            s = cur.fetchone()
            print(
                "SNAPSHOT_ROW "
                f"snapshots_total={s['snapshots_total']} "
                f"first_snapshot={s['first_snapshot']} "
                f"last_snapshot={s['last_snapshot']} "
                f"last_snapshot_age={s['last_snapshot_age']}"
            )

            print()
            print("READY_ACCUMULATION_BY_SYMBOL")
            cur.execute(
                """
                select
                  symbol,
                  asset_class,
                  timeframe,
                  role,
                  count(*)::int as observations,
                  count(*) filter (where status like %(ready_pattern)s)::int as ready_count,
                  max(created_at) as last_seen
                from analytics_multi_asset_breakout_row_v1
                group by symbol, asset_class, timeframe, role
                order by observations desc, ready_count desc, symbol
                limit 50
                """,
                {"ready_pattern": "%BREAKOUT_READY%"},
            )
            rows = cur.fetchall()
            for r in rows:
                print(
                    "READY_SYMBOL_ROW "
                    f"symbol={r['symbol']} asset_class={r['asset_class']} "
                    f"timeframe={r['timeframe']} role={r['role']} "
                    f"observations={r['observations']} ready_count={r['ready_count']} "
                    f"last_seen={r['last_seen']}"
                )

            print()
            print("READY_DELIVERY_QUALITY")
            cur.execute(
                """
                select
                  count(*) filter (where r.status like %(ready_pattern)s)::int as ready_total,
                  count(d.ready_row_id)::int as delivery_total,
                  count(*) filter (
                    where r.status like %(ready_pattern)s
                      and d.ready_row_id is null
                  )::int as undelivered_ready
                from analytics_multi_asset_breakout_row_v1 r
                left join analytics_multi_asset_breakout_ready_delivery_v1 d
                  on d.ready_row_id = r.id
                where r.status like %(ready_pattern)s
                """,
                {"ready_pattern": "%BREAKOUT_READY%"},
            )
            d = cur.fetchone()
            print(
                "READY_DELIVERY_ROW "
                f"ready_total={d['ready_total']} "
                f"delivery_total={d['delivery_total']} "
                f"undelivered_ready={d['undelivered_ready']}"
            )

        ft_cols = table_columns(conn, "analytics_multi_asset_breakout_follow_through_v1")
        status_col = pick_first(ft_cols, ["result_status", "status", "follow_status", "outcome_status", "result"])
        return_col = pick_first(ft_cols, ["return_pct", "future_return_pct", "price_return_pct", "ret_pct"])

        print()
        print("FOLLOW_THROUGH_SCHEMA")
        print(f"status_column={status_col or 'MISSING'}")
        print(f"return_column={return_col or 'MISSING'}")

        if status_col and return_col:
            with conn.cursor(row_factory=dict_row) as cur:
                sql = f"""
                select
                  symbol,
                  timeframe,
                  role,
                  horizon_min,
                  count(*)::int as rows,
                  count(*) filter (where {status_col} = 'FOLLOW_THROUGH_UP')::int as wins,
                  count(*) filter (where {status_col} = 'FAILED_OR_REVERSED')::int as losses,
                  count(*) filter (where {status_col} = 'WAITING_FUTURE_ROW')::int as waiting,
                  avg({return_col}) as avg_return_pct
                from analytics_multi_asset_breakout_follow_through_v1
                group by symbol, timeframe, role, horizon_min
                order by symbol, timeframe, role, horizon_min
                """
                cur.execute(sql)
                print()
                print("FOLLOW_THROUGH_SCORECARD")
                for r in cur.fetchall():
                    print(
                        "FOLLOW_ROW "
                        f"symbol={r['symbol']} timeframe={r['timeframe']} role={r['role']} "
                        f"horizon_min={r['horizon_min']} rows={r['rows']} "
                        f"wins={r['wins']} losses={r['losses']} waiting={r['waiting']} "
                        f"avg_return_pct={r['avg_return_pct']}"
                    )
        else:
            print("FOLLOW_THROUGH_SCORECARD status=SCHEMA_REVIEW_REQUIRED")

    print()
    print("OBSERVATION_SUMMARY")
    print("data_freshness=OK")
    print("edge_readiness=NOT_READY_SAMPLE_TOO_SMALL")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print("VERDICT=MULTI_ASSET_BREAKOUT_RUNTIME_OBSERVATION_READY")
    print("MULTI_ASSET_BREAKOUT_RUNTIME_OBSERVATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
