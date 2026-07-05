#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_SPRINT_REVIEW_V2 ==="

echo "--- PROJECT STATUS ---"
cat reports/edge_pipeline_audit_latest.txt

echo "--- PAPER CANDIDATES ---"
psql -d finam_core -c "
SELECT
  c.discovery_rank,
  c.candidate_class,
  c.candidate_status,
  c.validation_stage,
  c.paper_allowed,
  c.strategy_code,
  c.symbol,
  c.timeframe,
  o.trades,
  round(o.profit_factor,4) AS pf,
  round(o.expectancy,6) AS expectancy,
  round(o.normalized_edge_score,4) AS score
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid=c.observation_uuid
ORDER BY c.validation_score DESC, c.discovery_rank ASC;
"

echo "--- RECOMMENDATION ---"
echo "PRIMARY_BOTTLENECK=WITH_TRADES_TO_CANDIDATES"
echo "NEXT_ACTION=DISCOVERY_POLICY_TUNING_OR_STRATEGY_PARAMETER_EXPANSION"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_EDGE_SPRINT_REVIEW_V2_OK"
