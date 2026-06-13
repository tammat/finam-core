#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

DDL = """
CREATE TABLE IF NOT EXISTS runtime_review_package (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    source text,
    candidate_status text,
    decision_status text,
    signals integer,
    closed_trades integer,
    winrate numeric,
    expectancy numeric,
    profit_factor numeric,
    stability_ratio numeric,
    review_verdict text NOT NULL,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_runtime_review_package_symbol_created
ON runtime_review_package(symbol, created_at DESC);
"""

SQL = """
WITH scorecard AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        status,
        source,
        signals,
        trades,
        winrate,
        expectancy,
        profit_factor,
        stability_ratio,
        runtime_allowed,
        execution_enabled
    FROM runtime_candidate_scorecard
    ORDER BY symbol, id DESC
),
decision AS (
    SELECT DISTINCT ON (symbol)
        symbol,
        decision,
        decision_reason
    FROM runtime_candidate_decision_board
    ORDER BY symbol, id DESC
)
SELECT
    s.*,
    d.decision,
    d.decision_reason
FROM scorecard s
LEFT JOIN decision d ON d.symbol = s.symbol
ORDER BY s.symbol;
"""

INSERT = """
INSERT INTO runtime_review_package (
    symbol,
    source,
    candidate_status,
    decision_status,
    signals,
    closed_trades,
    winrate,
    expectancy,
    profit_factor,
    stability_ratio,
    review_verdict,
    runtime_allowed,
    execution_enabled,
    raw_json
)
VALUES (
    %(symbol)s,
    %(source)s,
    %(candidate_status)s,
    %(decision_status)s,
    %(signals)s,
    %(closed_trades)s,
    %(winrate)s,
    %(expectancy)s,
    %(profit_factor)s,
    %(stability_ratio)s,
    %(review_verdict)s,
    false,
    false,
    %(raw_json)s
);
"""

def main() -> int:
    print("=== RUNTIME REVIEW PACKAGE V1 ===")
    print("mode=runtime_review_package")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    rows_written = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL)
            rows = cur.fetchall()

            print("PACKAGE_ROWS")

            for row in rows:
                if row["decision"] == "PROMOTE_RUNTIME_REVIEW":
                    review_verdict = "READY_FOR_SHADOW_RUNTIME"
                elif row["status"] == "REJECTED" or row["decision"] == "REJECT":
                    review_verdict = "REJECTED"
                else:
                    review_verdict = "RESEARCH_CONTINUE"

                payload = dict(row)
                payload["review_verdict"] = review_verdict
                payload["runtime_allowed"] = False
                payload["execution_enabled"] = False

                cur.execute(
                    INSERT,
                    {
                        "symbol": row["symbol"],
                        "source": row["source"],
                        "candidate_status": row["status"],
                        "decision_status": row["decision"],
                        "signals": row["signals"],
                        "closed_trades": row["trades"],
                        "winrate": row["winrate"],
                        "expectancy": row["expectancy"],
                        "profit_factor": row["profit_factor"],
                        "stability_ratio": row["stability_ratio"],
                        "review_verdict": review_verdict,
                        "raw_json": json.dumps(payload, ensure_ascii=False, default=str),
                    },
                )
                rows_written += 1

                print(
                    "PACKAGE_ROW "
                    f"symbol={row['symbol']} "
                    f"source={row['source']} "
                    f"candidate_status={row['status']} "
                    f"decision_status={row['decision']} "
                    f"trades={row['trades']} "
                    f"expectancy={row['expectancy']} "
                    f"profit_factor={row['profit_factor']} "
                    f"review_verdict={review_verdict} "
                    "runtime_allowed=0 "
                    "execution_enabled=0"
                )

        conn.commit()

    print()
    print(f"PACKAGE_ROWS_WRITTEN={rows_written}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=RUNTIME_REVIEW_PACKAGE_RECORDED")
    print("RUNTIME_REVIEW_PACKAGE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
