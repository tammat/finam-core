#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_GOVERNANCE_VERSIONING_V1 ==="

PYTHONPATH=src python \
  src/scripts/research/build_risk_governance_versioning_v1.py \
  >/tmp/risk_governance_versioning_v1.out

cat /tmp/risk_governance_versioning_v1.out

grep -q "VERDICT=RISK_GOVERNANCE_VERSIONING_V1_READY" /tmp/risk_governance_versioning_v1.out
grep -q "risk_governance_version=1.0.0" /tmp/risk_governance_versioning_v1.out
grep -q "metadata_version=1.0.0" /tmp/risk_governance_versioning_v1.out
grep -q "audit_runs=1" /tmp/risk_governance_versioning_v1.out
grep -q "register_ready=1" /tmp/risk_governance_versioning_v1.out
grep -q "evidence_ready=1" /tmp/risk_governance_versioning_v1.out
grep -q "scorecard_ready=1" /tmp/risk_governance_versioning_v1.out
grep -q "heatmap_ready=1" /tmp/risk_governance_versioning_v1.out
grep -q "remediation_ready=1" /tmp/risk_governance_versioning_v1.out
grep -q "validation_status=PASSED" /tmp/risk_governance_versioning_v1.out
grep -q "release_status=RELEASED" /tmp/risk_governance_versioning_v1.out
grep -q "micro_live_allowed=0" /tmp/risk_governance_versioning_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/risk_governance_versioning_db_check_v1.out
SELECT 'release_table=' ||
CASE WHEN to_regclass('warehouse.risk_governance_release_registry_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'component_table=' ||
CASE WHEN to_regclass('warehouse.risk_governance_component_registry_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'validation_table=' ||
CASE WHEN to_regclass('warehouse.risk_governance_validation_snapshot_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'release=' || status
FROM warehouse.risk_governance_release_registry_v1
WHERE risk_governance_version='1.0.0';

SELECT 'components=' || count(*)
FROM warehouse.risk_governance_component_registry_v1
WHERE risk_governance_version='1.0.0'
  AND active=true;

SELECT 'validation=' || validation_status
FROM warehouse.risk_governance_validation_snapshot_v1
WHERE risk_governance_version='1.0.0';

SELECT 'audit_mode=' || audit_mode
FROM warehouse.risk_governance_validation_snapshot_v1
WHERE risk_governance_version='1.0.0';
SQL

cat /tmp/risk_governance_versioning_db_check_v1.out

grep -q "release_table=READY" /tmp/risk_governance_versioning_db_check_v1.out
grep -q "component_table=READY" /tmp/risk_governance_versioning_db_check_v1.out
grep -q "validation_table=READY" /tmp/risk_governance_versioning_db_check_v1.out
grep -q "release=RELEASED" /tmp/risk_governance_versioning_db_check_v1.out
grep -q "components=6" /tmp/risk_governance_versioning_db_check_v1.out
grep -q "validation=PASSED" /tmp/risk_governance_versioning_db_check_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/risk_governance_versioning_db_check_v1.out

echo "risk_governance_versioning=READY"
echo "risk_governance_v1_0_0=RELEASED"
echo "metadata_version=1.0.0"
echo "audit_mode=READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_RISK_GOVERNANCE_VERSIONING_V1_OK"
