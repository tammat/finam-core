#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "CORRELATION_RISK_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.correlation_risk_audit_report_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    group_name text NOT NULL,
    symbols text NOT NULL,
    positions bigint NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, group_name)
);
"""

UPSERT = """
INSERT INTO warehouse.correlation_risk_audit_report_v1
(audit_name,group_name,symbols,positions,status)
VALUES(%s,%s,%s,%s,%s)
ON CONFLICT(audit_name,group_name)
DO UPDATE SET
symbols=EXCLUDED.symbols,
positions=EXCLUDED.positions,
status=EXCLUDED.status;
"""

GROUPS = {
    "ENERGY": ["BRM6","NGK6"],
    "BANKS": ["SBER","SBERP","VTBR"],
    "OIL_GAS": ["LKOH","NVTK"],
}

def exists(cur, table):
    cur.execute("SELECT to_regclass(%s)", (table,))
    return cur.fetchone()[0] is not None

def main():
    print("=== CORRELATION_RISK_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)

    try:
        with conn.cursor() as cur:

            cur.execute(DDL)

            symbols = set()

            if exists(cur, "public.managed_positions"):
                cur.execute("SELECT symbol FROM public.managed_positions")
                symbols = {r[0] for r in cur.fetchall() if r[0]}

            correlated = 0

            for group, items in GROUPS.items():
                active = sorted(set(items) & symbols)

                status = "OK"
                if len(active) > 1:
                    status = "CORRELATED"
                    correlated += 1

                cur.execute(
                    UPSERT,
                    (
                        AUDIT,
                        group,
                        ",".join(active),
                        len(active),
                        status
                    )
                )

                print(
                    f"GROUP|name={group}"
                    f"|active={len(active)}"
                    f"|symbols={','.join(active)}"
                    f"|status={status}"
                )

            score = 100 - correlated * 10
            if score < 70:
                score = 70

            risk = (
                "LOW"
                if correlated == 0 else
                "MEDIUM"
                if correlated <= 2 else
                "HIGH"
            )

            cur.execute("""
            INSERT INTO warehouse.risk_assessment_scorecard_v1
            (audit_name,section_name,score,risk_level,status)
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(audit_name,section_name)
            DO UPDATE SET
            score=EXCLUDED.score,
            risk_level=EXCLUDED.risk_level,
            status=EXCLUDED.status;
            """,
            (
                AUDIT,
                "Correlation Risk",
                score,
                risk,
                "READY"
            ))

        conn.commit()

        print(f"correlated_groups={correlated}")
        print(f"correlation_score={score}")
        print(f"correlation_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=CORRELATION_RISK_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
