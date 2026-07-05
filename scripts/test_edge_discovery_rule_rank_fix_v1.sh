#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_DISCOVERY_RULE_RANK_FIX_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS discovery_batch_id TEXT NOT NULL DEFAULT 'DEFAULT';

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS discovery_rank INTEGER NOT NULL DEFAULT 0;

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS discovery_score NUMERIC(12,6) NOT NULL DEFAULT 0;

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS candidate_class TEXT NOT NULL DEFAULT 'UNCLASSIFIED';

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS discovery_formula_version TEXT NOT NULL DEFAULT 'RULE_RANK_V1';
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
INSERT INTO analytics.edge_candidate_v1 (
    observation_uuid,
    research_batch_id,
    research_code,
    strategy_code,
    strategy_version,
    symbol,
    timeframe,
    parameter_hash,
    parameter_json,
    dataset_version,
    raw_edge_score,
    normalized_edge_score,
    confidence_score,
    stability_score,
    candidate_status,
    validation_stage,
    paper_allowed,
    shadow_allowed,
    micro_live_allowed,
    live_allowed,
    discovery_batch_id,
    discovery_rank,
    discovery_score,
    candidate_class,
    discovery_formula_version,
    source_version,
    updated_at
)
SELECT
    observation_uuid,
    research_batch_id,
    research_code,
    strategy_code,
    strategy_version,
    symbol,
    timeframe,
    parameter_hash,
    parameter_json,
    dataset_version,
    raw_edge_score,
    normalized_edge_score,
    confidence_score,
    stability_score,
    'EDGE_CANDIDATE',
    'NOT_STARTED',
    false,
    false,
    false,
    false,
    'EDGE_SPRINT_REVIEW_V1',
    row_number() OVER (
        ORDER BY normalized_edge_score DESC, profit_factor DESC, expectancy DESC
    ),
    normalized_edge_score,
    CASE
        WHEN normalized_edge_score >= 75 THEN 'A'
        WHEN normalized_edge_score >= 60 THEN 'B'
        ELSE 'REJECT'
    END,
    'RULE_RANK_V1',
    'EDGE_DISCOVERY_RULE_RANK_FIX_V1',
    now()
FROM analytics.edge_observation_v1
WHERE trades > 0
  AND normalized_edge_score >= 60
  AND profit_factor > 1
  AND expectancy > 0
ON CONFLICT(observation_uuid) DO UPDATE SET
    normalized_edge_score=EXCLUDED.normalized_edge_score,
    confidence_score=EXCLUDED.confidence_score,
    stability_score=EXCLUDED.stability_score,
    discovery_rank=EXCLUDED.discovery_rank,
    discovery_score=EXCLUDED.discovery_score,
    candidate_class=EXCLUDED.candidate_class,
    source_version='EDGE_DISCOVERY_RULE_RANK_FIX_V1',
    updated_at=now();
SQL

candidates=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE source_version='EDGE_DISCOVERY_RULE_RANK_FIX_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE live_allowed=true OR micro_live_allowed=true;
")

test "$candidates" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
  discovery_rank,
  candidate_class,
  strategy_code,
  symbol,
  timeframe,
  normalized_edge_score,
  confidence_score,
  stability_score,
  candidate_status,
  validation_stage
FROM analytics.edge_candidate_v1
ORDER BY discovery_score DESC, discovery_rank ASC
LIMIT 20;
"

echo "candidates_created_or_updated=$candidates"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_DISCOVERY_RULE_RANK_FIX_V1_READY"
echo "VERDICT=TEST_EDGE_DISCOVERY_RULE_RANK_FIX_V1_OK"
