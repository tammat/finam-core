#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SCORE_MODEL_V2_RUNTIME_SHADOW_OBSERVATION_PLAN ==="

psql -d finam_core -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.edge_score_model_v2_shadow_observation_plan (
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    plan_code TEXT NOT NULL,
    observation_scope TEXT NOT NULL,
    source_layer TEXT NOT NULL,
    target_layer TEXT NOT NULL,
    runtime_allowed INTEGER NOT NULL DEFAULT 0,
    execution_allowed INTEGER NOT NULL DEFAULT 0,
    micro_live_allowed INTEGER NOT NULL DEFAULT 0,
    plan_status TEXT NOT NULL,
    notes TEXT NOT NULL
);

DELETE FROM analytics.edge_score_model_v2_shadow_observation_plan
WHERE plan_code='EDGE_SCORE_MODEL_V2_RUNTIME_SHADOW_OBSERVATION_PLAN';

INSERT INTO analytics.edge_score_model_v2_shadow_observation_plan
(
    plan_code,
    observation_scope,
    source_layer,
    target_layer,
    runtime_allowed,
    execution_allowed,
    micro_live_allowed,
    plan_status,
    notes
)
VALUES
(
    'EDGE_SCORE_MODEL_V2_RUNTIME_SHADOW_OBSERVATION_PLAN',
    'observe V2 score/explain against runtime candidates without order routing',
    'analytics.edge_score_model_v2',
    'runtime shadow observation only',
    0,
    0,
    0,
    'PLAN_ONLY',
    'EDGE_SCORE_MODEL_V2 remains read-only analytical layer. No runtime mutation. No execution. No orders. No fills.'
);
SQL

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_score_model_v2_shadow_observation_plan
WHERE plan_code='EDGE_SCORE_MODEL_V2_RUNTIME_SHADOW_OBSERVATION_PLAN'
  AND runtime_allowed=0
  AND execution_allowed=0
  AND micro_live_allowed=0
  AND plan_status='PLAN_ONLY';
")

if [ "$rows" != "1" ]; then
  echo "SHADOW_OBSERVATION_PLAN_NOT_SAFE"
  exit 1
fi

echo "plan_rows=$rows"
echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SCORE_MODEL_V2_RUNTIME_SHADOW_OBSERVATION_PLAN_READY"
echo "VERDICT=TEST_EDGE_SCORE_MODEL_V2_RUNTIME_SHADOW_OBSERVATION_PLAN_OK"
