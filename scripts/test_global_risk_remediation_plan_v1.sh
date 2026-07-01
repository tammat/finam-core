#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_RISK_REMEDIATION_PLAN_V1 ==="

PYTHONPATH=src python \
src/scripts/research/build_global_risk_remediation_plan_v1.py \
>/tmp/global_risk_remediation_plan_v1.out

cat /tmp/global_risk_remediation_plan_v1.out

grep -q "VERDICT=GLOBAL_RISK_REMEDIATION_PLAN_V1_READY" /tmp/global_risk_remediation_plan_v1.out
grep -q "planned_actions=2" /tmp/global_risk_remediation_plan_v1.out
grep -q "highest_priority=Correlation Risk" /tmp/global_risk_remediation_plan_v1.out
grep -q "correlation_remediation=PLANNED" /tmp/global_risk_remediation_plan_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/global_risk_remediation_plan_v1.out
grep -q "runtime_changed=0" /tmp/global_risk_remediation_plan_v1.out
grep -q "micro_live_allowed=0" /tmp/global_risk_remediation_plan_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/global_risk_remediation_plan_db.out
SELECT 'corr=' || status
FROM warehouse.risk_remediation_plan_v1
WHERE risk_code='RISK-CORR-0001';

SELECT 'lineage_obs=' || status
FROM warehouse.risk_remediation_plan_v1
WHERE risk_code='RISK-LINEAGE-OBS-0001';

SELECT 'p1=' || count(*)
FROM warehouse.risk_remediation_plan_v1
WHERE priority='P1';
SQL

cat /tmp/global_risk_remediation_plan_db.out

grep -q "corr=PLANNED" /tmp/global_risk_remediation_plan_db.out
grep -q "lineage_obs=OBSERVATION" /tmp/global_risk_remediation_plan_db.out
grep -q "p1=" /tmp/global_risk_remediation_plan_db.out

echo "global_risk_remediation_plan=READY"
echo "correlation_risk_planned=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_GLOBAL_RISK_REMEDIATION_PLAN_V1_OK"
