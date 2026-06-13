#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS runtime_candidate_decision_board (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    candidate_status text,
    review_gate text,
    expectancy numeric,
    profit_factor numeric,
    stability_ratio numeric,
    decision text NOT NULL,
    decision_reason text,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_candidate_decision_board_symbol_created
ON runtime_candidate_decision_board(symbol, created_at DESC);
"""

SQL = """
WITH latest AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        status,
        review_gate,
        expectancy,
        profit_factor,
        stability_ratio,
        runtime_allowed,
        execution_enabled,
        reason
    FROM runtime_candidate_scorecard
    ORDER BY symbol, id DESC
)
SELECT *
FROM latest
ORDER BY symbol;
"""

INSERT = """
INSERT INTO runtime_candidate_decision_board (
    symbol,
    candidate_status,
    review_gate,
    expectancy,
    profit_factor,
    stability_ratio,
    decision,
    decision_reason,
    runtime_allowed,
    execution_enabled,
    raw_json
)
VALUES (
    %(symbol)s,
    %(candidate_status)s,
    %(review_gate)s,
    %(expectancy)s,
    %(profit_factor)s,
    %(stability_ratio)s,
    %(decision)s,
    %(decision_reason)s,
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

def classify(row: dict) -> tuple[str, str]:
    status = row["status"]
    review_gate = row["review_gate"]
    stability_ratio = float(row["stability_ratio"]) if row["stability_ratio"] is not None else 0.0

    if (
        status == "READY_FOR_RUNTIME_REVIEW"
        and review_gate == "READY_FOR_RUNTIME_REVIEW"
        and stability_ratio >= 0.70
    ):
        return "PROMOTE_RUNTIME_REVIEW", "review_gate_passed"

    if status in ("RESEARCH", "WATCH_RUNTIME", "WATCH_RUNTIME_ACTIVE"):
        return "WATCH_RESEARCH", "continue_research_or_watch"

    return "REJECT", "candidate_rejected_or_not_ready"

def main() -> int:
    print("=== RUNTIME CANDIDATE DECISION BOARD V1 ===")
    print("mode=decision_board")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    promote = 0
    watch = 0
    reject = 0
    rows_written = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("DECISION_ROWS")

            for row in rows:
                decision, decision_reason = classify(row)

                if decision == "PROMOTE_RUNTIME_REVIEW":
                    promote += 1
                elif decision == "WATCH_RESEARCH":
                    watch += 1
                else:
                    reject += 1

                payload = {k: jsonable(v) for k, v in dict(row).items()}
                payload["decision"] = decision
                payload["decision_reason"] = decision_reason
                payload["runtime_allowed"] = False
                payload["execution_enabled"] = False

                cur.execute(
                    INSERT,
                    {
                        "symbol": row["symbol"],
                        "candidate_status": row["status"],
                        "review_gate": row["review_gate"],
                        "expectancy": row["expectancy"],
                        "profit_factor": row["profit_factor"],
                        "stability_ratio": row["stability_ratio"],
                        "decision": decision,
                        "decision_reason": decision_reason,
                        "raw_json": json.dumps(payload, ensure_ascii=False),
                    },
                )
                rows_written += 1

                print(
                    "DECISION_ROW "
                    f"symbol={row['symbol']} "
                    f"status={row['status']} "
                    f"review_gate={row['review_gate']} "
                    f"expectancy={row['expectancy']} "
                    f"profit_factor={row['profit_factor']} "
                    f"stability_ratio={row['stability_ratio']} "
                    f"decision={decision} "
                    f"reason={decision_reason} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(
        "SUMMARY_ROW "
        f"promote={promote} "
        f"watch={watch} "
        f"reject={reject} "
        f"rows_written={rows_written}"
    )
    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=RUNTIME_DECISION_BOARD_READY")
    print("RUNTIME_CANDIDATE_DECISION_BOARD_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
