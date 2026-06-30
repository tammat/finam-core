#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_CORRELATION_RISK_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_correlation_risk_v1.py \
>/tmp/correlation_risk_audit_v1.out

cat /tmp/correlation_risk_audit_v1.out

grep -q "VERDICT=CORRELATION_RISK_AUDIT_V1_READY" /tmp/correlation_risk_audit_v1.out
grep -q "GROUP|name=ENERGY" /tmp/correlation_risk_audit_v1.out
grep -q "GROUP|name=BANKS" /tmp/correlation_risk_audit_v1.out
grep -q "GROUP|name=OIL_GAS" /tmp/correlation_risk_audit_v1.out
grep -q "correlation_score=" /tmp/correlation_risk_audit_v1.out
grep -q "correlation_risk_level=" /tmp/correlation_risk_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/correlation_risk_audit_v1.out
grep -q "runtime_changed=0" /tmp/correlation_risk_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/correlation_risk_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/correlation_risk_db.out

SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.correlation_risk_audit_report_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='CORRELATION_RISK_AUDIT_V1'
AND section_name='Correlation Risk';

SQL

cat /tmp/correlation_risk_db.out

grep -q "table=READY" /tmp/correlation_risk_db.out
grep -q "scorecard=READY" /tmp/correlation_risk_db.out

echo "VERDICT=TEST_CORRELATION_RISK_AUDIT_V1_OK"
