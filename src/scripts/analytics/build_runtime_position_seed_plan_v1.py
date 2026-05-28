from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
WITH real_pos AS (
    SELECT
        symbol,
        qty::double precision AS real_qty,
        avg_price::double precision AS real_avg_price,
        current_price::double precision AS real_current_price,
        market_value::double precision AS real_market_value,
        pnl::double precision AS real_pnl,
        pnl_day::double precision AS real_pnl_day,
        source,
        updated_at AS real_updated_at
    FROM real_portfolio_positions
    WHERE qty <> 0
),
runtime_pos AS (
    SELECT
        symbol,
        qty::double precision AS runtime_qty,
        avg_price::double precision AS runtime_avg_price,
        updated_ts AS runtime_updated_at
    FROM positions
    WHERE qty <> 0
),
plan_rows AS (
    SELECT
        r.symbol,
        CASE
            WHEN r.symbol LIKE '%@RTSX' THEN 'FUTURES'
            WHEN r.symbol LIKE 'SU%@MISX' THEN 'BOND'
            ELSE 'EQUITY'
        END AS asset_class,
        r.real_qty,
        p.runtime_qty,
        r.real_avg_price,
        p.runtime_avg_price,
        r.real_current_price,
        r.real_market_value,
        r.real_pnl,
        r.real_pnl_day,
        r.source,
        r.real_updated_at,
        p.runtime_updated_at,
        CASE
            WHEN p.symbol IS NULL THEN 'SEED_RUNTIME_POSITION'
            WHEN COALESCE(r.real_qty, 0) <> COALESCE(p.runtime_qty, 0) THEN 'UPDATE_RUNTIME_QTY'
            WHEN abs(COALESCE(r.real_avg_price, 0) - COALESCE(p.runtime_avg_price, 0)) > 0.000001 THEN 'UPDATE_RUNTIME_AVG'
            ELSE 'NO_ACTION'
        END AS seed_action,
        CASE
            WHEN p.symbol IS NULL THEN 'missing_runtime_position'
            WHEN COALESCE(r.real_qty, 0) <> COALESCE(p.runtime_qty, 0) THEN 'runtime_qty_differs_from_broker'
            WHEN abs(COALESCE(r.real_avg_price, 0) - COALESCE(p.runtime_avg_price, 0)) > 0.000001 THEN 'runtime_avg_differs_from_broker'
            ELSE 'runtime_already_aligned'
        END AS seed_reason,
        CASE
            WHEN r.symbol LIKE '%@RTSX' THEN true
            ELSE false
        END AS requires_protective_awareness
    FROM real_pos r
    LEFT JOIN runtime_pos p
      ON p.symbol = r.symbol
)
SELECT *
FROM plan_rows
ORDER BY
    CASE seed_action
        WHEN 'SEED_RUNTIME_POSITION' THEN 1
        WHEN 'UPDATE_RUNTIME_QTY' THEN 2
        WHEN 'UPDATE_RUNTIME_AVG' THEN 3
        ELSE 4
    END,
    CASE asset_class
        WHEN 'FUTURES' THEN 1
        WHEN 'EQUITY' THEN 2
        WHEN 'BOND' THEN 3
        ELSE 4
    END,
    abs(real_market_value) DESC,
    symbol
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    seed_count = sum(1 for r in rows if r["seed_action"] == "SEED_RUNTIME_POSITION")
    update_qty_count = sum(1 for r in rows if r["seed_action"] == "UPDATE_RUNTIME_QTY")
    update_avg_count = sum(1 for r in rows if r["seed_action"] == "UPDATE_RUNTIME_AVG")
    no_action_count = sum(1 for r in rows if r["seed_action"] == "NO_ACTION")
    futures_count = sum(1 for r in rows if r["asset_class"] == "FUTURES")
    protective_count = sum(1 for r in rows if r["requires_protective_awareness"])
    total_market_value = sum(abs(float(r["real_market_value"] or 0.0)) for r in rows)

    print("RUNTIME_POSITION_SEED_PLAN_V1", flush=True)
    print(
        "RUNTIME_POSITION_SEED_PLAN_SUMMARY",
        f"rows={len(rows)}",
        f"seed={seed_count}",
        f"update_qty={update_qty_count}",
        f"update_avg={update_avg_count}",
        f"no_action={no_action_count}",
        f"futures={futures_count}",
        f"requires_protection={protective_count}",
        f"total_market_value_abs={total_market_value:.2f}",
        f"mode=DRY_RUN",
        flush=True,
    )

    for r in rows:
        print(
            "RUNTIME_POSITION_SEED_PLAN_ROW",
            f"symbol={r['symbol']}",
            f"asset_class={r['asset_class']}",
            f"action={r['seed_action']}",
            f"reason={r['seed_reason']}",
            f"real_qty={r['real_qty']}",
            f"runtime_qty={r['runtime_qty']}",
            f"real_avg={r['real_avg_price']}",
            f"runtime_avg={r['runtime_avg_price']}",
            f"current={r['real_current_price']}",
            f"market_value={r['real_market_value']}",
            f"real_pnl={r['real_pnl']}",
            f"pnl_day={r['real_pnl_day']}",
            f"requires_protection={r['requires_protective_awareness']}",
            f"real_updated_at={r['real_updated_at']}",
            f"runtime_updated_at={r['runtime_updated_at']}",
            flush=True,
        )

    print(f"RUNTIME_POSITION_SEED_PLAN_V1_OK rows={len(rows)} mode=DRY_RUN", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
