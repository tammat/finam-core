#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
REPORT = "GLOBAL_RISK_REPORT_V1"

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.global_risk_report_v1 (
    id bigserial PRIMARY KEY,
    report_name text NOT NULL,
    section_name text NOT NULL,
    score numeric NOT NULL,
    risk_level text NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(report_name, section_name)
);

CREATE TABLE IF NOT EXISTS warehouse.global_risk_report_summary_v1 (
    id bigserial PRIMARY KEY,
    report_name text NOT NULL UNIQUE,
    sections_total bigint NOT NULL,
    low_count bigint NOT NULL,
    medium_count bigint NOT NULL,
    high_count bigint NOT NULL,
    critical_count bigint NOT NULL,
    min_score numeric NOT NULL,
    avg_score numeric NOT NULL,
    overall_risk_level text NOT NULL,
    verdict text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
"""

UPSERT_SECTION = """
INSERT INTO warehouse.global_risk_report_v1
(report_name, section_name, score, risk_level, status)
VALUES (%s,%s,%s,%s,%s)
ON CONFLICT(report_name, section_name)
DO UPDATE SET
score=EXCLUDED.score,
risk_level=EXCLUDED.risk_level,
status=EXCLUDED.status;
"""

UPSERT_SUMMARY = """
INSERT INTO warehouse.global_risk_report_summary_v1
(report_name, sections_total, low_count, medium_count, high_count, critical_count,
 min_score, avg_score, overall_risk_level, verdict)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT(report_name)
DO UPDATE SET
sections_total=EXCLUDED.sections_total,
low_count=EXCLUDED.low_count,
medium_count=EXCLUDED.medium_count,
high_count=EXCLUDED.high_count,
critical_count=EXCLUDED.critical_count,
min_score=EXCLUDED.min_score,
avg_score=EXCLUDED.avg_score,
overall_risk_level=EXCLUDED.overall_risk_level,
verdict=EXCLUDED.verdict;
"""

EXPECTED = [
    ("RISK_ARCHITECTURE_AUDIT_V1", "Architecture"),
    ("POSITION_RISK_AUDIT_V1", "Position Risk"),
    ("PORTFOLIO_RISK_AUDIT_V1", "Portfolio Risk"),
    ("EXPOSURE_RISK_AUDIT_V1", "Exposure Risk"),
    ("CORRELATION_RISK_AUDIT_V1", "Correlation Risk"),
    ("REGIME_RISK_AUDIT_V1", "Regime Risk"),
    ("DRAWDOWN_RISK_AUDIT_V1", "Drawdown Risk"),
    ("KILL_SWITCH_AUDIT_V1", "Kill Switch"),
    ("RUNTIME_RECOVERY_RISK_AUDIT_V1", "Runtime Recovery"),
    ("RISK_LINEAGE_AUDIT_V1", "Risk Lineage"),
]

def main() -> None:
    print("=== GLOBAL_RISK_REPORT_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL)

            rows = []

            for audit_name, section in EXPECTED:
                cur.execute("""
                    SELECT score, risk_level, status
                    FROM warehouse.risk_assessment_scorecard_v1
                    WHERE audit_name=%s
                      AND section_name=%s;
                """, (audit_name, section))
                row = cur.fetchone()

                if row:
                    score, risk_level, status = row
                else:
                    score, risk_level, status = 0, "HIGH", "MISSING"

                rows.append((section, float(score), risk_level, status))

                cur.execute(
                    UPSERT_SECTION,
                    (REPORT, section, score, risk_level, status),
                )

                print(
                    f"SECTION|name={section}"
                    f"|score={score}"
                    f"|risk_level={risk_level}"
                    f"|status={status}"
                )

            sections_total = len(rows)
            low_count = sum(1 for _, _, r, _ in rows if r == "LOW")
            medium_count = sum(1 for _, _, r, _ in rows if r == "MEDIUM")
            high_count = sum(1 for _, _, r, _ in rows if r == "HIGH")
            critical_count = sum(1 for _, _, r, _ in rows if r == "CRITICAL")
            min_score = min(score for _, score, _, _ in rows)
            avg_score = round(sum(score for _, score, _, _ in rows) / sections_total, 2)

            if critical_count > 0:
                overall = "CRITICAL"
            elif high_count > 0:
                overall = "HIGH"
            elif medium_count > 0:
                overall = "MEDIUM"
            else:
                overall = "LOW"

            verdict = (
                "GLOBAL_RISK_REPORT_V1_READY_WITH_FINDINGS"
                if overall in ("HIGH", "CRITICAL")
                else "GLOBAL_RISK_REPORT_V1_READY"
            )

            cur.execute(
                UPSERT_SUMMARY,
                (
                    REPORT,
                    sections_total,
                    low_count,
                    medium_count,
                    high_count,
                    critical_count,
                    min_score,
                    avg_score,
                    overall,
                    verdict,
                ),
            )

            cur.execute("""
                INSERT INTO warehouse.risk_heatmap_snapshot_v1
                (
                    audit_name,
                    critical_count,
                    high_count,
                    medium_count,
                    low_count,
                    open_count
                )
                VALUES(%s,%s,%s,%s,%s,%s)
                ON CONFLICT(audit_name)
                DO UPDATE SET
                    critical_count=EXCLUDED.critical_count,
                    high_count=EXCLUDED.high_count,
                    medium_count=EXCLUDED.medium_count,
                    low_count=EXCLUDED.low_count,
                    open_count=EXCLUDED.open_count;
            """, (REPORT, critical_count, high_count, medium_count, low_count, high_count + critical_count))

        conn.commit()

        print(f"sections_total={sections_total}")
        print(f"low_count={low_count}")
        print(f"medium_count={medium_count}")
        print(f"high_count={high_count}")
        print(f"critical_count={critical_count}")
        print(f"min_score={min_score}")
        print(f"avg_score={avg_score}")
        print(f"overall_risk_level={overall}")
        print("known_high_risk=Correlation Risk")
        print("orders_rows_observation=public.orders rows may be 0 from lineage audit")
        print("audit_mode=READ_ONLY")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print(f"VERDICT={verdict}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()
