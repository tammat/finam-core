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
)
SELECT
    r.symbol,
    r.real_qty,
    p.runtime_qty,
    r.real_avg_price,
    p.runtime_avg_price,
    r.real_current_price,
    r.real_market_value,
    r.real_pnl,
    r.real_updated_at,
    p.runtime_updated_at,
    CASE
        WHEN p.symbol IS NULL THEN 'ADVISORY_CREATE_RUNTIME_POSITION'
        WHEN COALESCE(r.real_qty, 0) <> COALESCE(p.runtime_qty, 0) THEN 'ADVISORY_SYNC_RUNTIME_QTY'
        WHEN abs(COALESCE(r.real_avg_price, 0) - COALESCE(p.runtime_avg_price, 0)) > 0.000001 THEN 'ADVISORY_SYNC_RUNTIME_AVG'
        ELSE 'ADVISORY_OK'
    END AS advisory_action,
    CASE
        WHEN r.symbol LIKE '%@RTSX' THEN 'FUTURES'
        ELSE 'EQUITY_OR_BOND'
    END AS asset_class
FROM real_pos r
LEFT JOIN runtime_pos p
    ON r.symbol = p.symbol
ORDER BY abs(COALESCE(r.real_market_value, 0)) DESC;
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    create_count = sum(1 for r in rows if r["advisory_action"] == "ADVISORY_CREATE_RUNTIME_POSITION")
    sync_qty_count = sum(1 for r in rows if r["advisory_action"] == "ADVISORY_SYNC_RUNTIME_QTY")
    sync_avg_count = sum(1 for r in rows if r["advisory_action"] == "ADVISORY_SYNC_RUNTIME_AVG")
    ok_count = sum(1 for r in rows if r["advisory_action"] == "ADVISORY_OK")
    total_market_value = sum(abs(float(r["real_market_value"] or 0.0)) for r in rows)

    print("REAL_POSITION_RUNTIME_BRIDGE_ADVISORY_V1", flush=True)
    print(
        "REAL_POSITION_RUNTIME_BRIDGE_ADVISORY_SUMMARY",
        f"rows={len(rows)}",
        f"create_runtime={create_count}",
        f"sync_qty={sync_qty_count}",
        f"sync_avg={sync_avg_count}",
        f"ok={ok_count}",
        f"total_market_value_abs={total_market_value:.2f}",
        flush=True,
    )

    for r in rows:
        print(
            "REAL_POSITION_RUNTIME_BRIDGE_ADVISORY_ROW",
            f"symbol={r['symbol']}",
            f"asset_class={r['asset_class']}",
            f"action={r['advisory_action']}",
            f"real_qty={r['real_qty']}",
            f"runtime_qty={r['runtime_qty']}",
            f"real_avg={r['real_avg_price']}",
            f"runtime_avg={r['runtime_avg_price']}",
            f"current={r['real_current_price']}",
            f"market_value={r['real_market_value']}",
            f"real_pnl={r['real_pnl']}",
            f"real_updated_at={r['real_updated_at']}",
            f"runtime_updated_at={r['runtime_updated_at']}",
            flush=True,
        )

    print(f"REAL_POSITION_RUNTIME_BRIDGE_ADVISORY_V1_OK rows={len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
