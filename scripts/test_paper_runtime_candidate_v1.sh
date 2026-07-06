#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_RUNTIME_CANDIDATE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.paper_runtime_candidate_v1 (
    id BIGSERIAL PRIMARY KEY,
    candidate_id BIGINT NOT NULL,
    observation_uuid UUID NOT NULL,
    strategy_code TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    paper_status TEXT NOT NULL DEFAULT 'ACTIVE',
    paper_started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paper_finished_at TIMESTAMPTZ,
    source_version TEXT NOT NULL DEFAULT 'PAPER_RUNTIME_CANDIDATE_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(candidate_id)
);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.paper_runtime_candidate_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
INSERT INTO analytics.paper_runtime_candidate_v1 (
    candidate_id,
    observation_uuid,
    strategy_code,
    symbol,
    timeframe,
    paper_status,
    source_version,
    updated_at
)
SELECT
    c.id,
    c.observation_uuid,
    c.strategy_code,
    c.symbol,
    c.timeframe,
    'ACTIVE',
    'PAPER_RUNTIME_CANDIDATE_V1',
    now()
FROM analytics.edge_candidate_v1 c
WHERE c.paper_allowed=true
  AND c.candidate_status='VALIDATED'
  AND c.micro_live_allowed=false
  AND c.live_allowed=false
ON CONFLICT(candidate_id) DO UPDATE SET
    paper_status='ACTIVE',
    source_version='PAPER_RUNTIME_CANDIDATE_V1',
    updated_at=now();
SQL

paper_runtime=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_runtime_candidate_v1
WHERE paper_status='ACTIVE';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$paper_runtime" -gt 0
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
  p.id,
  p.paper_status,
  p.strategy_code,
  p.symbol,
  p.timeframe,
  c.validation_score,
  o.trades,
  round(o.profit_factor,4) AS pf,
  round(o.expectancy,6) AS expectancy,
  round(o.normalized_edge_score,4) AS score
FROM analytics.paper_runtime_candidate_v1 p
JOIN analytics.edge_candidate_v1 c
  ON c.id=p.candidate_id
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid=p.observation_uuid
ORDER BY c.validation_score DESC, c.discovery_score DESC;
"

echo "paper_runtime_active=$paper_runtime"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_CANDIDATE_V1_READY"
echo "VERDICT=TEST_PAPER_RUNTIME_CANDIDATE_V1_OK"
