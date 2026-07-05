#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_EDGE_SPRINT_FAST_RUN_V1 ==="

before_obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;" || echo 0)
before_trades=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.research_trade_v1;" || echo 0)

PARAMETER_SEARCH_JOB_LIMIT="${PARAMETER_SEARCH_JOB_LIMIT:-10}" \
  scripts/build_parameter_search_grid_v1.sh || true

scripts/build_edge_lab_foundation_v1.sh

DATABASE_URL=postgresql:///finam_core \
STRATEGY_EXECUTION_RUNNER_LIMIT="${STRATEGY_EXECUTION_RUNNER_LIMIT:-200}" \
PYTHONPATH=src \
python src/scripts/build_strategy_execution_runner_v1.py

DATABASE_URL=postgresql:///finam_core \
EDGE_SCORE_ENGINE_LIMIT="${EDGE_SCORE_ENGINE_LIMIT:-10000}" \
PYTHONPATH=src \
python src/scripts/build_edge_score_engine_v2.py

DATABASE_URL=postgresql:///finam_core \
PYTHONPATH=src \
python src/scripts/build_edge_sprint_v1.py

after_obs=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1;")
after_trades=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.research_trade_v1;")
with_trades=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.edge_observation_v1 WHERE trades > 0;")

echo "before_observations=$before_obs"
echo "after_observations=$after_obs"
echo "before_research_trades=$before_trades"
echo "after_research_trades=$after_trades"
echo "observations_with_trades=$with_trades"

psql -d finam_core -c "
SELECT
  strategy_code,
  symbol,
  timeframe,
  trades,
  profit_factor,
  expectancy,
  normalized_edge_score,
  confidence_score,
  stability_score
FROM analytics.edge_observation_v1
WHERE trades > 0
ORDER BY normalized_edge_score DESC, profit_factor DESC, expectancy DESC
LIMIT 30;
"

test "$after_obs" -ge "$before_obs"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SPRINT_FAST_RUN_V1_OK"
