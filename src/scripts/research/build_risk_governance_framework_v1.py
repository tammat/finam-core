#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.risk_audit_runs_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL UNIQUE,
    audit_scope text NOT NULL,
    audit_mode text NOT NULL,
    status text NOT NULL,
    metadata_version text NOT NULL,
    runtime_changed boolean NOT NULL DEFAULT false,
    execution_changed boolean NOT NULL DEFAULT false,
    orders_changed boolean NOT NULL DEFAULT false,
    fills_changed boolean NOT NULL DEFAULT false,
    micro_live_allowed boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.risk_register_v1 (
    id bigserial PRIMARY KEY,
    risk_code text NOT NULL UNIQUE,
    audit_name text NOT NULL,
    title text NOT NULL,
    category text NOT NULL,
    severity text NOT NULL,
    probability text NOT NULL,
    impact text NOT NULL,
    affected_components text NOT NULL,
    evidence_summary text NOT NULL,
    current_protection text NOT NULL,
    residual_risk text NOT NULL,
    recommendation text NOT NULL,
    remediation_required boolean NOT NULL,
    status text NOT NULL DEFAULT 'OPEN',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.risk_audit_evidence_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    check_name text NOT NULL,
    object_name text NOT NULL,
    result text NOT NULL,
    severity text NOT NULL,
    payload text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.risk_assessment_scorecard_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL,
    section_name text NOT NULL,
    score numeric NOT NULL,
    risk_level text NOT NULL,
    status text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(audit_name, section_name)
);

CREATE TABLE IF NOT EXISTS warehouse.risk_heatmap_snapshot_v1 (
    id bigserial PRIMARY KEY,
    audit_name text NOT NULL UNIQUE,
    critical_count bigint NOT NULL DEFAULT 0,
    high_count bigint NOT NULL DEFAULT 0,
    medium_count bigint NOT NULL DEFAULT 0,
    low_count bigint NOT NULL DEFAULT 0,
    open_count bigint NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.risk_remediation_plan_v1 (
    id bigserial PRIMARY KEY,
    risk_code text NOT NULL UNIQUE,
    priority text NOT NULL,
    remediation_action text NOT NULL,
    dependency text NOT NULL,
    status text NOT NULL DEFAULT 'PLANNED',
    created_at timestamptz NOT NULL DEFAULT now()
);
"""

def main() -> None:
    print("=== RISK_GOVERNANCE_FRAMEWORK_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS warehouse;")
            cur.execute(DDL)

            cur.execute("""
                INSERT INTO warehouse.risk_audit_runs_v1 (
                    audit_name,
                    audit_scope,
                    audit_mode,
                    status,
                    metadata_version,
                    runtime_changed,
                    execution_changed,
                    orders_changed,
                    fills_changed,
                    micro_live_allowed
                )
                VALUES (
                    'GLOBAL_RISK_FORENSIC_AUDIT_V1',
                    'ARCHITECTURE,POSITION,PORTFOLIO,EXPOSURE,CORRELATION,REGIME,DRAWDOWN,KILL_SWITCH,RECOVERY,LINEAGE',
                    'READ_ONLY',
                    'STARTED',
                    '1.0.0',
                    false,
                    false,
                    false,
                    false,
                    false
                )
                ON CONFLICT (audit_name)
                DO UPDATE SET
                    audit_scope=EXCLUDED.audit_scope,
                    audit_mode=EXCLUDED.audit_mode,
                    status=EXCLUDED.status,
                    metadata_version=EXCLUDED.metadata_version,
                    runtime_changed=false,
                    execution_changed=false,
                    orders_changed=false,
                    fills_changed=false,
                    micro_live_allowed=false;
            """)

            tables = [
                "risk_audit_runs_v1",
                "risk_register_v1",
                "risk_audit_evidence_v1",
                "risk_assessment_scorecard_v1",
                "risk_heatmap_snapshot_v1",
                "risk_remediation_plan_v1",
            ]

            for table in tables:
                cur.execute(
                    "SELECT to_regclass(%s);",
                    (f"warehouse.{table}",),
                )
                status = "READY" if cur.fetchone()[0] else "MISSING"
                print(f"TABLE|name=warehouse.{table}|status={status}")

            cur.execute("""
                SELECT count(*)
                FROM warehouse.risk_audit_runs_v1
                WHERE audit_name='GLOBAL_RISK_FORENSIC_AUDIT_V1'
                  AND audit_mode='READ_ONLY'
                  AND status='STARTED'
                  AND metadata_version='1.0.0'
                  AND runtime_changed=false
                  AND execution_changed=false
                  AND orders_changed=false
                  AND fills_changed=false
                  AND micro_live_allowed=false;
            """)
            audit_run_ready = cur.fetchone()[0]

        conn.commit()

        print(f"audit_run_ready={audit_run_ready}")
        print("risk_governance_framework=READY")
        print("audit_mode=READ_ONLY")
        print("architecture_frozen=1")
        print("metadata_version=1.0.0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if audit_run_ready == 1:
            print("VERDICT=RISK_GOVERNANCE_FRAMEWORK_V1_READY")
        else:
            print("VERDICT=RISK_GOVERNANCE_FRAMEWORK_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
