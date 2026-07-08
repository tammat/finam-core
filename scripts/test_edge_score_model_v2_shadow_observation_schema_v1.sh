#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_SCHEMA_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.edge_score_model_v2_shadow_observation_v1 (
    id BIGSERIAL PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    symbol TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    source_candidate_id TEXT,
    source_layer TEXT NOT NULL DEFAULT 'analytics.edge_score_model_v2',
    observation_layer TEXT NOT NULL DEFAULT 'runtime_shadow_observation',

    edge_score_v2 NUMERIC(12,6) NOT NULL,
    model_verdict TEXT NOT NULL,
    reconciliation_verdict TEXT,
    score_delta NUMERIC(12,6),
    rank_delta INTEGER,

    explain_groups JSONB NOT NULL DEFAULT '[]'::jsonb,

    runtime_seen INTEGER NOT NULL DEFAULT 0,
    signal_seen INTEGER NOT NULL DEFAULT 0,
    order_seen INTEGER NOT NULL DEFAULT 0,
    fill_seen INTEGER NOT NULL DEFAULT 0,

    runtime_allowed INTEGER NOT NULL DEFAULT 0,
    execution_allowed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,

    observation_status TEXT NOT NULL DEFAULT 'OBSERVED_ONLY',
    source_version TEXT NOT NULL DEFAULT 'EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_SCHEMA_V1',

    CHECK (runtime_allowed = 0),
    CHECK (execution_allowed = 0),
    CHECK (micro_live_allowed = 0),
    CHECK (order_seen = 0),
    CHECK (fill_seen = 0)
);

CREATE INDEX IF NOT EXISTS idx_edge_score_v2_shadow_obs_v1_key
ON analytics.edge_score_model_v2_shadow_observation_v1(symbol, strategy_code, timeframe, observed_at DESC);

CREATE INDEX IF NOT EXISTS idx_edge_score_v2_shadow_obs_v1_status
ON analytics.edge_score_model_v2_shadow_observation_v1(observation_status, observed_at DESC);
SQL

cols=$(psql -At -d finam_core -c "
SELECT count(*)
FROM information_schema.columns
WHERE table_schema='analytics'
  AND table_name='edge_score_model_v2_shadow_observation_v1'
  AND column_name IN (
    'symbol',
    'strategy_code',
    'timeframe',
    'edge_score_v2',
    'model_verdict',
    'reconciliation_verdict',
    'explain_groups',
    'runtime_seen',
    'signal_seen',
    'order_seen',
    'fill_seen',
    'runtime_allowed',
    'execution_allowed',
    'micro_live_allowed',
    'observation_status'
  );
")

if [ "$cols" -lt 15 ]; then
  echo "SHADOW_OBSERVATION_SCHEMA_INCOMPLETE=$cols"
  exit 1
fi

unsafe_constraints=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_v1
WHERE runtime_allowed <> 0
   OR execution_allowed <> 0
   OR micro_live_allowed <> 0
   OR order_seen <> 0
   OR fill_seen <> 0;
")

if [ "$unsafe_constraints" != "0" ]; then
  echo "UNSAFE_SHADOW_OBSERVATION_ROWS=$unsafe_constraints"
  exit 1
fi

echo "schema_columns=$cols"
echo "unsafe_rows=0"
echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_SCHEMA_V1_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_SCHEMA_V1_OK"
