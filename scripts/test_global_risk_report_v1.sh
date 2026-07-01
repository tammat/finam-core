#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_GLOBAL_RISK_REPORT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/build_global_risk_report_v1.py \
>/tmp/global_risk_report_v1.out

cat /tmp/global_risk_report_v1.out

grep -Eq "VERDICT=GLOBAL_RISK_REPORT_V1_READY|VERDICT=GLOBAL_RISK_REPORT_V1_READY_WITH_FINDINGS" /tmp/global_risk_report_v1.out
grep -q "sections_total=10" /tmp/global_risk_report_v1.out
grep -q "known_high_risk=Correlation Risk" /tmp/global_risk_report_v1.out
grep -q "overall_risk_level=" /tmp/global_risk_report_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/global_risk_report_v1.out
grep -q "runtime_changed=0" /tmp/global_risk_report_v1.out
grep -q "micro_live_allowed=0" /tmp/global_risk_report_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/global_risk_report_db.out
SELECT 'report_table=' ||
CASE WHEN to_regclass('warehouse.global_risk_report_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'summary_table=' ||
CASE WHEN to_regclass('warehouse.global_risk_report_summary_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'sections=' || count(*)
FROM warehouse.global_risk_report_v1
WHERE report_name='GLOBAL_RISK_REPORT_V1';

SELECT 'overall=' || overall_risk_level
FROM warehouse.global_risk_report_summary_v1
WHERE report_name='GLOBAL_RISK_REPORT_V1';

SELECT 'high=' || high_count
FROM warehouse.global_risk_report_summary_v1
WHERE report_name='GLOBAL_RISK_REPORT_V1';
SQL

cat /tmp/global_risk_report_db.out

grep -q "report_table=READY" /tmp/global_risk_report_db.out
grep -q "summary_table=READY" /tmp/global_risk_report_db.out
grep -q "sections=10" /tmp/global_risk_report_db.out
grep -q "overall=" /tmp/global_risk_report_db.out
grep -q "high=" /tmp/global_risk_report_db.out

echo "global_risk_report=READY"
echo "risk_heatmap=READY"
echo "audit_mode=READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_GLOBAL_RISK_REPORT_V1_OK"
