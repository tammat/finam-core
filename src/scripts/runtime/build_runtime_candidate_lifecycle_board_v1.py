#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS runtime_candidate_lifecycle_board (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    event_type text NOT NULL,
    event_status text,
    event_reason text,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_candidate_lifecycle_board_symbol_created
ON runtime_candidate_lifecycle_board(symbol, created_at DESC);
"""

SQL = """
WITH registry AS (
    SELECT
        symbol,
        'REGISTRY'::text AS event_type,
        status AS event_status,
        reason AS event_reason,
        runtime_allowed,
        execution_enabled,
        updated_at AS source_ts
    FROM runtime_candidate_registry
),
review_gate AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        'REVIEW_GATE'::text AS event_type,
        decision AS event_status,
        reason AS event_reason,
        runtime_allowed,
        execution_enabled,
        created_at AS source_ts
    FROM gold_runtime_review_gate
    ORDER BY symbol, id DESC
),
decision AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        'DECISION'::text AS event_type,
        decision AS event_status,
        decision_reason AS event_reason,
        runtime_allowed,
        execution_enabled,
        created_at AS source_ts
    FROM runtime_candidate_decision_board
    ORDER BY symbol, id DESC
),
events AS (
    SELECT * FROM registry
    UNION ALL
    SELECT * FROM review_gate
    UNION ALL
    SELECT * FROM decision
)
SELECT *
FROM events
ORDER BY symbol, source_ts, event_type;
"""

INSERT = """
INSERT INTO runtime_candidate_lifecycle_board (
    symbol,
    event_type,
    event_status,
    event_reason,
    runtime_allowed,
    execution_enabled,
    raw_json
)
VALUES (
    %(symbol)s,
    %(event_type)s,
    %(event_status)s,
    %(event_reason)s,
    false,
    false,
    %(raw_json)s
);
"""

def jsonable(value):
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value

def main() -> int:
    print("=== RUNTIME CANDIDATE LIFECYCLE BOARD V1 ===")
    print("mode=lifecycle_board")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    symbols = set()
    events_count = 0
    promote = 0
    watch = 0
    reject = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("LIFECYCLE_ROWS")

            for row in rows:
                symbols.add(row["symbol"])
                events_count += 1

                status = row["event_status"]
                if status in ("READY_FOR_RUNTIME_REVIEW", "PROMOTE_RUNTIME_REVIEW"):
                    promote += 1
                elif status in ("RESEARCH", "WATCH_RESEARCH", "WATCH_RUNTIME", "WATCH_RUNTIME_ACTIVE"):
                    watch += 1
                elif status in ("REJECTED", "REJECT"):
                    reject += 1

                payload = {k: jsonable(v) for k, v in dict(row).items()}
                payload["runtime_allowed"] = False
                payload["execution_enabled"] = False

                cur.execute(
                    INSERT,
                    {
                        "symbol": row["symbol"],
                        "event_type": row["event_type"],
                        "event_status": row["event_status"],
                        "event_reason": row["event_reason"],
                        "raw_json": json.dumps(payload, ensure_ascii=False),
                    },
                )

                print(
                    "LIFECYCLE_ROW "
                    f"symbol={row['symbol']} "
                    f"event_type={row['event_type']} "
                    f"status={row['event_status']} "
                    f"reason={row['event_reason']} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(
        "SUMMARY_ROW "
        f"symbols={len(symbols)} "
        f"events={events_count} "
        f"promote={promote} "
        f"watch={watch} "
        f"reject={reject}"
    )

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=RUNTIME_CANDIDATE_LIFECYCLE_READY")
    print("RUNTIME_CANDIDATE_LIFECYCLE_BOARD_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
