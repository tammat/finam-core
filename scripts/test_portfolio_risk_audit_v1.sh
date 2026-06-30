#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PORTFOLIO_RISK_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_portfolio_risk_v1.py \
>/tmp/portfolio_risk_audit_v1.out

cat /tmp/portfolio_risk_audit_v1.out

grep -q "VERDICT=PORTFOLIO_RISK_AUDIT_V1_READY" /tmp/portfolio_risk_audit_v1.out
grep -q "portfolio_score=" /tmp/portfolio_risk_audit_v1.out
grep -q "portfolio_risk_level=" /tmp/portfolio_risk_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/portfolio_risk_audit_v1.out
grep -q "runtime_changed=0" /tmp/portfolio_risk_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/portfolio_risk_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/portfolio_risk_db.out

SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.portfolio_risk_audit_report_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='PORTFOLIO_RISK_AUDIT_V1'
AND section_name='Portfolio Risk';

SQL

cat /tmp/portfolio_risk_db.out

grep -q "table=READY" /tmp/portfolio_risk_db.out
grep -q "scorecard=READY" /tmp/portfolio_risk_db.out

echo "VERDICT=TEST_PORTFOLIO_RISK_AUDIT_V1_OK"
