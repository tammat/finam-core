#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_REGIME_RISK_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_regime_risk_v1.py \
>/tmp/regime_risk_audit_v1.out

cat /tmp/regime_risk_audit_v1.out

grep -q "VERDICT=REGIME_RISK_AUDIT_V1_READY" /tmp/regime_risk_audit_v1.out
grep -q "REGIME|table=analytics_regime_snapshots_v2" /tmp/regime_risk_audit_v1.out
grep -q "REGIME|table=strategy_regime_matrix" /tmp/regime_risk_audit_v1.out
grep -q "regime_score=" /tmp/regime_risk_audit_v1.out
grep -q "regime_risk_level=" /tmp/regime_risk_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/regime_risk_audit_v1.out
grep -q "runtime_changed=0" /tmp/regime_risk_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/regime_risk_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/regime_risk_db.out

SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.regime_risk_audit_report_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='REGIME_RISK_AUDIT_V1'
AND section_name='Regime Risk';

SQL

cat /tmp/regime_risk_db.out

grep -q "table=READY" /tmp/regime_risk_db.out
grep -q "scorecard=READY" /tmp/regime_risk_db.out

echo "VERDICT=TEST_REGIME_RISK_AUDIT_V1_OK"
