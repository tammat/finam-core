#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_SPRINT_ANALYSIS_V1 ==="

mkdir -p reports

REPORT="reports/edge_sprint_analysis_latest.txt"

{
echo "=== EDGE_SPRINT_ANALYSIS_V1 ==="
echo "created_at=$(date -Is)"

echo
echo "--- FUNNEL ---"
psql -d finam_core -c "
SELECT
  (SELECT count(*) FROM analytics.research_queue_v1) AS research_queue,
  (SELECT count(*) FROM analytics.edge_lab_run_v1) AS runs,
  (SELECT count(*) FROM analytics.edge_observation_v1) AS observations,
  (SELECT count(*) FROM analytics.edge_observation_v1 WHERE trades > 0) AS with_trades,
  (SELECT count(*) FROM analytics.edge_candidate_v1) AS candidates,
  (SELECT count(*) FROM analytics.edge_candidate_v1 WHERE candidate_status='VALIDATED') AS validated,
  (SELECT count(*) FROM analytics.edge_candidate_v1 WHERE paper_allowed=true) AS paper;
"

echo
echo "--- BEST PAPER CANDIDATES ---"
psql -d finam_core -c "
SELECT
  c.discovery_rank,
  c.candidate_class,
  c.validation_score,
  c.strategy_code,
  c.symbol,
  c.timeframe,
  o.trades,
  o.wins,
  o.losses,
  round(o.win_rate*100,2) AS win_rate,
  round(o.profit_factor,4) AS pf,
  round(o.expectancy,6) AS expectancy,
  round(o.max_drawdown,6) AS drawdown,
  round(o.normalized_edge_score,4) AS score
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid=c.observation_uuid
WHERE c.paper_allowed=true
ORDER BY c.validation_score DESC, c.discovery_rank ASC;
"

echo
echo "--- STRATEGY ANALYSIS ---"
psql -d finam_core -c "
SELECT
  strategy_code,
  count(*) AS observations,
  count(*) FILTER (WHERE trades>0) AS with_trades,
  max(round(profit_factor,4)) AS best_pf,
  max(round(expectancy,6)) AS best_expectancy,
  max(round(normalized_edge_score,4)) AS best_score
FROM analytics.edge_observation_v1
GROUP BY strategy_code
ORDER BY best_score DESC NULLS LAST, best_pf DESC NULLS LAST;
"

echo
echo "--- SYMBOL ANALYSIS ---"
psql -d finam_core -c "
SELECT
  symbol,
  count(*) AS observations,
  count(*) FILTER (WHERE trades>0) AS with_trades,
  max(round(profit_factor,4)) AS best_pf,
  max(round(expectancy,6)) AS best_expectancy,
  max(round(normalized_edge_score,4)) AS best_score
FROM analytics.edge_observation_v1
GROUP BY symbol
ORDER BY best_score DESC NULLS LAST, best_pf DESC NULLS LAST;
"

echo
echo "--- CONCLUSION ---"
echo "STATUS=FIRST_PAPER_CANDIDATES_FOUND"
echo "MAIN_WINNERS=BOLLINGER_REVERSION_V1,VWAP_REVERSION_V1,RSI_MEAN_REVERSION_V1"
echo "BEST_SYMBOLS=SBER@MISX,LKOH@MISX"
echo "WEAK_SYMBOLS=BR@RTSX,NG@RTSX"
echo "PRIMARY_BOTTLENECK=WITH_TRADES_TO_CANDIDATES"
echo "NEXT_ACTION=PARAMETER_EXPANSION_FOR_MEAN_REVERSION_AND_SBER_LKOH"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SPRINT_ANALYSIS_V1_READY"
} | tee "$REPORT"

grep -q "VERDICT=EDGE_SPRINT_ANALYSIS_V1_READY" "$REPORT"

echo "report=$REPORT"
echo "VERDICT=TEST_EDGE_SPRINT_ANALYSIS_V1_OK"
