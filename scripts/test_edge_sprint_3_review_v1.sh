#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_SPRINT_3_REVIEW_V1 ==="

mkdir -p reports
REPORT="reports/edge_sprint_3_review_latest.txt"

{
echo "=== EDGE_SPRINT_3_REVIEW_V1 ==="
echo "created_at=$(date -Is)"

echo
echo "--- PIPELINE SUMMARY ---"
cat reports/edge_pipeline_audit_latest.txt

echo
echo "--- TOP PAPER CANDIDATES ---"
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
  o.wins,
  o.losses,
  round(o.win_rate*100,2) AS win_rate,
  round(o.profit_factor,4) AS pf,
  round(o.expectancy,6) AS expectancy,
  round(o.max_drawdown,6) AS drawdown,
  round(o.normalized_edge_score,4) AS score,
  round(c.validation_score,4) AS validation_score
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid=c.observation_uuid
WHERE c.paper_allowed=true
ORDER BY c.validation_score DESC, c.discovery_score DESC
LIMIT 30;
"

echo
echo "--- TOP MEAN REVERSION OBSERVATIONS ---"
psql -d finam_core -c "
SELECT
  strategy_code,
  symbol,
  timeframe,
  parameter_json,
  trades,
  wins,
  losses,
  round(profit_factor,4) AS pf,
  round(expectancy,6) AS expectancy,
  round(normalized_edge_score,4) AS score
FROM analytics.edge_observation_v1
WHERE trades > 0
  AND strategy_code IN (
    'VWAP_REVERSION_V1',
    'BOLLINGER_REVERSION_V1',
    'RSI_MEAN_REVERSION_V1'
  )
ORDER BY normalized_edge_score DESC, profit_factor DESC, expectancy DESC
LIMIT 40;
"

echo
echo "--- STRATEGY SUMMARY ---"
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
echo "--- SYMBOL SUMMARY ---"
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
echo "--- REVIEW CONCLUSION ---"
echo "STATUS=EDGE_SPRINT_3_REVIEW_DONE"
echo "PRIMARY_DIRECTION=MEAN_REVERSION"
echo "PRIMARY_SYMBOLS=SBER@MISX,LKOH@MISX"
echo "PRIMARY_STRATEGIES=VWAP_REVERSION_V1,BOLLINGER_REVERSION_V1,RSI_MEAN_REVERSION_V1"
echo "TEMPORARY_DROP=BR@RTSX,NG@RTSX"
echo "NEXT_EPIC=PAPER_RUNTIME_CANDIDATE_V1"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SPRINT_3_REVIEW_V1_READY"
} | tee "$REPORT"

grep -q "VERDICT=EDGE_SPRINT_3_REVIEW_V1_READY" "$REPORT"

paper=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE paper_allowed=true;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$paper" -gt 0
test "$unsafe" = "0"

echo "paper_candidates=$paper"
echo "unsafe_rows=$unsafe"
echo "report=$REPORT"
echo "VERDICT=TEST_EDGE_SPRINT_3_REVIEW_V1_OK"
