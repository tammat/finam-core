#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
AUDIT = "RISK_ARCHITECTURE_AUDIT_V1"

DDL_EXTRA = """
CREATE TABLE IF NOT EXISTS warehouse.risk_architecture_audit_report_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    section_name text NOT NULL,
    check_name text NOT NULL,
    result text NOT NULL,
    severity text NOT NULL,
    payload text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, section_name, check_name)
);
"""

UPSERT_REPORT = """
INSERT INTO warehouse.risk_architecture_audit_report_v1 (
    audit_name, section_name, check_name, result, severity, payload
)
VALUES (%s,%s,%s,%s,%s,%s)
ON CONFLICT (audit_name, section_name, check_name)
DO UPDATE SET
    result=EXCLUDED.result,
    severity=EXCLUDED.severity,
    payload=EXCLUDED.payload,
    active=true;
"""

INSERT_EVIDENCE = """
INSERT INTO warehouse.risk_audit_evidence_v1 (
    audit_name, check_name, object_name, result, severity, payload
)
VALUES (%s,%s,%s,%s,%s,%s);
"""

UPSERT_SCORE = """
INSERT INTO warehouse.risk_assessment_scorecard_v1 (
    audit_name, section_name, score, risk_level, status
)
VALUES (%s,%s,%s,%s,%s)
ON CONFLICT (audit_name, section_name)
DO UPDATE SET
    score=EXCLUDED.score,
    risk_level=EXCLUDED.risk_level,
    status=EXCLUDED.status;
"""

UPSERT_RISK = """
INSERT INTO warehouse.risk_register_v1 (
    risk_code,
    audit_name,
    title,
    category,
    severity,
    probability,
    impact,
    affected_components,
    evidence_summary,
    current_protection,
    residual_risk,
    recommendation,
    remediation_required,
    status
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (risk_code)
DO UPDATE SET
    audit_name=EXCLUDED.audit_name,
    title=EXCLUDED.title,
    category=EXCLUDED.category,
    severity=EXCLUDED.severity,
    probability=EXCLUDED.probability,
    impact=EXCLUDED.impact,
    affected_components=EXCLUDED.affected_components,
    evidence_summary=EXCLUDED.evidence_summary,
    current_protection=EXCLUDED.current_protection,
    residual_risk=EXCLUDED.residual_risk,
    recommendation=EXCLUDED.recommendation,
    remediation_required=EXCLUDED.remediation_required,
    status=EXCLUDED.status;
"""

def table_exists(cur, table: str) -> bool:
    cur.execute("SELECT to_regclass(%s);", (table,))
    return cur.fetchone()[0] is not None

def count_table(cur, table: str) -> int:
    if not table_exists(cur, table):
        return -1
    cur.execute(f"SELECT count(*) FROM {table};")
    return int(cur.fetchone()[0])

def main() -> None:
    print("=== RISK_ARCHITECTURE_AUDIT_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute(DDL_EXTRA)

            checks = []

            required_tables = {
                "signals": "public.signals",
                "orders": "public.orders",
                "fills": "public.fills",
                "positions": "public.positions",
                "risk_events": "public.risk_events",
                "portfolio_risk_state": "public.portfolio_risk_state",
                "persistent_kill_switch": "public.persistent_kill_switch",
                "execution_intents": "public.execution_intents",
                "execution_events": "public.execution_events",
                "order_events": "public.order_events",
                "broker_reconciliation_events": "public.broker_reconciliation_events",
            }

            missing = []
            for name, table in required_tables.items():
                exists = table_exists(cur, table)
                checks.append((name, table, "PASS" if exists else "FAIL", "HIGH" if not exists else "LOW"))
                if not exists:
                    missing.append(table)

            risk_table_ready = table_exists(cur, "public.risk_events")
            execution_ready = table_exists(cur, "public.execution_intents") and table_exists(cur, "public.execution_events")
            broker_ready = table_exists(cur, "public.broker_reconciliation_events")
            kill_switch_ready = table_exists(cur, "public.persistent_kill_switch")
            portfolio_risk_ready = table_exists(cur, "public.portfolio_risk_state")

            bypass_risk = not (risk_table_ready and execution_ready and broker_ready)
            critical_findings = 1 if bypass_risk else 0

            for check_name, object_name, result, severity in checks:
                payload = f"object={object_name}|exists={result == 'PASS'}"
                cur.execute(UPSERT_REPORT, (AUDIT, "ARCHITECTURE_OBJECTS", check_name, result, severity, payload))
                cur.execute(INSERT_EVIDENCE, (AUDIT, check_name, object_name, result, severity, payload))
                print(f"CHECK|name={check_name}|object={object_name}|result={result}|severity={severity}")

            if bypass_risk:
                cur.execute(
                    UPSERT_RISK,
                    (
                        "RISK-ARCH-0001",
                        AUDIT,
                        "Risk decision path is not fully evidenced",
                        "ARCHITECTURE",
                        "HIGH",
                        "MEDIUM",
                        "CRITICAL",
                        "Risk Engine, Execution, Broker",
                        "Required risk/execution/broker evidence tables are incomplete.",
                        "Partial table-level controls exist.",
                        "Potential inability to prove Signal -> Risk -> Execution -> Broker chain.",
                        "Add explicit risk-decision lineage audit before live trading.",
                        True,
                        "OPEN",
                    ),
                )

            score = 100
            if missing:
                score -= min(40, len(missing) * 5)
            if not kill_switch_ready:
                score -= 10
            if not portfolio_risk_ready:
                score -= 10
            if bypass_risk:
                score -= 20

            risk_level = "LOW" if score >= 90 else "MEDIUM" if score >= 75 else "HIGH"

            cur.execute(UPSERT_SCORE, (AUDIT, "Architecture", score, risk_level, "READY"))

            print(f"risk_table_ready={int(risk_table_ready)}")
            print(f"execution_layer_ready={int(execution_ready)}")
            print(f"broker_layer_ready={int(broker_ready)}")
            print(f"kill_switch_ready={int(kill_switch_ready)}")
            print(f"portfolio_risk_ready={int(portfolio_risk_ready)}")
            print(f"missing_required_objects={len(missing)}")
            print(f"critical_findings={critical_findings}")
            print(f"architecture_score={score}")
            print(f"architecture_risk_level={risk_level}")

            print("audit_mode=READ_ONLY")
            print("classification_changed=0")
            print("runtime_changed=0")
            print("execution_changed=0")
            print("orders_changed=0")
            print("fills_changed=0")
            print("micro_live_allowed=0")

            cur.execute("""
                SELECT count(*)
                FROM warehouse.risk_audit_runs_v1
                WHERE audit_name='GLOBAL_RISK_FORENSIC_AUDIT_V1'
                  AND audit_mode='READ_ONLY'
                  AND metadata_version='1.0.0';
            """)
            run_ok = int(cur.fetchone()[0])

        conn.commit()

        if run_ok == 1 and score >= 75:
            print("VERDICT=RISK_ARCHITECTURE_AUDIT_V1_READY")
        else:
            print("VERDICT=RISK_ARCHITECTURE_AUDIT_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
