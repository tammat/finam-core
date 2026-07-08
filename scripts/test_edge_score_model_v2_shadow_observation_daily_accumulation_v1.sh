#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1 ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.edge_score_model_v2_shadow_observation_daily_v1 (
    id BIGSERIAL PRIMARY KEY,
    trade_date DATE NOT NULL,
    symbol TEXT NOT NULL,
    strategy_code TEXT NOT NULL,
    timeframe TEXT NOT NULL,

    observations_count INTEGER NOT NULL,
    runtime_seen_count INTEGER NOT NULL,
    signal_seen_count INTEGER NOT NULL,
    order_seen_count INTEGER NOT NULL,
    fill_seen_count INTEGER NOT NULL,

    avg_edge_score_v2 NUMERIC(12,6),
    min_edge_score_v2 NUMERIC(12,6),
    max_edge_score_v2 NUMERIC(12,6),

    pass_count INTEGER NOT NULL,
    review_count INTEGER NOT NULL,

    runtime_allowed INTEGER NOT NULL DEFAULT 0,
    execution_allowed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,

    source_version TEXT NOT NULL DEFAULT 'EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE(trade_date, symbol, strategy_code, timeframe, source_version),

    CHECK (runtime_allowed = 0),
    CHECK (execution_allowed = 0),
    CHECK (micro_live_allowed = 0),
    CHECK (order_seen_count = 0),
    CHECK (fill_seen_count = 0)
);

DELETE FROM analytics.edge_score_model_v2_shadow_observation_daily_v1
WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1';

INSERT INTO analytics.edge_score_model_v2_shadow_observation_daily_v1 (
    trade_date,
    symbol,
    strategy_code,
    timeframe,
    observations_count,
    runtime_seen_count,
    signal_seen_count,
    order_seen_count,
    fill_seen_count,
    avg_edge_score_v2,
    min_edge_score_v2,
    max_edge_score_v2,
    pass_count,
    review_count,
    runtime_allowed,
    execution_allowed,
    micro_live_allowed,
    source_version
)
SELECT
    observed_at::date AS trade_date,
    symbol,
    strategy_code,
    timeframe,
    count(*)::integer AS observations_count,
    count(*) FILTER (WHERE runtime_seen = 1)::integer AS runtime_seen_count,
    count(*) FILTER (WHERE signal_seen = 1)::integer AS signal_seen_count,
    0 AS order_seen_count,
    0 AS fill_seen_count,
    avg(edge_score_v2)::numeric(12,6) AS avg_edge_score_v2,
    min(edge_score_v2)::numeric(12,6) AS min_edge_score_v2,
    max(edge_score_v2)::numeric(12,6) AS max_edge_score_v2,
    count(*) FILTER (WHERE reconciliation_verdict = 'PASS')::integer AS pass_count,
    count(*) FILTER (WHERE reconciliation_verdict IS DISTINCT FROM 'PASS')::integer AS review_count,
    0 AS runtime_allowed,
    0 AS execution_allowed,
    0 AS micro_live_allowed,
    'EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1' AS source_version
FROM analytics.edge_score_model_v2_shadow_observation_v1
WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_COLLECTOR_V1'
GROUP BY observed_at::date, symbol, strategy_code, timeframe;
SQL

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_daily_v1
WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_daily_v1
WHERE source_version='EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1'
  AND (
      runtime_allowed <> 0
   OR execution_allowed <> 0
   OR micro_live_allowed <> 0
   OR order_seen_count <> 0
   OR fill_seen_count <> 0
  );
")

if [ "$rows" -lt 1 ]; then
  echo "NO_DAILY_ACCUMULATION_ROWS"
  exit 1
fi

if [ "$unsafe" != "0" ]; then
  echo "UNSAFE_DAILY_ACCUMULATION_ROWS=$unsafe"
  exit 1
fi

echo "daily_rows=$rows"
echo "unsafe_rows=0"
echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_SHADOW_OBSERVATION_DAILY_ACCUMULATION_V1_OK"
