#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

DDL = """
CREATE TABLE IF NOT EXISTS futures_contract_calendar (
    symbol text PRIMARY KEY,
    root_symbol text NOT NULL,
    contract_role text NOT NULL DEFAULT 'UNKNOWN',
    last_trade_date date NOT NULL,
    expiration_date date,
    source text NOT NULL DEFAULT 'manual',
    updated_at timestamptz NOT NULL DEFAULT now()
);
"""

SQL = """
SELECT
    root_symbol,
    symbol,
    contract_role,
    last_trade_date,
    expiration_date,
    (last_trade_date - CURRENT_DATE) AS days_to_last_trade,
    CASE
        WHEN (last_trade_date - CURRENT_DATE) <= 3 THEN 'EXPIRING'
        WHEN (last_trade_date - CURRENT_DATE) <= 7 THEN 'ROLLOVER_WATCH'
        ELSE 'NORMAL'
    END AS rollover_state,
    source,
    updated_at
FROM futures_contract_calendar
WHERE root_symbol IN ('BR','NG')
ORDER BY root_symbol, last_trade_date;
"""

def main() -> None:
    print("=== ROLLOVER STATUS REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            conn.commit()

            cur.execute(SQL)
            rows = cur.fetchall()

    print("ROLLOVER_ROWS")
    if not rows:
        print("NONE")

    for r in rows:
        print(
            "ROLLOVER_ROW "
            f"root={r['root_symbol']} "
            f"symbol={r['symbol']} "
            f"role={r['contract_role']} "
            f"last_trade_date={r['last_trade_date']} "
            f"expiration_date={r['expiration_date']} "
            f"days_to_last_trade={r['days_to_last_trade']} "
            f"state={r['rollover_state']} "
            f"source={r['source']}"
        )

    print()
    print(f"ROWS={len(rows)}")
    print("VERDICT=ROLLOVER_STATUS_RECORDED")
    print("ROLLOVER_STATUS_REPORT_V1_OK")

if __name__ == "__main__":
    main()
