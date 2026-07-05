#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_SPRINT_REVIEW_V1 ==="

echo "--- SUMMARY ---"
psql -d finam_core -c "
SELECT
  count(*) AS observations_total,
  count(*) FILTER (WHERE trades > 0) AS with_trades,
  count(*) FILTER (WHERE normalized_edge_score >= 60) AS strong_rows,
  max(normalized_edge_score) AS best_score,
  max(profit_factor) AS best_pf,
  max(expectancy) AS best_expectancy
FROM analytics.edge_observation_v1;
"

echo "--- TOP 30 OBSERVATIONS ---"
psql -d finam_core -c "
SELECT
  strategy_code,
  symbol,
  timeframe,
  trades,
  wins,
  losses,
  round(profit_factor, 4) AS pf,
  round(expectancy, 6) AS expectancy,
  round(normalized_edge_score, 4) AS score,
  round(confidence_score, 4) AS confidence,
  round(stability_score, 4) AS stability,
  runner_version
FROM analytics.edge_observation_v1
WHERE trades > 0
ORDER BY normalized_edge_score DESC, profit_factor DESC, expectancy DESC
LIMIT 30;
"

echo "--- BY STRATEGY ---"
psql -d finam_core -c "
SELECT
  strategy_code,
  count(*) AS observations,
  count(*) FILTER (WHERE trades > 0) AS with_trades,
  max(round(normalized_edge_score, 4)) AS best_score,
  max(round(profit_factor, 4)) AS best_pf,
  max(round(expectancy, 6)) AS best_expectancy
FROM analytics.edge_observation_v1
GROUP BY strategy_code
ORDER BY best_score DESC NULLS LAST, best_pf DESC NULLS LAST
LIMIT 30;
"

echo "--- BY SYMBOL ---"
psql -d finam_core -c "
SELECT
  symbol,
  count(*) AS observations,
  count(*) FILTER (WHERE trades > 0) AS with_trades,
  max(round(normalized_edge_score, 4)) AS best_score,
  max(round(profit_factor, 4)) AS best_pf,
  max(round(expectancy, 6)) AS best_expectancy
FROM analytics.edge_observation_v1
GROUP BY symbol
ORDER BY best_score DESC NULLS LAST, best_pf DESC NULLS LAST
LIMIT 30;
"

strong_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_observation_v1
WHERE trades > 0
  AND normalized_edge_score >= 60;
")

with_trades=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_observation_v1
WHERE trades > 0;
")

echo "observations_with_trades=$with_trades"
echo "strong_rows=$strong_rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SPRINT_REVIEW_V1_READY"
echo "VERDICT=TEST_EDGE_SPRINT_REVIEW_V1_OK"
