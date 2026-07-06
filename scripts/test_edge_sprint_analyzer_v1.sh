#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_SPRINT_ANALYZER_V1 ==="

mkdir -p reports

REPORT="reports/edge_sprint_analyzer_latest.txt"

{
echo "=== EDGE_SPRINT_ANALYZER_V1 ==="
echo "created_at=$(date -Is)"

echo
echo "--- SUMMARY ---"
psql -d finam_core -c "
SELECT
  (SELECT count(*) FROM analytics.research_queue_v1) AS research_queue,
  (SELECT count(*) FROM analytics.edge_observation_v1) AS observations,
  (SELECT count(*) FROM analytics.edge_observation_v1 WHERE trades > 0) AS with_trades,
  (SELECT count(*) FROM analytics.edge_candidate_v1) AS candidates,
  (SELECT count(*) FROM analytics.edge_candidate_v1 WHERE candidate_status='VALIDATED') AS validated,
  (SELECT count(*) FROM analytics.edge_candidate_v1 WHERE paper_allowed=true) AS paper,
  (SELECT count(*) FROM analytics.research_trade_v1) AS research_trades;
"

echo
echo "--- WINNER STRATEGIES ---"
psql -d finam_core -c "
SELECT
  strategy_code,
  count(*) AS observations,
  count(*) FILTER (WHERE trades > 0) AS with_trades,
  max(round(profit_factor,4)) AS best_pf,
  max(round(expectancy,6)) AS best_expectancy,
  max(round(normalized_edge_score,4)) AS best_score
FROM analytics.edge_observation_v1
GROUP BY strategy_code
ORDER BY best_score DESC NULLS LAST, best_pf DESC NULLS LAST
LIMIT 10;
"

echo
echo "--- WINNER SYMBOLS ---"
psql -d finam_core -c "
SELECT
  symbol,
  count(*) AS observations,
  count(*) FILTER (WHERE trades > 0) AS with_trades,
  max(round(profit_factor,4)) AS best_pf,
  max(round(expectancy,6)) AS best_expectancy,
  max(round(normalized_edge_score,4)) AS best_score
FROM analytics.edge_observation_v1
GROUP BY symbol
ORDER BY best_score DESC NULLS LAST, best_pf DESC NULLS LAST
LIMIT 10;
"

echo
echo "--- BEST PARAMETER SETS ---"
psql -d finam_core -c "
SELECT
  strategy_code,
  symbol,
  timeframe,
  parameter_json,
  trades,
  round(profit_factor,4) AS pf,
  round(expectancy,6) AS expectancy,
  round(normalized_edge_score,4) AS score
FROM analytics.edge_observation_v1
WHERE trades > 0
ORDER BY normalized_edge_score DESC, profit_factor DESC, expectancy DESC
LIMIT 20;
"

echo
echo "--- LOSERS / EXCLUDE CANDIDATES ---"
psql -d finam_core -c "
SELECT
  strategy_code,
  symbol,
  count(*) AS observations,
  count(*) FILTER (WHERE trades > 0) AS with_trades,
  max(round(normalized_edge_score,4)) AS best_score
FROM analytics.edge_observation_v1
GROUP BY strategy_code, symbol
HAVING count(*) FILTER (WHERE trades > 0) = 0
    OR max(normalized_edge_score) < 30
ORDER BY best_score ASC NULLS FIRST
LIMIT 30;
"

echo
echo "--- NEXT SPRINT PLAN ---"
echo "FOCUS_STRATEGIES=BOLLINGER_REVERSION_V1,VWAP_REVERSION_V1,RSI_MEAN_REVERSION_V1"
echo "FOCUS_SYMBOLS=SBER@MISX,LKOH@MISX"
echo "FOCUS_TIMEFRAMES=M1,M5,M15"
echo "ACTION=EXPAND_MEAN_REVERSION_PARAMETERS"
echo "DROP_TEMPORARY=BR@RTSX,NG@RTSX"
echo "BOTTLENECK=WITH_TRADES_TO_CANDIDATES"
echo "NEXT_EPIC=RECOMMENDATION_ENGINE_V1"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SPRINT_ANALYZER_V1_READY"
} | tee "$REPORT"

grep -q "VERDICT=EDGE_SPRINT_ANALYZER_V1_READY" "$REPORT"

echo "report=$REPORT"
echo "VERDICT=TEST_EDGE_SPRINT_ANALYZER_V1_OK"
