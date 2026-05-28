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
joined AS (
    SELECT
        r.symbol,
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
            WHEN p.symbol IS NULL THEN 'MISSING_IN_RUNTIME'
            WHEN COALESCE(r.real_qty, 0) <> COALESCE(p.runtime_qty, 0) THEN 'RUNTIME_QTY_MISMATCH'
            WHEN abs(COALESCE(r.real_avg_price, 0) - COALESCE(p.runtime_avg_price, 0)) > 0.000001 THEN 'RUNTIME_AVG_MISMATCH'
            ELSE 'VISIBLE_IN_RUNTIME'
        END AS bridge_status,
        CASE
            WHEN p.symbol IS NULL THEN abs(COALESCE(r.real_market_value, 0))
            WHEN COALESCE(r.real_qty, 0) <> COALESCE(p.runtime_qty, 0) THEN abs(COALESCE(r.real_market_value, 0))
            ELSE 0
        END AS unaccounted_market_value,
        CASE
            WHEN r.symbol LIKE 'BR%' OR r.symbol LIKE 'NG%' OR r.symbol LIKE 'Si%' THEN 'FUTURES'
            ELSE 'EQUITY_OR_BOND'
        END AS asset_class
    FROM real_pos r
    LEFT JOIN runtime_pos p
      ON p.symbol = r.symbol
)
SELECT *
FROM joined
ORDER BY
    CASE bridge_status
        WHEN 'MISSING_IN_RUNTIME' THEN 1
        WHEN 'RUNTIME_QTY_MISMATCH' THEN 2
        WHEN 'RUNTIME_AVG_MISMATCH' THEN 3
        ELSE 4
    END,
    abs(unaccounted_market_value) DESC,
    symbol
"""


SUMMARY_SQL = """
WITH real_pos AS (
    SELECT
        symbol,
        qty::double precision AS real_qty,
        market_value::double precision AS real_market_value,
        pnl::double precision AS real_pnl
    FROM real_portfolio_positions
    WHERE qty <> 0
),
runtime_pos AS (
    SELECT
        symbol,
        qty::double precision AS runtime_qty
    FROM positions
    WHERE qty <> 0
),
joined AS (
    SELECT
        r.symbol,
        r.real_qty,
        p.runtime_qty,
        r.real_market_value,
        r.real_pnl,
        CASE
            WHEN p.symbol IS NULL THEN 'MISSING_IN_RUNTIME'
            WHEN COALESCE(r.real_qty, 0) <> COALESCE(p.runtime_qty, 0) THEN 'RUNTIME_QTY_MISMATCH'
            ELSE 'VISIBLE_IN_RUNTIME'
        END AS bridge_status,
        CASE
            WHEN r.symbol LIKE 'BR%' OR r.symbol LIKE 'NG%' OR r.symbol LIKE 'Si%' THEN 'FUTURES'
            ELSE 'EQUITY_OR_BOND'
        END AS asset_class
    FROM real_pos r
    LEFT JOIN runtime_pos p
      ON p.symbol = r.symbol
)
SELECT
    count(*) AS real_positions,
    count(*) FILTER (WHERE bridge_status = 'MISSING_IN_RUNTIME') AS missing_in_runtime,
    count(*) FILTER (WHERE bridge_status = 'RUNTIME_QTY_MISMATCH') AS qty_mismatch,
    count(*) FILTER (WHERE bridge_status = 'VISIBLE_IN_RUNTIME') AS visible_in_runtime,
    round(sum(abs(real_market_value))::numeric, 2) AS total_market_value_abs,
    round(sum(abs(real_market_value)) FILTER (WHERE bridge_status <> 'VISIBLE_IN_RUNTIME')::numeric, 2) AS unaccounted_market_value_abs,
    round(sum(real_pnl)::numeric, 2) AS total_real_pnl,
    count(*) FILTER (WHERE asset_class = 'FUTURES') AS futures_positions
FROM joined
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SUMMARY_SQL)
            summary = dict(cur.fetchone())

            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    print("REAL_POSITION_RUNTIME_BRIDGE_AUDIT_V1", flush=True)

    print(
        "REAL_POSITION_RUNTIME_BRIDGE_SUMMARY",
        f"real_positions={summary['real_positions']}",
        f"missing_in_runtime={summary['missing_in_runtime']}",
        f"qty_mismatch={summary['qty_mismatch']}",
        f"visible_in_runtime={summary['visible_in_runtime']}",
        f"total_market_value_abs={summary['total_market_value_abs']}",
        f"unaccounted_market_value_abs={summary['unaccounted_market_value_abs']}",
        f"total_real_pnl={summary['total_real_pnl']}",
        f"futures_positions={summary['futures_positions']}",
        flush=True,
    )

    for r in rows:
        print(
            "REAL_POSITION_RUNTIME_BRIDGE_ROW",
            f"symbol={r['symbol']}",
            f"asset_class={r['asset_class']}",
            f"status={r['bridge_status']}",
            f"real_qty={r['real_qty']}",
            f"runtime_qty={r['runtime_qty']}",
            f"real_avg={r['real_avg_price']}",
            f"runtime_avg={r['runtime_avg_price']}",
            f"current={r['real_current_price']}",
            f"market_value={r['real_market_value']}",
            f"unaccounted_market_value={r['unaccounted_market_value']}",
            f"real_pnl={r['real_pnl']}",
            f"real_updated_at={r['real_updated_at']}",
            f"runtime_updated_at={r['runtime_updated_at']}",
            flush=True,
        )

    print(f"REAL_POSITION_RUNTIME_BRIDGE_AUDIT_V1_OK rows={len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
