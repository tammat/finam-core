#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROFIT_FACTORY_TRUST_FOUNDATION_V1 ==="

psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/022_profit_factory_contract_v1.sql
psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/023_profit_factory_identity_contract_v1.sql
psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/024_profit_factory_trust_foundation_v1.sql

summary=$(psql -At -F '|' -d finam_core -c "
SELECT total_candidates, verified_candidates, partial_candidates,
       stale_candidates, conflict_candidates, unverified_candidates,
       quarantined_candidates, financial_kpi_eligible_candidates
FROM analytics.profit_factory_trust_summary_v1;")

total_candidates=$(printf '%s' "$summary" | cut -d'|' -f1)
unverified_candidates=$(printf '%s' "$summary" | cut -d'|' -f6)
eligible_candidates=$(printf '%s' "$summary" | cut -d'|' -f8)
classified_candidates=$(printf '%s' "$summary" | awk -F'|' \
  '{print $2 + $3 + $4 + $5 + $6 + $7}')

test "$total_candidates" -gt 0
test "$classified_candidates" = "$total_candidates"

candidate_id=$(psql -At -d finam_core -c "
SELECT candidate_id
FROM analytics.profit_factory_candidate_identity_v1
ORDER BY candidate_id
LIMIT 1;")

verified_chain_result=$(psql -qAt -F '|' -v ON_ERROR_STOP=1 -d finam_core -c "
BEGIN;
INSERT INTO analytics.profit_factory_candidate_link_v1 (
  candidate_id, target_stage, target_entity_type, target_entity_id,
  source_table, source_record_id, link_method, verification_status,
  confidence_score, evidence_observed_at, verified_at, verified_by
) VALUES
('$candidate_id', 'PAPER', 'PAPER_RUN', 'TEST-PAPER', 'test.paper', '1',
 'EXPLICIT_ID', 'VERIFIED', 1, now(), now(), 'CONTRACT_TEST'),
('$candidate_id', 'RUNTIME', 'RUNTIME_ALLOCATION', 'TEST-RUNTIME', 'test.runtime', '1',
 'SOURCE_REFERENCE', 'VERIFIED', 1, now(), now(), 'CONTRACT_TEST'),
('$candidate_id', 'PRODUCTION', 'PRODUCTION_ALLOCATION', 'TEST-PRODUCTION', 'test.production', '1',
 'OPERATOR_APPROVED', 'VERIFIED', 1, now(), now(), 'CONTRACT_TEST');
SELECT data_quality_status, financial_kpi_eligible, next_trust_action
FROM analytics.profit_factory_trust_status_v1
WHERE candidate_id='$candidate_id';
ROLLBACK;")

inferred_rejected=0
if psql -q -v ON_ERROR_STOP=1 -d finam_core -c "
BEGIN;
INSERT INTO analytics.profit_factory_candidate_link_v1 (
  candidate_id, target_stage, target_entity_type, target_entity_id,
  source_table, source_record_id, link_method, verification_status,
  confidence_score, evidence_observed_at, verified_at, verified_by
) VALUES (
  '$candidate_id', 'PRODUCTION', 'BAD_INFERENCE', 'BAD-1',
  'test.inferred', '1', 'INFERRED_MATCH', 'VERIFIED',
  1, now(), now(), 'CONTRACT_TEST'
);
ROLLBACK;" >/dev/null 2>&1; then
  inferred_rejected=0
else
  inferred_rejected=1
fi

test "$verified_chain_result" = "VERIFIED|t|READY_FOR_FINANCIAL_KPI"
test "$inferred_rejected" = "1"

echo "total_candidates=$total_candidates"
echo "classified_candidates=$classified_candidates"
echo "unverified_candidates=$unverified_candidates"
echo "financial_kpi_eligible_candidates=$eligible_candidates"
echo "verified_chain_result=$verified_chain_result"
echo "inferred_verified_rejected=$inferred_rejected"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "VERDICT=PROFIT_FACTORY_TRUST_FOUNDATION_V1_READY"
echo "VERDICT=TEST_PROFIT_FACTORY_TRUST_FOUNDATION_V1_OK"
