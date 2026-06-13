#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

SYMBOL = "LKOH@MISX"
STRATEGY = "lkoh_sell_only_scorecard_v1"

SQL = """
SELECT
    symbol,
    strategy,
    closed_trades,
    winrate,
    expectancy,
    profit_factor,
    verdict AS scorecard_verdict
FROM lkoh_sell_only_scorecard
WHERE symbol=%s
ORDER BY id DESC
LIMIT 1;
"""

DDL = """
CREATE TABLE IF NOT EXISTS lkoh_sell_only_review_gate (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    strategy text NOT NULL,
    closed_trades integer,
    winrate numeric,
    expectancy numeric,
    profit_factor numeric,
    scorecard_verdict text,
    decision text NOT NULL,
    reason text,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb
);
"""

INSERT = """
INSERT INTO lkoh_sell_only_review_gate (
    symbol, strategy, closed_trades, winrate, expectancy, profit_factor,
    scorecard_verdict, decision, reason,
    runtime_allowed, execution_enabled, raw_json
)
VALUES (
    %(symbol)s, %(strategy)s, %(closed_trades)s, %(winrate)s, %(expectancy)s, %(profit_factor)s,
    %(scorecard_verdict)s, %(decision)s, %(reason)s,
    false, false, %(raw_json)s
);
"""

def main() -> int:
    print("=== LKOH SELL ONLY REVIEW GATE V1 ===")
    print("mode=review_gate")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (SYMBOL,))
            row = cur.fetchone()

            if not row:
                print("REVIEW_GATE_ERROR reason=missing_lkoh_sell_only_scorecard")
                return 1

            pf = float(row["profit_factor"] or 0)
            exp = float(row["expectancy"] or 0)
            trades = int(row["closed_trades"] or 0)

            passed = (
                trades >= 300
                and exp > 0
                and pf >= 1.5
                and row["scorecard_verdict"] == "LKOH_SELL_ONLY_READY_FOR_REVIEW"
            )

            decision = "READY_FOR_RUNTIME_REVIEW" if passed else "CONTINUE_RESEARCH"
            reason = "lkoh_sell_only_gate_passed" if passed else "lkoh_sell_only_gate_failed"

            payload = {
                **dict(row),
                "decision": decision,
                "reason": reason,
                "runtime_allowed": False,
                "execution_enabled": False,
            }

            cur.execute(
                INSERT,
                {
                    **dict(row),
                    "decision": decision,
                    "reason": reason,
                    "raw_json": json.dumps(payload, ensure_ascii=False, default=str),
                },
            )
        conn.commit()

    print(
        "REVIEW_GATE_ROW "
        f"symbol={row['symbol']} "
        f"closed_trades={row['closed_trades']} "
        f"winrate={row['winrate']} "
        f"expectancy={row['expectancy']} "
        f"profit_factor={row['profit_factor']} "
        f"scorecard_verdict={row['scorecard_verdict']} "
        f"decision={decision} "
        f"reason={reason} "
        "runtime_allowed=0 "
        "execution_enabled=0"
    )
    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={decision}")
    print("LKOH_SELL_ONLY_REVIEW_GATE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
