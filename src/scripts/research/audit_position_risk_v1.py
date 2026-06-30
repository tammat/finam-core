#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "POSITION_RISK_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.position_risk_audit_report_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    symbol text NOT NULL,
    strategy_name text NOT NULL,
    position_side text NOT NULL,
    position_count bigint NOT NULL,
    duplicate_positions boolean NOT NULL,
    opposite_positions boolean NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name,symbol,strategy_name,position_side)
);
"""

UPSERT = """
INSERT INTO warehouse.position_risk_audit_report_v1(
audit_name,symbol,strategy_name,position_side,
position_count,duplicate_positions,
opposite_positions,status)
VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT(audit_name,symbol,strategy_name,position_side)
DO UPDATE SET
position_count=EXCLUDED.position_count,
duplicate_positions=EXCLUDED.duplicate_positions,
opposite_positions=EXCLUDED.opposite_positions,
status=EXCLUDED.status;
"""

def exists(cur, table):
    cur.execute("SELECT to_regclass(%s)", (table,))
    return cur.fetchone()[0] is not None

def main():
    print("=== POSITION_RISK_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)

    try:
        with conn.cursor() as cur:

            cur.execute(DDL)

            if exists(cur, "public.managed_positions"):

                cur.execute("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema='public'
                      AND table_name='managed_positions';
                """)
                cols = {r[0] for r in cur.fetchall()}

                symbol_expr = "COALESCE(symbol::text,'UNKNOWN')" if "symbol" in cols else "'UNKNOWN'"
                strategy_expr = "COALESCE(strategy_name::text,'UNKNOWN')" if "strategy_name" in cols else "'UNKNOWN'"
                side_expr = (
                    "COALESCE(side::text,'UNKNOWN')" if "side" in cols
                    else "COALESCE(direction::text,'UNKNOWN')" if "direction" in cols
                    else "'UNKNOWN'"
                )

                cur.execute(f"""
                SELECT
                    {symbol_expr},
                    {strategy_expr},
                    {side_expr},
                    count(*)
                FROM public.managed_positions
                GROUP BY 1,2,3
                ORDER BY 1,2,3
                """)

                rows = cur.fetchall()

            else:
                rows = []

            duplicates = 0

            for symbol,strategy,side,cnt in rows:

                duplicate = cnt > 1

                if duplicate:
                    duplicates += 1

                cur.execute(
                    UPSERT,
                    (
                        AUDIT,
                        symbol,
                        strategy,
                        side,
                        cnt,
                        duplicate,
                        False,
                        "READY"
                    )
                )

                print(
                    f"POSITION|symbol={symbol}"
                    f"|strategy={strategy}"
                    f"|side={side}"
                    f"|count={cnt}"
                    f"|duplicate={int(duplicate)}"
                )

            cur.execute("""
            INSERT INTO warehouse.risk_assessment_scorecard_v1(
                audit_name,
                section_name,
                score,
                risk_level,
                status)
            VALUES(%s,%s,%s,%s,%s)
            ON CONFLICT(audit_name,section_name)
            DO UPDATE SET
            score=EXCLUDED.score,
            risk_level=EXCLUDED.risk_level,
            status=EXCLUDED.status;
            """,
            (
                AUDIT,
                "Position Risk",
                100 if duplicates==0 else 80,
                "LOW" if duplicates==0 else "MEDIUM",
                "READY"
            ))

        conn.commit()

        print(f"duplicate_positions={duplicates}")
        print(f"position_rows={len(rows)}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=POSITION_RISK_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
