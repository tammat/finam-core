#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"

DDL = """
CREATE TABLE IF NOT EXISTS gold_runtime_review_gate (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    registry_status text,
    registry_reason text,
    mandatory_filter_rule text,
    stability_verdict text,
    stability_ratio numeric,
    negative_ratio numeric,
    days_effective integer,
    days_stable integer,
    filtered_pnl numeric,
    telemetry_status text,
    shadow_signals integer,
    shadow_trades integer,
    shadow_winrate numeric,
    shadow_expectancy numeric,
    shadow_profit_factor numeric,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    decision text NOT NULL,
    reason text,
    raw_json jsonb
);

CREATE INDEX IF NOT EXISTS idx_gold_runtime_review_gate_symbol_created
ON gold_runtime_review_gate(symbol, created_at DESC);
"""

SQL = """
WITH registry AS (
    SELECT
        symbol,
        status,
        reason,
        runtime_allowed,
        execution_enabled,
        raw_json->'mandatory_filters'->'gold_shadow_regime_filter_v1'->>'rule' AS filter_rule
    FROM runtime_candidate_registry
    WHERE symbol=%s
),
stability AS (
    SELECT
        verdict,
        stability_ratio,
        negative_ratio,
        days_effective,
        days_stable,
        filtered_pnl
    FROM gold_shadow_stability_monitor
    WHERE symbol=%s
    ORDER BY id DESC
    LIMIT 1
),
telemetry AS (
    SELECT
        status,
        shadow_signals,
        shadow_trades,
        shadow_winrate,
        shadow_expectancy,
        shadow_profit_factor,
        runtime_allowed,
        execution_enabled
    FROM runtime_gold_watch_telemetry
    WHERE symbol=%s
    ORDER BY id DESC
    LIMIT 1
)
SELECT
    r.symbol,
    r.status AS registry_status,
    r.reason AS registry_reason,
    r.runtime_allowed AS registry_runtime_allowed,
    r.execution_enabled AS registry_execution_enabled,
    r.filter_rule AS mandatory_filter_rule,
    s.verdict AS stability_verdict,
    s.stability_ratio,
    s.negative_ratio,
    s.days_effective,
    s.days_stable,
    s.filtered_pnl,
    t.status AS telemetry_status,
    t.shadow_signals,
    t.shadow_trades,
    t.shadow_winrate,
    t.shadow_expectancy,
    t.shadow_profit_factor,
    t.runtime_allowed AS telemetry_runtime_allowed,
    t.execution_enabled AS telemetry_execution_enabled
FROM registry r
LEFT JOIN stability s ON true
LEFT JOIN telemetry t ON true;
"""

INSERT = """
INSERT INTO gold_runtime_review_gate (
    symbol,
    registry_status,
    registry_reason,
    mandatory_filter_rule,
    stability_verdict,
    stability_ratio,
    negative_ratio,
    days_effective,
    days_stable,
    filtered_pnl,
    telemetry_status,
    shadow_signals,
    shadow_trades,
    shadow_winrate,
    shadow_expectancy,
    shadow_profit_factor,
    runtime_allowed,
    execution_enabled,
    decision,
    reason,
    raw_json
)
VALUES (
    %(symbol)s,
    %(registry_status)s,
    %(registry_reason)s,
    %(mandatory_filter_rule)s,
    %(stability_verdict)s,
    %(stability_ratio)s,
    %(negative_ratio)s,
    %(days_effective)s,
    %(days_stable)s,
    %(filtered_pnl)s,
    %(telemetry_status)s,
    %(shadow_signals)s,
    %(shadow_trades)s,
    %(shadow_winrate)s,
    %(shadow_expectancy)s,
    %(shadow_profit_factor)s,
    false,
    false,
    %(decision)s,
    %(reason)s,
    %(raw_json)s
);
"""

def j(v):
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v

def main() -> int:
    print("=== GOLD RUNTIME REVIEW GATE V1 ===")
    print("mode=review_gate")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (SYMBOL, SYMBOL, SYMBOL))
            row = cur.fetchone()

            if not row:
                print("REVIEW_GATE_ERROR reason=missing_registry")
                return 1

            checks = {
                "registry_watch_active": row["registry_status"] == "WATCH_RUNTIME_ACTIVE",
                "mandatory_filter_registered": row["mandatory_filter_rule"] == "up_impulse_sell_block",
                "stability_ready": row["stability_verdict"] == "GOLD_STABILITY_MONITOR_READY_FOR_REVIEW",
                "stability_ratio_ok": float(row["stability_ratio"] or 0) >= 0.70,
                "negative_ratio_ok": float(row["negative_ratio"] or 1) <= 0.20,
                "effective_days_ok": int(row["days_effective"] or 0) >= 3,
                "filtered_pnl_positive": float(row["filtered_pnl"] or 0) > 0,
                "telemetry_watch_active": row["telemetry_status"] == "WATCH_RUNTIME_ACTIVE",
                "runtime_still_off": row["registry_runtime_allowed"] is False and row["telemetry_runtime_allowed"] is False,
                "execution_still_off": row["registry_execution_enabled"] is False and row["telemetry_execution_enabled"] is False,
            }

            decision = "READY_FOR_RUNTIME_REVIEW" if all(checks.values()) else "CONTINUE_WATCH"
            failed = [k for k, v in checks.items() if not v]
            reason = "all_review_checks_passed" if not failed else "failed_checks=" + ",".join(failed)

            payload = {k: j(v) for k, v in dict(row).items()}
            payload["checks"] = checks
            payload["decision"] = decision
            payload["reason"] = reason
            payload["runtime_allowed"] = False
            payload["execution_enabled"] = False

            cur.execute(
                INSERT,
                {
                    **dict(row),
                    "decision": decision,
                    "reason": reason,
                    "raw_json": json.dumps(payload, ensure_ascii=False),
                },
            )

        conn.commit()

    print(
        "REVIEW_GATE_ROW "
        f"symbol={row['symbol']} "
        f"registry_status={row['registry_status']} "
        f"mandatory_filter_rule={row['mandatory_filter_rule']} "
        f"stability_verdict={row['stability_verdict']} "
        f"stability_ratio={row['stability_ratio']} "
        f"negative_ratio={row['negative_ratio']} "
        f"days_effective={row['days_effective']} "
        f"filtered_pnl={row['filtered_pnl']} "
        f"telemetry_status={row['telemetry_status']} "
        f"decision={decision} "
        f"reason={reason} "
        "runtime_allowed=0 "
        "execution_enabled=0"
    )

    print()
    for name, ok in checks.items():
        print(f"CHECK_ROW name={name} passed={int(ok)}")

    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print(f"VERDICT={decision}")
    print("GOLD_RUNTIME_REVIEW_GATE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
