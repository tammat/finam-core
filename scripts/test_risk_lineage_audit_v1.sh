#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_LINEAGE_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_risk_lineage_v1.py \
>/tmp/risk_lineage_audit_v1.out

cat /tmp/risk_lineage_audit_v1.out

grep -q "VERDICT=RISK_LINEAGE_AUDIT_V1_READY" /tmp/risk_lineage_audit_v1.out
grep -q "lineage_steps_total=" /tmp/risk_lineage_audit_v1.out
grep -q "lineage_objects_ready=" /tmp/risk_lineage_audit_v1.out
grep -q "lineage_objects_populated=" /tmp/risk_lineage_audit_v1.out
grep -q "lineage_score=" /tmp/risk_lineage_audit_v1.out
grep -q "lineage_risk_level=" /tmp/risk_lineage_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/risk_lineage_audit_v1.out
grep -q "runtime_changed=0" /tmp/risk_lineage_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/risk_lineage_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/risk_lineage_db.out

SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.risk_lineage_audit_report_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='RISK_LINEAGE_AUDIT_V1'
AND section_name='Risk Lineage';

SQL

cat /tmp/risk_lineage_db.out

grep -q "table=READY" /tmp/risk_lineage_db.out
grep -q "scorecard=READY" /tmp/risk_lineage_db.out

echo "VERDICT=TEST_RISK_LINEAGE_AUDIT_V1_OK"
