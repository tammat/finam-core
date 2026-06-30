#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EXPOSURE_RISK_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_exposure_risk_v1.py \
>/tmp/exposure_risk_audit_v1.out

cat /tmp/exposure_risk_audit_v1.out

grep -q "VERDICT=EXPOSURE_RISK_AUDIT_V1_READY" /tmp/exposure_risk_audit_v1.out
grep -q "gross_exposure=" /tmp/exposure_risk_audit_v1.out
grep -q "opposite_exposure=" /tmp/exposure_risk_audit_v1.out
grep -q "exposure_score=" /tmp/exposure_risk_audit_v1.out
grep -q "exposure_risk_level=" /tmp/exposure_risk_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/exposure_risk_audit_v1.out
grep -q "runtime_changed=0" /tmp/exposure_risk_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/exposure_risk_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/exposure_risk_db.out

SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.exposure_risk_audit_report_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='EXPOSURE_RISK_AUDIT_V1'
AND section_name='Exposure Risk';

SQL

cat /tmp/exposure_risk_db.out

grep -q "table=READY" /tmp/exposure_risk_db.out
grep -q "scorecard=READY" /tmp/exposure_risk_db.out

echo "VERDICT=TEST_EXPOSURE_RISK_AUDIT_V1_OK"
