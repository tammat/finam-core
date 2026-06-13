#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

SYMBOL = "USDRUBF@RTSX"

SQL_UPSERT = """
INSERT INTO runtime_candidate_registry (
    symbol,
    status,
    reason,
    runtime_allowed,
    execution_enabled,
    raw_json,
    updated_at
)
VALUES (
    %(symbol)s,
    'REJECTED',
    'loss_tail_filter_unstable',
    false,
    false,
    %(raw_json)s,
    now()
)
ON CONFLICT (symbol) DO UPDATE
SET
    status='REJECTED',
    reason='loss_tail_filter_unstable',
    runtime_allowed=false,
    execution_enabled=false,
    raw_json = COALESCE(runtime_candidate_registry.raw_json, '{}'::jsonb) || EXCLUDED.raw_json,
    updated_at=now()
RETURNING symbol, status, reason, runtime_allowed, execution_enabled, updated_at;
"""

def main() -> int:
    print("=== USDRUB SHADOW REJECT REGISTRY V1 ===")
    print("mode=registry_reject")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print()

    payload = {
        "source": "usdrub_shadow_reject_registry_v1",
        "reject_reason": "loss_tail_filter_unstable",
        "scorecard_verdict": "USDRUB_SHADOW_SCORECARD_REJECT",
        "stability_verdict": "USDRUB_LOSS_TAIL_UNSTABLE",
        "runtime_allowed": False,
        "execution_enabled": False,
    }

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                SQL_UPSERT,
                {
                    "symbol": SYMBOL,
                    "raw_json": json.dumps(payload, ensure_ascii=False),
                },
            )
            row = cur.fetchone()
        conn.commit()

    print(
        "REGISTRY_ROW "
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
    print("VERDICT=USDRUB_REJECTED")
    print("USDRUB_SHADOW_REJECT_REGISTRY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
