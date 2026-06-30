#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KILL_SWITCH_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_kill_switch_v1.py \
>/tmp/kill_switch_audit_v1.out

cat /tmp/kill_switch_audit_v1.out

grep -q "VERDICT=KILL_SWITCH_AUDIT_V1_READY" /tmp/kill_switch_audit_v1.out
grep -q "kill_switch_objects_ready=" /tmp/kill_switch_audit_v1.out
grep -q "kill_switch_objects_populated=" /tmp/kill_switch_audit_v1.out
grep -q "kill_switch_objects_missing=" /tmp/kill_switch_audit_v1.out
grep -q "persistent_kill_switch_ready=" /tmp/kill_switch_audit_v1.out
grep -q "risk_events_ready=" /tmp/kill_switch_audit_v1.out
grep -q "governance_ready=" /tmp/kill_switch_audit_v1.out
grep -q "governance_history_ready=" /tmp/kill_switch_audit_v1.out
grep -q "kill_switch_score=" /tmp/kill_switch_audit_v1.out
grep -q "kill_switch_risk_level=" /tmp/kill_switch_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/kill_switch_audit_v1.out
grep -q "runtime_changed=0" /tmp/kill_switch_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/kill_switch_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/kill_switch_audit_db.out

SELECT 'table=' ||
CASE
WHEN to_regclass('warehouse.kill_switch_audit_report_v1') IS NULL
THEN 'MISSING'
ELSE 'READY'
END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='KILL_SWITCH_AUDIT_V1'
AND section_name='Kill Switch';

SQL

cat /tmp/kill_switch_audit_db.out

grep -q "table=READY" /tmp/kill_switch_audit_db.out
grep -q "scorecard=READY" /tmp/kill_switch_audit_db.out

echo "VERDICT=TEST_KILL_SWITCH_AUDIT_V1_OK"
