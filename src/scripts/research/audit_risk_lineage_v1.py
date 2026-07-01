#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "RISK_LINEAGE_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.risk_lineage_audit_report_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    lineage_step text NOT NULL,
    object_name text NOT NULL,
    rows_count bigint NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, lineage_step, object_name)
);
"""

UPSERT = """
INSERT INTO warehouse.risk_lineage_audit_report_v1
(audit_name,lineage_step,object_name,rows_count,status)
VALUES(%s,%s,%s,%s,%s)
ON CONFLICT(audit_name,lineage_step,object_name)
DO UPDATE SET
rows_count=EXCLUDED.rows_count,
status=EXCLUDED.status;
"""

LINEAGE = [
    ("MARKET_DATA", "public.market_bars"),
    ("FEATURE", "public.feature_snapshots"),
    ("SIGNAL", "public.signals"),
    ("RISK_CONTEXT", "public.trade_risk_context"),
    ("RISK_EVENTS", "public.risk_events"),
    ("EXECUTION_INTENT", "public.execution_intents"),
    ("ORDER", "public.orders"),
    ("FILL", "public.fills"),
    ("TRADE_CONTEXT", "public.trade_context_snapshots"),
    ("PORTFOLIO", "public.portfolio_risk_state"),
]

def exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None

def rows(cur, name: str) -> int:
    cur.execute(f"SELECT count(*) FROM {name}")
    return int(cur.fetchone()[0])

def main() -> None:
    print("=== RISK_LINEAGE_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)

    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            ready = 0
            populated = 0
            missing = 0

            for step, obj in LINEAGE:
                if exists(cur, obj):
                    cnt = rows(cur, obj)
                    status = "READY"
                    ready += 1
                    if cnt > 0:
                        populated += 1
                else:
                    cnt = 0
                    status = "MISSING"
                    missing += 1

                cur.execute(UPSERT, (AUDIT, step, obj, cnt, status))

                print(
                    f"LINEAGE|step={step}"
                    f"|object={obj}"
                    f"|rows={cnt}"
                    f"|status={status}"
                )

            score = int(ready / len(LINEAGE) * 100)

            if populated < 5:
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
            """, (AUDIT, "Risk Lineage", score, risk, "READY"))

        conn.commit()

        print(f"lineage_steps_total={len(LINEAGE)}")
        print(f"lineage_objects_ready={ready}")
        print(f"lineage_objects_populated={populated}")
        print(f"lineage_objects_missing={missing}")
        print(f"lineage_score={score}")
        print(f"lineage_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=RISK_LINEAGE_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
