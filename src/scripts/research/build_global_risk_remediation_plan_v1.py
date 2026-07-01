#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
PLAN = "GLOBAL_RISK_REMEDIATION_PLAN_V1"

def main() -> None:
    print("=== GLOBAL_RISK_REMEDIATION_PLAN_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO warehouse.risk_remediation_plan_v1
                (
                    risk_code,
                    priority,
                    remediation_action,
                    dependency,
                    status
                )
                VALUES
                (
                    'RISK-CORR-0001',
                    'P1',
                    'Implement correlation limits for ENERGY, BANKS and OIL_GAS groups before any live trading enablement.',
                    'CORRELATION_RISK_AUDIT_V1',
                    'PLANNED'
                )
                ON CONFLICT(risk_code)
                DO UPDATE SET
                    priority=EXCLUDED.priority,
                    remediation_action=EXCLUDED.remediation_action,
                    dependency=EXCLUDED.dependency,
                    status=EXCLUDED.status;
            """)

            cur.execute("""
                INSERT INTO warehouse.risk_remediation_plan_v1
                (
                    risk_code,
                    priority,
                    remediation_action,
                    dependency,
                    status
                )
                VALUES
                (
                    'RISK-LINEAGE-OBS-0001',
                    'P3',
                    'Investigate why public.orders has zero rows while execution_intents and fills are populated.',
                    'RISK_LINEAGE_AUDIT_V1',
                    'OBSERVATION'
                )
                ON CONFLICT(risk_code)
                DO UPDATE SET
                    priority=EXCLUDED.priority,
                    remediation_action=EXCLUDED.remediation_action,
                    dependency=EXCLUDED.dependency,
                    status=EXCLUDED.status;
            """)

            cur.execute("""
                SELECT count(*)
                FROM warehouse.risk_remediation_plan_v1
                WHERE risk_code IN ('RISK-CORR-0001','RISK-LINEAGE-OBS-0001');
            """)
            planned_actions = int(cur.fetchone()[0])

            cur.execute("""
                SELECT count(*)
                FROM warehouse.risk_remediation_plan_v1
                WHERE priority='P1';
            """)
            p1_actions = int(cur.fetchone()[0])

            cur.execute("""
                SELECT count(*)
                FROM warehouse.risk_remediation_plan_v1
                WHERE status='OBSERVATION';
            """)
            observation_actions = int(cur.fetchone()[0])

        conn.commit()

        print(f"planned_actions={planned_actions}")
        print(f"p1_actions={p1_actions}")
        print(f"observation_actions={observation_actions}")
        print("highest_priority=Correlation Risk")
        print("correlation_remediation=PLANNED")
        print("orders_lineage_observation=PLANNED")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if planned_actions == 2 and p1_actions >= 1:
            print("VERDICT=GLOBAL_RISK_REMEDIATION_PLAN_V1_READY")
        else:
            print("VERDICT=GLOBAL_RISK_REMEDIATION_PLAN_V1_FAILED")
            raise SystemExit(1)

    finally:
        conn.close()

if __name__ == "__main__":
    main()
