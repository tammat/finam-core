#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RUNTIME_RECOVERY_RISK_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_runtime_recovery_risk_v1.py \
>/tmp/runtime_recovery_risk_audit_v1.out

cat /tmp/runtime_recovery_risk_audit_v1.out

grep -q "VERDICT=RUNTIME_RECOVERY_RISK_AUDIT_V1_READY" /tmp/runtime_recovery_risk_audit_v1.out
grep -q "recovery_score=" /tmp/runtime_recovery_risk_audit_v1.out
grep -q "recovery_risk_level=" /tmp/runtime_recovery_risk_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/runtime_recovery_risk_audit_v1.out
grep -q "runtime_changed=0" /tmp/runtime_recovery_risk_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/runtime_recovery_risk_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/runtime_recovery_db.out
SELECT 'table=' ||
CASE WHEN to_regclass('warehouse.runtime_recovery_risk_audit_report_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='RUNTIME_RECOVERY_RISK_AUDIT_V1'
AND section_name='Runtime Recovery';
SQL

cat /tmp/runtime_recovery_db.out

grep -q "table=READY" /tmp/runtime_recovery_db.out
grep -q "scorecard=READY" /tmp/runtime_recovery_db.out

echo "VERDICT=TEST_RUNTIME_RECOVERY_RISK_AUDIT_V1_OK"
