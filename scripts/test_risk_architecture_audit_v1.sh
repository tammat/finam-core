#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_ARCHITECTURE_AUDIT_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/audit_risk_architecture_v1.py \
  >/tmp/risk_architecture_audit_v1.out

cat /tmp/risk_architecture_audit_v1.out

grep -q "VERDICT=RISK_ARCHITECTURE_AUDIT_V1_READY" /tmp/risk_architecture_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/risk_architecture_audit_v1.out
grep -q "risk_table_ready=" /tmp/risk_architecture_audit_v1.out
grep -q "execution_layer_ready=" /tmp/risk_architecture_audit_v1.out
grep -q "broker_layer_ready=" /tmp/risk_architecture_audit_v1.out
grep -q "kill_switch_ready=" /tmp/risk_architecture_audit_v1.out
grep -q "portfolio_risk_ready=" /tmp/risk_architecture_audit_v1.out
grep -q "architecture_score=" /tmp/risk_architecture_audit_v1.out
grep -q "architecture_risk_level=" /tmp/risk_architecture_audit_v1.out
grep -q "classification_changed=0" /tmp/risk_architecture_audit_v1.out
grep -q "runtime_changed=0" /tmp/risk_architecture_audit_v1.out
grep -q "execution_changed=0" /tmp/risk_architecture_audit_v1.out
grep -q "orders_changed=0" /tmp/risk_architecture_audit_v1.out
grep -q "fills_changed=0" /tmp/risk_architecture_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/risk_architecture_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/risk_architecture_audit_db_check_v1.out
SELECT 'report_table=' ||
CASE WHEN to_regclass('warehouse.risk_architecture_audit_report_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'evidence_rows=' || count(*)
FROM warehouse.risk_audit_evidence_v1
WHERE audit_name='RISK_ARCHITECTURE_AUDIT_V1';

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='RISK_ARCHITECTURE_AUDIT_V1'
  AND section_name='Architecture';

SELECT 'risk_level=' || risk_level
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='RISK_ARCHITECTURE_AUDIT_V1'
  AND section_name='Architecture';
SQL

cat /tmp/risk_architecture_audit_db_check_v1.out

grep -q "report_table=READY" /tmp/risk_architecture_audit_db_check_v1.out
grep -q "evidence_rows=" /tmp/risk_architecture_audit_db_check_v1.out
grep -q "scorecard=READY" /tmp/risk_architecture_audit_db_check_v1.out
grep -q "risk_level=" /tmp/risk_architecture_audit_db_check_v1.out

echo "risk_architecture_audit=READY"
echo "risk_evidence_saved=READY"
echo "risk_scorecard_saved=READY"
echo "audit_mode=READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_RISK_ARCHITECTURE_AUDIT_V1_OK"
