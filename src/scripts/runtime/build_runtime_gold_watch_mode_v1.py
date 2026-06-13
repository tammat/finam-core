#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"

SQL_SELECT = """
SELECT symbol, status, reason, runtime_allowed, execution_enabled
FROM runtime_candidate_registry
WHERE symbol=%s;
"""

SQL_UPDATE = """
UPDATE runtime_candidate_registry
SET
    status='WATCH_RUNTIME_ACTIVE',
    reason='gold_runtime_watch_mode_active',
    runtime_allowed=false,
    execution_enabled=false,
    raw_json = COALESCE(raw_json, '{}'::jsonb) || %s::jsonb,
    updated_at=now()
WHERE symbol=%s
  AND status IN ('WATCH_RUNTIME', 'WATCH_RUNTIME_ACTIVE')
RETURNING symbol, status, reason, runtime_allowed, execution_enabled, updated_at;
"""

def main() -> int:
    print("=== RUNTIME GOLD WATCH MODE V1 ===")
    print("mode=watch_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print()

    payload = {
        "watch_mode": "WATCH_RUNTIME_ACTIVE",
        "runtime_allowed": False,
        "execution_enabled": False,
        "source": "runtime_gold_watch_mode_v1",
    }

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_SELECT, (SYMBOL,))
            before = cur.fetchone()

            if not before:
                print("WATCH_MODE_ERROR reason=registry_row_missing")
                return 1

            cur.execute(SQL_UPDATE, (json.dumps(payload, ensure_ascii=False), SYMBOL))
            after = cur.fetchone()

            if not after:
                print(
                    "WATCH_MODE_ERROR "
                    f"symbol={SYMBOL} "
                    f"reason=invalid_previous_status "
                    f"previous_status={before['status']}"
                )
                return 1

        conn.commit()

    print(
        "WATCH_MODE_ROW "
        f"symbol={after['symbol']} "
        f"status={after['status']} "
        f"reason={after['reason']} "
        f"runtime_allowed={int(after['runtime_allowed'])} "
        f"execution_enabled={int(after['execution_enabled'])} "
        f"updated_at={after['updated_at']}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=GOLD_WATCH_RUNTIME_ACTIVE")
    print("RUNTIME_GOLD_WATCH_MODE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
