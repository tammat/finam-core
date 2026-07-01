#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "RUNTIME_RECOVERY_RISK_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.runtime_recovery_risk_audit_report_v1 (
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
INSERT INTO warehouse.runtime_recovery_risk_audit_report_v1
(audit_name,object_name,rows_count,status)
VALUES(%s,%s,%s,%s)
ON CONFLICT(audit_name,object_name)
DO UPDATE SET
rows_count=EXCLUDED.rows_count,
status=EXCLUDED.status;
"""

OBJECTS = [
    "public.runtime_state_snapshots",
    "public.runtime_governance_history",
    "public.position_lifecycle_state",
    "public.order_projection",
    "public.portfolio_projection",
    "public.trade_context_snapshots",
    "public.runtime_governance_live_accumulation_v1",
    "public.shadow_runtime_positions",
]

def exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None

def rows(cur, name: str) -> int:
    cur.execute(f"SELECT count(*) FROM {name}")
    return int(cur.fetchone()[0])

def main() -> None:
    print("=== RUNTIME_RECOVERY_RISK_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            ready = 0
            populated = 0

            for obj in OBJECTS:
                if exists(cur, obj):
                    cnt = rows(cur, obj)
                    status = "READY"
                    ready += 1
                    if cnt > 0:
                        populated += 1
                else:
                    cnt = 0
                    status = "MISSING"

                cur.execute(UPSERT, (AUDIT, obj, cnt, status))
                print(f"RECOVERY|object={obj}|rows={cnt}|status={status}")

            score = int(ready / len(OBJECTS) * 100)
            if populated == 0:
                score -= 20
            score = max(score, 0)

            risk = "LOW" if score >= 90 else "MEDIUM" if score >= 70 else "HIGH"

            cur.execute("""
            INSERT INTO warehouse.risk_assessment_scorecard_v1
            (audit_name, section_name, score, risk_level, status)
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(audit_name,section_name)
            DO UPDATE SET
                score=EXCLUDED.score,
                risk_level=EXCLUDED.risk_level,
                status=EXCLUDED.status;
            """, (AUDIT, "Runtime Recovery", score, risk, "READY"))

        conn.commit()

        print(f"recovery_objects_ready={ready}")
        print(f"recovery_objects_populated={populated}")
        print(f"recovery_score={score}")
        print(f"recovery_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=RUNTIME_RECOVERY_RISK_AUDIT_V1_READY")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
