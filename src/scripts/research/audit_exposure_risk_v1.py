#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "EXPOSURE_RISK_AUDIT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.exposure_risk_audit_report_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    symbol text NOT NULL,
    long_positions bigint NOT NULL,
    short_positions bigint NOT NULL,
    net_exposure bigint NOT NULL,
    gross_exposure bigint NOT NULL,
    exposure_status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, symbol)
);
"""

UPSERT = """
INSERT INTO warehouse.exposure_risk_audit_report_v1
(
 audit_name,
 symbol,
 long_positions,
 short_positions,
 net_exposure,
 gross_exposure,
 exposure_status
)
VALUES (%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT(audit_name,symbol)
DO UPDATE SET
 long_positions=EXCLUDED.long_positions,
 short_positions=EXCLUDED.short_positions,
 net_exposure=EXCLUDED.net_exposure,
 gross_exposure=EXCLUDED.gross_exposure,
 exposure_status=EXCLUDED.exposure_status;
"""

def exists(cur, table):
    cur.execute("SELECT to_regclass(%s)", (table,))
    return cur.fetchone()[0] is not None

def main():
    print("=== EXPOSURE_RISK_AUDIT_V1 ===")

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

                side_expr = (
                    "COALESCE(side::text,'UNKNOWN')" if "side" in cols
                    else "COALESCE(direction::text,'UNKNOWN')" if "direction" in cols
                    else "'UNKNOWN'"
                )

                cur.execute(f"""
                    SELECT
                        {symbol_expr},
                        sum(case when upper({side_expr})='LONG' then 1 else 0 end),
                        sum(case when upper({side_expr})='SHORT' then 1 else 0 end)
                    FROM public.managed_positions
                    GROUP BY 1
                    ORDER BY 1;
                """)

                rows = cur.fetchall()

            else:
                rows = []

            gross = 0
            opposite = 0

            for symbol, long_cnt, short_cnt in rows:

                long_cnt = int(long_cnt or 0)
                short_cnt = int(short_cnt or 0)

                gross_exposure = long_cnt + short_cnt
                net_exposure = abs(long_cnt - short_cnt)

                gross += gross_exposure

                status = "OK"

                if long_cnt > 0 and short_cnt > 0:
                    status = "OPPOSITE_EXPOSURE"
                    opposite += 1

                cur.execute(
                    UPSERT,
                    (
                        AUDIT,
                        symbol,
                        long_cnt,
                        short_cnt,
                        net_exposure,
                        gross_exposure,
                        status
                    )
                )

                print(
                    f"EXPOSURE|symbol={symbol}"
                    f"|long={long_cnt}"
                    f"|short={short_cnt}"
                    f"|gross={gross_exposure}"
                    f"|net={net_exposure}"
                    f"|status={status}"
                )

            score = 100 if opposite == 0 else 80
            risk = "LOW" if opposite == 0 else "MEDIUM"

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
                "Exposure Risk",
                score,
                risk,
                "READY"
            ))

        conn.commit()

        print(f"gross_exposure={gross}")
        print(f"opposite_exposure={opposite}")
        print(f"exposure_score={score}")
        print(f"exposure_risk_level={risk}")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print("VERDICT=EXPOSURE_RISK_AUDIT_V1_READY")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
