#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS shadow_runtime_admission_board (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    source text,
    review_verdict text,
    decision_status text,
    admission_decision text NOT NULL,
    admission_reason text NOT NULL,
    shadow_runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);
"""

SQL = """
SELECT DISTINCT ON (symbol)
    symbol,
    source,
    review_verdict,
    decision_status
FROM runtime_review_package
ORDER BY symbol, id DESC;
"""

def main() -> int:
    print("=== SHADOW RUNTIME ADMISSION BOARD V1 ===")
    print("mode=admission_board")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    admitted = 0
    rejected = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

            cur.execute(DDL)
            cur.execute(SQL)

            rows = cur.fetchall()

            print("ADMISSION_ROWS")

            for row in rows:

                if (
                    row["review_verdict"] == "READY_FOR_SHADOW_RUNTIME"
                    and row["decision_status"] == "PROMOTE_RUNTIME_REVIEW"
                ):
                    decision = "ADMIT_SHADOW_RUNTIME"
                    reason = "review_and_decision_passed"
                    admitted += 1
                else:
                    decision = "REJECT"
                    reason = "candidate_not_ready"
                    rejected += 1

                payload = {
                    "symbol": row["symbol"],
                    "decision": decision,
                    "reason": reason,
                }

                cur.execute(
                    """
                    INSERT INTO shadow_runtime_admission_board (
                        symbol,
                        source,
                        review_verdict,
                        decision_status,
                        admission_decision,
                        admission_reason,
                        shadow_runtime_allowed,
                        execution_enabled,
                        raw_json
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,
                        false,
                        false,
                        %s::jsonb
                    )
                    """,
                    (
                        row["symbol"],
                        row["source"],
                        row["review_verdict"],
                        row["decision_status"],
                        decision,
                        reason,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )

                print(
                    f"ADMISSION_ROW symbol={row['symbol']} "
                    f"admission={decision} "
                    f"reason={reason} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"SUMMARY_ROW admitted={admitted} rejected={rejected}")
    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=SHADOW_RUNTIME_ADMISSION_BOARD_READY")
    print("SHADOW_RUNTIME_ADMISSION_BOARD_V1_OK")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
