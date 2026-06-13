#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"

SQL_GATE = """
SELECT decision, reason
FROM gold_runtime_review_gate
WHERE symbol=%s
ORDER BY id DESC
LIMIT 1;
"""

SQL_UPDATE = """
UPDATE runtime_candidate_registry
SET
    status='READY_FOR_RUNTIME_REVIEW',
    reason='gold_ready_for_runtime_review_after_gate',
    runtime_allowed=false,
    execution_enabled=false,
    raw_json = COALESCE(raw_json, '{}'::jsonb) || %s::jsonb,
    updated_at=now()
WHERE symbol=%s
  AND status='WATCH_RUNTIME_ACTIVE'
RETURNING symbol, status, reason, runtime_allowed, execution_enabled, raw_json, updated_at;
"""

def main() -> int:
    print("=== GOLD RUNTIME CANDIDATE PROMOTION V1 ===")
    print("mode=candidate_promotion")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_GATE, (SYMBOL,))
            gate = cur.fetchone()

            if not gate:
                print("PROMOTION_ERROR reason=review_gate_missing")
                return 1

            if gate["decision"] != "READY_FOR_RUNTIME_REVIEW":
                print(
                    "PROMOTION_ERROR "
                    f"reason=gate_not_ready "
                    f"decision={gate['decision']}"
                )
                return 1

            payload = {
                "promotion": {
                    "source": "gold_runtime_candidate_promotion_v1",
                    "from_status": "WATCH_RUNTIME_ACTIVE",
                    "to_status": "READY_FOR_RUNTIME_REVIEW",
                    "gate_decision": gate["decision"],
                    "gate_reason": gate["reason"],
                    "runtime_allowed": False,
                    "execution_enabled": False,
                }
            }

            cur.execute(
                SQL_UPDATE,
                (json.dumps(payload, ensure_ascii=False), SYMBOL),
            )
            row = cur.fetchone()

            if not row:
                print("PROMOTION_ERROR reason=watch_runtime_active_row_missing")
                return 1

        conn.commit()

    print(
        "PROMOTION_ROW "
        f"symbol={row['symbol']} "
        f"status={row['status']} "
        f"reason={row['reason']} "
        f"runtime_allowed={int(row['runtime_allowed'])} "
        f"execution_enabled={int(row['execution_enabled'])} "
        f"updated_at={row['updated_at']}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=GOLD_READY_FOR_RUNTIME_REVIEW_REGISTERED")
    print("GOLD_RUNTIME_CANDIDATE_PROMOTION_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
