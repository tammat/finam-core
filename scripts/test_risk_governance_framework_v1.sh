#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_GOVERNANCE_FRAMEWORK_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/build_risk_governance_framework_v1.py \
  >/tmp/risk_governance_framework_v1.out

cat /tmp/risk_governance_framework_v1.out

grep -q "VERDICT=RISK_GOVERNANCE_FRAMEWORK_V1_READY" /tmp/risk_governance_framework_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/risk_governance_framework_v1.out
grep -q "metadata_version=1.0.0" /tmp/risk_governance_framework_v1.out
grep -q "runtime_changed=0" /tmp/risk_governance_framework_v1.out
grep -q "execution_changed=0" /tmp/risk_governance_framework_v1.out
grep -q "orders_changed=0" /tmp/risk_governance_framework_v1.out
grep -q "fills_changed=0" /tmp/risk_governance_framework_v1.out
grep -q "micro_live_allowed=0" /tmp/risk_governance_framework_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/risk_governance_framework_db_check_v1.out
SELECT 'runs=' ||
CASE WHEN to_regclass('warehouse.risk_audit_runs_v1') IS NULL THEN 'MISSING' ELSE 'READY' END;

SELECT 'register=' ||
CASE WHEN to_regclass('warehouse.risk_register_v1') IS NULL THEN 'MISSING' ELSE 'READY' END;

SELECT 'evidence=' ||
CASE WHEN to_regclass('warehouse.risk_audit_evidence_v1') IS NULL THEN 'MISSING' ELSE 'READY' END;

SELECT 'scorecard=' ||
CASE WHEN to_regclass('warehouse.risk_assessment_scorecard_v1') IS NULL THEN 'MISSING' ELSE 'READY' END;

SELECT 'heatmap=' ||
CASE WHEN to_regclass('warehouse.risk_heatmap_snapshot_v1') IS NULL THEN 'MISSING' ELSE 'READY' END;

SELECT 'remediation=' ||
CASE WHEN to_regclass('warehouse.risk_remediation_plan_v1') IS NULL THEN 'MISSING' ELSE 'READY' END;

SELECT 'audit=' || status
FROM warehouse.risk_audit_runs_v1
WHERE audit_name='GLOBAL_RISK_FORENSIC_AUDIT_V1';

SELECT 'mode=' || audit_mode
FROM warehouse.risk_audit_runs_v1
WHERE audit_name='GLOBAL_RISK_FORENSIC_AUDIT_V1';

SELECT 'metadata_version=' || metadata_version
FROM warehouse.risk_audit_runs_v1
WHERE audit_name='GLOBAL_RISK_FORENSIC_AUDIT_V1';
SQL

cat /tmp/risk_governance_framework_db_check_v1.out

grep -q "runs=READY" /tmp/risk_governance_framework_db_check_v1.out
grep -q "register=READY" /tmp/risk_governance_framework_db_check_v1.out
grep -q "evidence=READY" /tmp/risk_governance_framework_db_check_v1.out
grep -q "scorecard=READY" /tmp/risk_governance_framework_db_check_v1.out
grep -q "heatmap=READY" /tmp/risk_governance_framework_db_check_v1.out
grep -q "remediation=READY" /tmp/risk_governance_framework_db_check_v1.out
grep -q "audit=STARTED" /tmp/risk_governance_framework_db_check_v1.out
grep -q "mode=READ_ONLY" /tmp/risk_governance_framework_db_check_v1.out
grep -q "metadata_version=1.0.0" /tmp/risk_governance_framework_db_check_v1.out

echo "risk_governance_framework=READY"
echo "risk_register=READY"
echo "risk_evidence_store=READY"
echo "risk_scorecard=READY"
echo "risk_heatmap=READY"
echo "risk_remediation_plan=READY"
echo "audit_mode=READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_RISK_GOVERNANCE_FRAMEWORK_V1_OK"
