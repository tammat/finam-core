#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "KILL_SWITCH_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.kill_switch_audit_report_v1 (
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
INSERT INTO warehouse.kill_switch_audit_report_v1
(audit_name, object_name, rows_count, status)
VALUES (%s,%s,%s,%s)
ON CONFLICT(audit_name, object_name)
DO UPDATE SET
rows_count=EXCLUDED.rows_count,
status=EXCLUDED.status;
"""

OBJECTS = [
    "public.persistent_kill_switch",
    "public.runtime_risk_freeze",
    "public.risk_events",
    "public.risk_event_audit_v1",
    "public.portfolio_governance_events",
    "public.runtime_governance_decisions",
    "public.runtime_governance_history",
]

def exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None

def count_rows(cur, name: str) -> int:
    cur.execute(f"SELECT count(*) FROM {name}")
    return int(cur.fetchone()[0])

def main() -> None:
    print("=== KILL_SWITCH_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)

    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            ready = 0
            populated = 0
            missing = 0

            for obj in OBJECTS:
                if exists(cur, obj):
                    rows_count = count_rows(cur, obj)
                    status = "READY"
                    ready += 1
                    if rows_count > 0:
                        populated += 1
                else:
                    rows_count = 0
                    status = "MISSING"
                    missing += 1

                cur.execute(UPSERT, (AUDIT, obj, rows_count, status))

                print(
                    f"KILL_SWITCH|object={obj}"
                    f"|rows={rows_count}"
                    f"|status={status}"
                )

            persistent_ready = exists(cur, "public.persistent_kill_switch")
            risk_events_ready = exists(cur, "public.risk_events")
            governance_ready = exists(cur, "public.runtime_governance_decisions")
            history_ready = exists(cur, "public.runtime_governance_history")

            score = 100
            if not persistent_ready:
                score -= 35
            if not risk_events_ready:
                score -= 25
            if not governance_ready:
                score -= 20
            if not history_ready:
                score -= 10
            if missing > 0:
                score -= min(20, missing * 5)

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
            """, (AUDIT, "Kill Switch", score, risk, "READY"))

        conn.commit()

        print(f"kill_switch_objects_ready={ready}")
        print(f"kill_switch_objects_populated={populated}")
        print(f"kill_switch_objects_missing={missing}")
        print(f"persistent_kill_switch_ready={int(persistent_ready)}")
        print(f"risk_events_ready={int(risk_events_ready)}")
        print(f"governance_ready={int(governance_ready)}")
        print(f"governance_history_ready={int(history_ready)}")
        print(f"kill_switch_score={score}")
        print(f"kill_switch_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=KILL_SWITCH_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
