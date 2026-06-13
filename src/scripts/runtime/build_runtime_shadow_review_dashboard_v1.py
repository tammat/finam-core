#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    candidate_status,
    decision_status,
    closed_trades,
    expectancy,
    profit_factor,
    review_verdict,
    runtime_allowed,
    execution_enabled
FROM runtime_review_package
ORDER BY symbol, id DESC;
"""

def main() -> int:
    print("=== RUNTIME SHADOW REVIEW DASHBOARD V1 ===")
    print("mode=readonly_dashboard")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    ready = 0
    rejected = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    print("DASHBOARD_ROWS")
    for row in sorted(rows, key=lambda r: (r["review_verdict"] != "READY_FOR_SHADOW_RUNTIME", r["symbol"])):
        if row["review_verdict"] == "READY_FOR_SHADOW_RUNTIME":
            ready += 1
        elif row["review_verdict"] == "REJECTED":
            rejected += 1

        print(
            "DASHBOARD_ROW "
            f"symbol={row['symbol']} "
            f"source={row['source']} "
            f"candidate_status={row['candidate_status']} "
            f"decision_status={row['decision_status']} "
            f"closed_trades={row['closed_trades']} "
            f"expectancy={row['expectancy']} "
            f"profit_factor={row['profit_factor']} "
            f"review_verdict={row['review_verdict']} "
            f"runtime_allowed={int(row['runtime_allowed'])} "
            f"execution_enabled={int(row['execution_enabled'])}"
        )

    print()
    print(f"SUMMARY_ROW ready_for_shadow_runtime={ready} rejected={rejected} total={len(rows)}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=RUNTIME_SHADOW_REVIEW_DASHBOARD_READY")
    print("RUNTIME_SHADOW_REVIEW_DASHBOARD_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
