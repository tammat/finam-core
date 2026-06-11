#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

TARGET_SIGNALS = 50

SQL = """
SELECT
    COUNT(*) AS signals,
    MIN(signal_ts) AS first_ts,
    MAX(signal_ts) AS last_ts
FROM runtime_shadow_gold_signals
WHERE symbol='GDU6@RTSX'
  AND strategy='gold_short_only_shadow_v1';
"""

def main():
    print("=== RUNTIME SHADOW VALIDATION GOLD SCHEDULER V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(SQL)
            row = cur.fetchone()

    signals = int(row["signals"] or 0)
    remaining = max(0, TARGET_SIGNALS - signals)

    status = (
        "READY_FOR_SCORECARD"
        if signals >= TARGET_SIGNALS
        else "ACCUMULATING"
    )

    print()
    print("SCHEDULER_ROW")
    print(f"current_signals={signals}")
    print(f"target_signals={TARGET_SIGNALS}")
    print(f"remaining_signals={remaining}")
    print(f"first_ts={row['first_ts']}")
    print(f"last_ts={row['last_ts']}")
    print(f"status={status}")
    print("promotion_ready=0")
    print("runtime_allow=0")
    print("execution_enabled=0")

    print()
    print("VERDICT=RUNTIME_SHADOW_VALIDATION_GOLD_SCHEDULER_RECORDED")
    print("RUNTIME_SHADOW_VALIDATION_GOLD_SCHEDULER_V1_OK")

if __name__ == "__main__":
    main()
