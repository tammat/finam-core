#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

SYMBOL = "LKOH@MISX"
SOURCE = "lkoh_sell_only_scorecard_v1"

SQL_GATE = """
SELECT
    symbol,
    strategy,
    closed_trades,
    winrate,
    expectancy,
    profit_factor,
    decision,
    reason
FROM lkoh_sell_only_review_gate
WHERE symbol=%s
ORDER BY id DESC
LIMIT 1;
"""

SQL_UPSERT = """
INSERT INTO runtime_candidate_registry (
    symbol,
    status,
    reason,
    source,
    runtime_allowed,
    execution_enabled,
    raw_json,
    updated_at
)
VALUES (
    %(symbol)s,
    'READY_FOR_RUNTIME_REVIEW',
    'lkoh_sell_only_review_gate_passed',
    %(source)s,
    false,
    false,
    %(raw_json)s,
    now()
)
ON CONFLICT (symbol) DO UPDATE
SET
    status='READY_FOR_RUNTIME_REVIEW',
    reason='lkoh_sell_only_review_gate_passed',
    source=EXCLUDED.source,
    runtime_allowed=false,
    execution_enabled=false,
    raw_json = COALESCE(runtime_candidate_registry.raw_json, '{}'::jsonb) || EXCLUDED.raw_json,
    updated_at=now()
RETURNING
    symbol,
    status,
    reason,
    source,
    runtime_allowed,
    execution_enabled,
    updated_at;
"""

def main() -> int:
    print("=== LKOH SELL ONLY CANDIDATE REGISTRY V1 ===")
    print("mode=candidate_registry")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"source={SOURCE}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_GATE, (SYMBOL,))
            gate = cur.fetchone()

            if not gate:
                print("REGISTRY_ERROR reason=missing_review_gate")
                return 1

            if gate["decision"] != "READY_FOR_RUNTIME_REVIEW":
                print(
                    "REGISTRY_ERROR "
                    f"reason=review_gate_not_passed "
                    f"decision={gate['decision']}"
                )
                return 1

            payload = {
                "source": "lkoh_sell_only_candidate_registry_v1",
                "strategy": gate["strategy"],
                "closed_trades": gate["closed_trades"],
                "winrate": gate["winrate"],
                "expectancy": gate["expectancy"],
                "profit_factor": gate["profit_factor"],
                "review_gate_decision": gate["decision"],
                "review_gate_reason": gate["reason"],
                "runtime_allowed": False,
                "execution_enabled": False,
            }

            cur.execute(
                SQL_UPSERT,
                {
                    "symbol": SYMBOL,
                    "source": SOURCE,
                    "raw_json": json.dumps(payload, ensure_ascii=False, default=str),
                },
            )
            row = cur.fetchone()

        conn.commit()

    print(
        "REGISTRY_ROW "
        f"symbol={row['symbol']} "
        f"status={row['status']} "
        f"reason={row['reason']} "
        f"source={row['source']} "
        f"runtime_allowed={int(row['runtime_allowed'])} "
        f"execution_enabled={int(row['execution_enabled'])} "
        f"updated_at={row['updated_at']}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=LKOH_REGISTERED_FOR_RUNTIME_REVIEW")
    print("LKOH_SELL_ONLY_CANDIDATE_REGISTRY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
