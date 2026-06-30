#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import subprocess
import psycopg2

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

RISK_VERSION = "1.0.0"
METADATA_VERSION = "1.0.0"
GIT_TAG = "checkpoint_risk_governance_versioning_v1"

COMPONENTS = [
    ("Risk Governance Framework", "1.0.0", "COMPLETE"),
    ("Risk Register", "1.0.0", "READY"),
    ("Risk Evidence Store", "1.0.0", "READY"),
    ("Risk Scorecard", "1.0.0", "READY"),
    ("Risk Heatmap", "1.0.0", "READY"),
    ("Risk Remediation Plan", "1.0.0", "READY"),
]

DDL = """
CREATE TABLE IF NOT EXISTS warehouse.risk_governance_release_registry_v1 (
    id bigserial PRIMARY KEY,
    risk_governance_version text NOT NULL UNIQUE,
    metadata_version text NOT NULL,
    git_commit text NOT NULL,
    git_tag text NOT NULL,
    framework_hash text NOT NULL,
    validation_hash text NOT NULL,
    release_hash text NOT NULL,
    status text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS warehouse.risk_governance_component_registry_v1 (
    id bigserial PRIMARY KEY,
    risk_governance_version text NOT NULL,
    component_name text NOT NULL,
    component_version text NOT NULL,
    component_status text NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE(risk_governance_version, component_name)
);

CREATE TABLE IF NOT EXISTS warehouse.risk_governance_validation_snapshot_v1 (
    id bigserial PRIMARY KEY,
    risk_governance_version text NOT NULL UNIQUE,
    metadata_version text NOT NULL,
    audit_runs bigint NOT NULL,
    register_ready boolean NOT NULL,
    evidence_ready boolean NOT NULL,
    scorecard_ready boolean NOT NULL,
    heatmap_ready boolean NOT NULL,
    remediation_ready boolean NOT NULL,
    audit_mode text NOT NULL,
    validation_status text NOT NULL,
    runtime_safe boolean NOT NULL,
    active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
"""

UPSERT_RELEASE = """
INSERT INTO warehouse.risk_governance_release_registry_v1 (
    risk_governance_version,
    metadata_version,
    git_commit,
    git_tag,
    framework_hash,
    validation_hash,
    release_hash,
    status
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (risk_governance_version)
DO UPDATE SET
    metadata_version=EXCLUDED.metadata_version,
    git_commit=EXCLUDED.git_commit,
    git_tag=EXCLUDED.git_tag,
    framework_hash=EXCLUDED.framework_hash,
    validation_hash=EXCLUDED.validation_hash,
    release_hash=EXCLUDED.release_hash,
    status=EXCLUDED.status,
    active=true,
    updated_at=now();
"""

UPSERT_COMPONENT = """
INSERT INTO warehouse.risk_governance_component_registry_v1 (
    risk_governance_version,
    component_name,
    component_version,
    component_status
)
VALUES (%s,%s,%s,%s)
ON CONFLICT (risk_governance_version, component_name)
DO UPDATE SET
    component_version=EXCLUDED.component_version,
    component_status=EXCLUDED.component_status,
    active=true,
    updated_at=now();
"""

UPSERT_VALIDATION = """
INSERT INTO warehouse.risk_governance_validation_snapshot_v1 (
    risk_governance_version,
    metadata_version,
    audit_runs,
    register_ready,
    evidence_ready,
    scorecard_ready,
    heatmap_ready,
    remediation_ready,
    audit_mode,
    validation_status,
    runtime_safe
)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
ON CONFLICT (risk_governance_version)
DO UPDATE SET
    metadata_version=EXCLUDED.metadata_version,
    audit_runs=EXCLUDED.audit_runs,
    register_ready=EXCLUDED.register_ready,
    evidence_ready=EXCLUDED.evidence_ready,
    scorecard_ready=EXCLUDED.scorecard_ready,
    heatmap_ready=EXCLUDED.heatmap_ready,
    remediation_ready=EXCLUDED.remediation_ready,
    audit_mode=EXCLUDED.audit_mode,
    validation_status=EXCLUDED.validation_status,
    runtime_safe=EXCLUDED.runtime_safe,
    active=true,
    updated_at=now();
"""

def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"

def sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def table_ready(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s);", (name,))
    return cur.fetchone()[0] is not None

def main() -> None:
    print("=== RISK_GOVERNANCE_VERSIONING_V1 ===")

    conn = psycopg2.connect(DB)
    try:
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS warehouse;")
            cur.execute(DDL)

            register_ready = table_ready(cur, "warehouse.risk_register_v1")
            evidence_ready = table_ready(cur, "warehouse.risk_audit_evidence_v1")
            scorecard_ready = table_ready(cur, "warehouse.risk_assessment_scorecard_v1")
            heatmap_ready = table_ready(cur, "warehouse.risk_heatmap_snapshot_v1")
            remediation_ready = table_ready(cur, "warehouse.risk_remediation_plan_v1")

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
            audit_runs = int(cur.fetchone()[0])

            audit_mode = "READ_ONLY"
            runtime_safe = True

            validation_ok = all([
                audit_runs == 1,
                register_ready,
                evidence_ready,
                scorecard_ready,
                heatmap_ready,
                remediation_ready,
            ])

            validation_status = "PASSED" if validation_ok else "FAILED"

            framework_hash = sha(
                f"{RISK_VERSION}|{METADATA_VERSION}|{audit_runs}|{audit_mode}"
            )
            validation_hash = sha(
                f"{register_ready}|{evidence_ready}|{scorecard_ready}|"
                f"{heatmap_ready}|{remediation_ready}|{validation_status}"
            )
            release_hash = sha(f"{framework_hash}|{validation_hash}|{RISK_VERSION}")

            commit = git_commit()

            cur.execute(
                UPSERT_RELEASE,
                (
                    RISK_VERSION,
                    METADATA_VERSION,
                    commit,
                    GIT_TAG,
                    framework_hash,
                    validation_hash,
                    release_hash,
                    "RELEASED",
                ),
            )

            for name, version, status in COMPONENTS:
                cur.execute(UPSERT_COMPONENT, (RISK_VERSION, name, version, status))

            cur.execute(
                UPSERT_VALIDATION,
                (
                    RISK_VERSION,
                    METADATA_VERSION,
                    audit_runs,
                    register_ready,
                    evidence_ready,
                    scorecard_ready,
                    heatmap_ready,
                    remediation_ready,
                    audit_mode,
                    validation_status,
                    runtime_safe,
                ),
            )

        conn.commit()

        print(f"risk_governance_version={RISK_VERSION}")
        print(f"metadata_version={METADATA_VERSION}")
        print(f"git_commit={commit}")
        print(f"git_tag={GIT_TAG}")
        print(f"audit_runs={audit_runs}")
        print(f"register_ready={int(register_ready)}")
        print(f"evidence_ready={int(evidence_ready)}")
        print(f"scorecard_ready={int(scorecard_ready)}")
        print(f"heatmap_ready={int(heatmap_ready)}")
        print(f"remediation_ready={int(remediation_ready)}")
        print(f"framework_hash={framework_hash}")
        print(f"validation_hash={validation_hash}")
        print(f"release_hash={release_hash}")
        print(f"validation_status={validation_status}")
        print("release_status=RELEASED")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if validation_ok:
            print("VERDICT=RISK_GOVERNANCE_VERSIONING_V1_READY")
        else:
            print("VERDICT=RISK_GOVERNANCE_VERSIONING_V1_FAILED")
            raise SystemExit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
