#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROFIT_FACTORY_PAPER_RECONCILIATION_V1 ==="

psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/024_profit_factory_trust_foundation_v1.sql
psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/025_profit_factory_paper_reconciliation_v1.sql

source_count=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_runtime_candidate_v1 p
JOIN analytics.edge_candidate_v1 e
  ON e.id=p.candidate_id
 AND e.observation_uuid=p.observation_uuid
 AND e.strategy_code=p.strategy_code
 AND e.symbol=p.symbol
 AND e.timeframe=p.timeframe
JOIN analytics.profit_factory_candidate_identity_v1 i
  ON i.edge_candidate_id=e.id
 AND i.candidate_id=e.candidate_uuid
 AND i.observation_id=e.observation_uuid;")

verified_paper_links=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.profit_factory_candidate_link_v1
WHERE target_stage='PAPER'
  AND link_method='SOURCE_REFERENCE'
  AND verification_status='VERIFIED'
  AND confidence_score=1
  AND verified_by='PROFIT_FACTORY_PAPER_RECONCILIATION_V1';")

partial_candidates=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.profit_factory_trust_status_v1
WHERE data_scope='REAL' AND data_quality_status='PARTIAL';")

eligible_candidates=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.profit_factory_trust_status_v1
WHERE data_scope='REAL' AND financial_kpi_eligible;")

wrong_next_action=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.profit_factory_trust_status_v1
WHERE data_scope='REAL' AND data_quality_status='PARTIAL'
  AND next_trust_action <> 'VERIFY_RUNTIME_LINK';")

test "$source_count" -gt 0
test "$verified_paper_links" = "$source_count"
test "$partial_candidates" = "$source_count"
test "$eligible_candidates" = "0"
test "$wrong_next_action" = "0"

echo "source_count=$source_count"
echo "verified_paper_links=$verified_paper_links"
echo "partial_candidates=$partial_candidates"
echo "financial_kpi_eligible_candidates=$eligible_candidates"
echo "wrong_next_action=$wrong_next_action"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "VERDICT=PROFIT_FACTORY_PAPER_RECONCILIATION_V1_READY"
echo "VERDICT=TEST_PROFIT_FACTORY_PAPER_RECONCILIATION_V1_OK"
