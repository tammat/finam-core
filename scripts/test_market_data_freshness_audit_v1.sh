#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_FRESHNESS_AUDIT_V1 ==="

PYTHONPATH=src python \
src/scripts/research/audit_market_data_freshness_v1.py \
>/tmp/market_data_freshness_audit_v1.out

cat /tmp/market_data_freshness_audit_v1.out

grep -q "VERDICT=MARKET_DATA_FRESHNESS_AUDIT_V1_READY" /tmp/market_data_freshness_audit_v1.out
grep -q "symbols_total=" /tmp/market_data_freshness_audit_v1.out
grep -q "fresh_symbols=" /tmp/market_data_freshness_audit_v1.out
grep -q "normalized_status=" /tmp/market_data_freshness_audit_v1.out
grep -q "pipeline_ready=" /tmp/market_data_freshness_audit_v1.out
grep -q "market_data_freshness_score=" /tmp/market_data_freshness_audit_v1.out
grep -q "market_data_freshness_risk_level=" /tmp/market_data_freshness_audit_v1.out
grep -q "audit_mode=READ_ONLY" /tmp/market_data_freshness_audit_v1.out
grep -q "runtime_changed=0" /tmp/market_data_freshness_audit_v1.out
grep -q "micro_live_allowed=0" /tmp/market_data_freshness_audit_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' >/tmp/market_data_freshness_db.out
SELECT 'table=' ||
CASE WHEN to_regclass('warehouse.market_data_freshness_audit_v1') IS NULL
THEN 'MISSING' ELSE 'READY' END;

SELECT 'scorecard=' || status
FROM warehouse.risk_assessment_scorecard_v1
WHERE audit_name='MARKET_DATA_FRESHNESS_AUDIT_V1'
AND section_name='Market Data Freshness';
SQL

cat /tmp/market_data_freshness_db.out

grep -q "table=READY" /tmp/market_data_freshness_db.out
grep -q "scorecard=READY" /tmp/market_data_freshness_db.out

echo "market_data_freshness_audit=READY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_MARKET_DATA_FRESHNESS_AUDIT_V1_OK"
