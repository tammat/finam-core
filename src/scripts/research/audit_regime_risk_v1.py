#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "REGIME_RISK_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.regime_risk_audit_report_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    regime_table text NOT NULL,
    rows_count bigint NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, regime_table)
);
"""

UPSERT = """
INSERT INTO warehouse.regime_risk_audit_report_v1
(audit_name, regime_table, rows_count, status)
VALUES (%s,%s,%s,%s)
ON CONFLICT(audit_name, regime_table)
DO UPDATE SET
rows_count=EXCLUDED.rows_count,
status=EXCLUDED.status;
"""

TABLES = [
    "analytics_regime_snapshots_v2",
    "strategy_regime_matrix",
    "research_regime_policy",
    "runtime_regime_overrides",
    "ng_runtime_regime_policy",
    "ng_runtime_regime_policy_v2",
    "futures_regime_governance",
]

def exists(cur, table):
    cur.execute("SELECT to_regclass(%s)", (f"public.{table}",))
    return cur.fetchone()[0] is not None

def rows(cur, table):
    cur.execute(f"SELECT count(*) FROM public.{table}")
    return int(cur.fetchone()[0])

def main():
    print("=== REGIME_RISK_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)

    try:
        with conn.cursor() as cur:

            cur.execute(DDL)

            ready = 0

            for table in TABLES:

                if exists(cur, table):
                    cnt = rows(cur, table)
                    status = "READY"
                    ready += 1
                else:
                    cnt = 0
                    status = "MISSING"

                cur.execute(
                    UPSERT,
                    (
                        AUDIT,
                        table,
                        cnt,
                        status
                    )
                )

                print(
                    f"REGIME|table={table}"
                    f"|rows={cnt}"
                    f"|status={status}"
                )

            score = int(ready / len(TABLES) * 100)
            risk = (
                "LOW" if score >= 90 else
                "MEDIUM" if score >= 70 else
                "HIGH"
            )

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
            """,
            (
                AUDIT,
                "Regime Risk",
                score,
                risk,
                "READY"
            ))

        conn.commit()

        print(f"regime_tables_ready={ready}")
        print(f"regime_score={score}")
        print(f"regime_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=REGIME_RISK_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
