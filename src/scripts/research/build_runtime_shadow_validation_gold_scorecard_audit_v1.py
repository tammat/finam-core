#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOL = os.getenv("GOLD_SYMBOL", "GDU6@RTSX")
STRATEGY = "gold_short_only_shadow_v1"

SQL = """
WITH base AS (
    SELECT *
    FROM runtime_shadow_gold_signals
    WHERE symbol=%s
      AND strategy=%s
),
dups AS (
    SELECT symbol, timeframe, signal_ts, strategy, COUNT(*) AS cnt
    FROM runtime_shadow_gold_signals
    WHERE symbol=%s
      AND strategy=%s
    GROUP BY symbol, timeframe, signal_ts, strategy
    HAVING COUNT(*) > 1
),
other_gold AS (
    SELECT symbol, COUNT(*) AS rows
    FROM runtime_shadow_gold_signals
    WHERE strategy=%s
      AND symbol <> %s
    GROUP BY symbol
)
SELECT
    (SELECT COUNT(*) FROM base) AS target_rows,
    (SELECT COUNT(*) FROM base WHERE shadow_only IS TRUE) AS shadow_only_rows,
    (SELECT COUNT(*) FROM base WHERE shadow_only IS DISTINCT FROM TRUE) AS unsafe_shadow_rows,
    (SELECT COUNT(*) FROM dups) AS duplicate_keys,
    (SELECT COUNT(*) FROM other_gold) AS other_gold_symbols,
    (SELECT MIN(signal_ts) FROM base) AS first_signal_ts,
    (SELECT MAX(signal_ts) FROM base) AS last_signal_ts;
"""

OTHER_SQL = """
SELECT symbol, COUNT(*) AS rows
FROM runtime_shadow_gold_signals
WHERE strategy=%s
  AND symbol <> %s
GROUP BY symbol
ORDER BY symbol;
"""

def main() -> None:
    print("=== RUNTIME SHADOW VALIDATION GOLD SCORECARD AUDIT V1 ===")
    print("mode=research_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOL, STRATEGY, SYMBOL, STRATEGY, STRATEGY, SYMBOL))
            row = cur.fetchone()

            cur.execute(OTHER_SQL, (STRATEGY, SYMBOL))
            others = cur.fetchall()

    target_rows = int(row["target_rows"] or 0)
    unsafe_shadow_rows = int(row["unsafe_shadow_rows"] or 0)
    duplicate_keys = int(row["duplicate_keys"] or 0)

    print(
        "AUDIT_ROW "
        f"target_rows={target_rows} "
        f"shadow_only_rows={row['shadow_only_rows']} "
        f"unsafe_shadow_rows={unsafe_shadow_rows} "
        f"duplicate_keys={duplicate_keys} "
        f"other_gold_symbols={row['other_gold_symbols']} "
        f"first_signal_ts={row['first_signal_ts']} "
        f"last_signal_ts={row['last_signal_ts']}"
    )

    print("OTHER_GOLD_ROWS")
    for r in others:
        print(f"OTHER_GOLD_ROW symbol={r['symbol']} rows={r['rows']}")

    verdict = "PASS" if (
        target_rows >= 50
        and unsafe_shadow_rows == 0
        and duplicate_keys == 0
    ) else "FAIL"

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"AUDIT_VERDICT={verdict}")

    if verdict != "PASS":
        raise SystemExit(1)

    print("RUNTIME_SHADOW_VALIDATION_GOLD_SCORECARD_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
