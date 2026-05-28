from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
WITH broker AS (
    SELECT
        symbol,
        qty::double precision AS broker_qty,
        avg_price::double precision AS broker_avg_price,
        current_price::double precision AS broker_current_price,
        pnl::double precision AS broker_pnl,
        pnl_day::double precision AS broker_pnl_day,
        updated_at AS broker_updated_at
    FROM real_portfolio_positions
    WHERE qty <> 0
),
runtime AS (
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
        COALESCE(b.symbol, r.symbol) AS symbol,
        b.broker_qty,
        r.runtime_qty,
        b.broker_avg_price,
        r.runtime_avg_price,
        b.broker_current_price,
        b.broker_pnl,
        b.broker_pnl_day,
        b.broker_updated_at,
        r.runtime_updated_at,
        CASE
            WHEN b.symbol IS NOT NULL AND r.symbol IS NULL
                THEN 'BROKER_ONLY'
            WHEN b.symbol IS NULL AND r.symbol IS NOT NULL
                THEN 'RUNTIME_ONLY'
            WHEN COALESCE(b.broker_qty, 0) <> COALESCE(r.runtime_qty, 0)
                THEN 'QTY_MISMATCH'
            WHEN abs(COALESCE(b.broker_avg_price, 0) - COALESCE(r.runtime_avg_price, 0)) > 0.000001
                THEN 'AVG_PRICE_MISMATCH'
            ELSE 'MATCHED'
        END AS reconciliation_status
    FROM broker b
    FULL OUTER JOIN runtime r
      ON r.symbol = b.symbol
)
SELECT *
FROM joined
ORDER BY
    CASE reconciliation_status
        WHEN 'BROKER_ONLY' THEN 1
        WHEN 'RUNTIME_ONLY' THEN 2
        WHEN 'QTY_MISMATCH' THEN 3
        WHEN 'AVG_PRICE_MISMATCH' THEN 4
        ELSE 5
    END,
    symbol
"""


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    print("BROKER_POSITION_RECONCILIATION_AUDIT_V1", flush=True)

    for r in rows:
        print(
            "BROKER_POSITION_RECONCILIATION_ROW",
            f"symbol={r['symbol']}",
            f"status={r['reconciliation_status']}",
            f"broker_qty={r['broker_qty']}",
            f"runtime_qty={r['runtime_qty']}",
            f"broker_avg={r['broker_avg_price']}",
            f"runtime_avg={r['runtime_avg_price']}",
            f"broker_current={r['broker_current_price']}",
            f"broker_pnl={r['broker_pnl']}",
            f"broker_updated_at={r['broker_updated_at']}",
            f"runtime_updated_at={r['runtime_updated_at']}",
            flush=True,
        )

    print(f"BROKER_POSITION_RECONCILIATION_AUDIT_V1_OK rows={len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
