#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DRAWDOWN_RISK_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_drawdown_risk_v1.py \
>/tmp/drawdown_risk_audit_v1.out

cat /tmp/drawdown_risk_audit_v1.out

grep -q "VERDICT=DRAWDOWN_RISK_AUDIT_V1_READY" /tmp/drawdown_risk_audit_v1.out
grep -q "drawdown_objects_ready=" /tmp/drawdown_risk_audit_v1.out
grep -q "drawdown_objects_populated=" /tmp/drawdown_risk_audit_v1.out
grep -q "single_source_ready=" /tmp/drawdown_risk_audit_v1.out
grep -q "portfolio_state_ready=" /tmp/drawdown_risk_audit_v1.out
grep -q "live_accumulation_ready=" /tmp/drawdown_risk_audit_v1.out
grep -q "drawdown_score=" /tmp/drawdown_risk_audit_v1.out
grep -q "drawdown_risk_level=" /tmp/drawdown_risk_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/drawdown_risk_audit_v1.out
grep -q "runtime_changed=0" /tmp/drawdown_risk_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/drawdown_risk_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/drawdown_risk_db.out

SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.drawdown_risk_audit_report_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='DRAWDOWN_RISK_AUDIT_V1'
AND section_name='Drawdown Risk';

SQL

cat /tmp/drawdown_risk_db.out

grep -q "table=READY" /tmp/drawdown_risk_db.out
grep -q "scorecard=READY" /tmp/drawdown_risk_db.out

echo "VERDICT=TEST_DRAWDOWN_RISK_AUDIT_V1_OK"
