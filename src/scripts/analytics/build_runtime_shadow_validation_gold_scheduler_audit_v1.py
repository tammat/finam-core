#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import psycopg2
import psycopg2.extras

SCHEDULER_PATH = Path(
    "src/scripts/analytics/build_runtime_shadow_validation_gold_scheduler_v1.py"
)

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

FORBIDDEN_TOKENS = [
    "INSERT INTO",
    "UPDATE ",
    "DELETE FROM",
    "TRUNCATE ",
    "CREATE TABLE",
    "DROP TABLE",
    "ALTER TABLE",
]

def main() -> None:
    print("=== RUNTIME SHADOW VALIDATION GOLD SCHEDULER AUDIT V1 ===")
    print("mode=scheduler_audit")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    source = SCHEDULER_PATH.read_text()

    forbidden_hits = [
        token for token in FORBIDDEN_TOKENS
        if token.lower() in source.lower()
    ]

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(SQL)
            row = cur.fetchone()

    signals = int(row["signals"] or 0)
    remaining = max(0, TARGET_SIGNALS - signals)
    status = "READY_FOR_SCORECARD" if signals >= TARGET_SIGNALS else "ACCUMULATING"

    print(
        "AUDIT_ROW "
        f"scheduler_file_exists={int(SCHEDULER_PATH.exists())} "
        f"forbidden_write_tokens={len(forbidden_hits)} "
        f"tokens={','.join(forbidden_hits) if forbidden_hits else 'none'}"
    )

    print(
        "AUDIT_ROW "
        f"current_signals={signals} "
        f"target_signals={TARGET_SIGNALS} "
        f"remaining_signals={remaining} "
        f"status={status} "
        f"promotion_ready={int(status == 'READY_FOR_SCORECARD')} "
        f"runtime_allow=0 "
        f"execution_enabled=0 "
        f"first_ts={row['first_ts']} "
        f"last_ts={row['last_ts']}"
    )

    verdict = "PASS" if (
        SCHEDULER_PATH.exists()
        and not forbidden_hits
        and signals >= 0
        and remaining >= 0
    ) else "FAIL"

    print()
    print(f"AUDIT_VERDICT={verdict}")

    if verdict != "PASS":
        raise SystemExit(1)

    print("RUNTIME_SHADOW_VALIDATION_GOLD_SCHEDULER_AUDIT_V1_OK")

if __name__ == "__main__":
    main()
