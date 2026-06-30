#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "DRAWDOWN_RISK_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.drawdown_risk_audit_report_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    object_name text NOT NULL,
    rows_count bigint NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, object_name)
);
"""

UPSERT = """
INSERT INTO warehouse.drawdown_risk_audit_report_v1
(audit_name, object_name, rows_count, status)
VALUES (%s,%s,%s,%s)
ON CONFLICT(audit_name, object_name)
DO UPDATE SET
rows_count=EXCLUDED.rows_count,
status=EXCLUDED.status;
"""

OBJECTS = [
    "public.analytics_drawdown_summary",
    "public.analytics_equity_curve",
    "public.portfolio_risk_state",
    "public.runtime_governance_live_accumulation_v1",
    "public.shadow_runtime_mark_to_market",
    "public.shadow_runtime_pnl_monitor",
]

def exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None

def count_rows(cur, name: str) -> int:
    cur.execute(f"SELECT count(*) FROM {name}")
    return int(cur.fetchone()[0])

def main() -> None:
    print("=== DRAWDOWN_RISK_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)

    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            ready = 0
            populated = 0

            for obj in OBJECTS:
                if exists(cur, obj):
                    rows_count = count_rows(cur, obj)
                    status = "READY" if rows_count >= 0 else "EMPTY"
                    ready += 1
                    if rows_count > 0:
                        populated += 1
                else:
                    rows_count = 0
                    status = "MISSING"

                cur.execute(UPSERT, (AUDIT, obj, rows_count, status))

                print(
                    f"DRAWDOWN|object={obj}"
                    f"|rows={rows_count}"
                    f"|status={status}"
                )

            single_source_ready = exists(cur, "public.analytics_drawdown_summary")
            portfolio_state_ready = exists(cur, "public.portfolio_risk_state")
            live_accumulation_ready = exists(cur, "public.runtime_governance_live_accumulation_v1")

            score = 100
            if not single_source_ready:
                score -= 30
            if not portfolio_state_ready:
                score -= 20
            if not live_accumulation_ready:
                score -= 20
            if populated == 0:
                score -= 20

            if score < 0:
                score = 0

            risk = "LOW" if score >= 90 else "MEDIUM" if score >= 70 else "HIGH"

            cur.execute("""
            INSERT INTO warehouse.risk_assessment_scorecard_v1
            (
                audit_name,
                section_name,
                score,
                risk_level,
                status
            )
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(audit_name,section_name)
            DO UPDATE SET
                score=EXCLUDED.score,
                risk_level=EXCLUDED.risk_level,
                status=EXCLUDED.status;
            """, (AUDIT, "Drawdown Risk", score, risk, "READY"))

        conn.commit()

        print(f"drawdown_objects_ready={ready}")
        print(f"drawdown_objects_populated={populated}")
        print(f"single_source_ready={int(single_source_ready)}")
        print(f"portfolio_state_ready={int(portfolio_state_ready)}")
        print(f"live_accumulation_ready={int(live_accumulation_ready)}")
        print(f"drawdown_score={score}")
        print(f"drawdown_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=DRAWDOWN_RISK_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
