#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_POSITION_RISK_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_position_risk_v1.py \
>/tmp/position_risk_audit_v1.out

cat /tmp/position_risk_audit_v1.out

grep -q "VERDICT=POSITION_RISK_AUDIT_V1_READY" /tmp/position_risk_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/position_risk_audit_v1.out
grep -q "duplicate_positions=" /tmp/position_risk_audit_v1.out
grep -q "position_rows=" /tmp/position_risk_audit_v1.out
grep -q "runtime_changed=0" /tmp/position_risk_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/position_risk_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/position_risk_db.out

SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.position_risk_audit_report_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='POSITION_RISK_AUDIT_V1'
AND section_name='Position Risk';

SQL

cat /tmp/position_risk_db.out

grep -q "table=READY" /tmp/position_risk_db.out
grep -q "scorecard=READY" /tmp/position_risk_db.out

echo "VERDICT=TEST_POSITION_RISK_AUDIT_V1_OK"
