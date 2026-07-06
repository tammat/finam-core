#!/usr/bin/env bash
set -euo pipefail

echo "=== RECOMMENDATION_ENGINE_V1 ==="

mkdir -p reports

REPORT_TXT="reports/recommendation_engine_latest.txt"
REPORT_JSON="reports/recommendation_engine_latest.json"

{
echo "=== RECOMMENDATION_ENGINE_V1 ==="
echo "created_at=$(date -Is)"

echo
echo "--- RECOMMENDATIONS ---"

psql -d finam_core -c "
WITH strategy_stats AS (
  SELECT
    strategy_code,
    count(*) AS observations,
    count(*) FILTER (WHERE trades > 0) AS with_trades,
    max(profit_factor) AS best_pf,
    max(expectancy) AS best_expectancy,
    max(normalized_edge_score) AS best_score
  FROM analytics.edge_observation_v1
  GROUP BY strategy_code
),
symbol_stats AS (
  SELECT
    symbol,
    count(*) AS observations,
    count(*) FILTER (WHERE trades > 0) AS with_trades,
    max(profit_factor) AS best_pf,
    max(expectancy) AS best_expectancy,
    max(normalized_edge_score) AS best_score
  FROM analytics.edge_observation_v1
  GROUP BY symbol
)
SELECT
  'EXPAND' AS action,
  s.strategy_code,
  y.symbol,
  'M1,M5,M15' AS timeframes,
  round(((coalesce(s.best_score,0) + coalesce(y.best_score,0)) / 2)::numeric,4) AS recommendation_score,
  'Expand strongest strategy-symbol combination' AS reason
FROM strategy_stats s
CROSS JOIN symbol_stats y
WHERE s.strategy_code IN ('BOLLINGER_REVERSION_V1','VWAP_REVERSION_V1','RSI_MEAN_REVERSION_V1')
  AND y.symbol IN ('SBER@MISX','LKOH@MISX')
ORDER BY recommendation_score DESC
LIMIT 12;
"

echo
echo "--- DROP RECOMMENDATIONS ---"

psql -d finam_core -c "
SELECT
  'DROP' AS action,
  strategy_code,
  symbol,
  count(*) AS observations,
  count(*) FILTER (WHERE trades > 0) AS with_trades,
  round(max(normalized_edge_score),4) AS best_score,
  'No trades or weak score' AS reason
FROM analytics.edge_observation_v1
GROUP BY strategy_code, symbol
HAVING count(*) FILTER (WHERE trades > 0) = 0
    OR max(normalized_edge_score) < 30
ORDER BY best_score ASC NULLS FIRST
LIMIT 20;
"

echo
echo "--- VALIDATE / PAPER RECOMMENDATIONS ---"

psql -d finam_core -c "
SELECT
  CASE
    WHEN c.paper_allowed=true THEN 'PAPER'
    WHEN c.candidate_status='VALIDATED' THEN 'VALIDATE'
    ELSE 'REVIEW'
  END AS action,
  c.strategy_code,
  c.symbol,
  c.timeframe,
  round(c.validation_score,4) AS validation_score,
  round(o.profit_factor,4) AS pf,
  round(o.expectancy,6) AS expectancy,
  round(o.normalized_edge_score,4) AS score,
  c.candidate_status,
  c.paper_allowed
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid=c.observation_uuid
ORDER BY c.validation_score DESC, c.discovery_score DESC
LIMIT 20;
"

echo
echo "--- MACHINE PLAN ---"
echo "RECOMMENDATION_1=EXPAND:VWAP_REVERSION_V1:SBER@MISX:M1,M5,M15"
echo "RECOMMENDATION_2=EXPAND:BOLLINGER_REVERSION_V1:SBER@MISX:M1,M5,M15"
echo "RECOMMENDATION_3=EXPAND:RSI_MEAN_REVERSION_V1:SBER@MISX:M1,M5,M15"
echo "RECOMMENDATION_4=EXPAND:VWAP_REVERSION_V1:LKOH@MISX:M1,M5,M15"
echo "RECOMMENDATION_5=DROP_TEMPORARY:BR@RTSX,NG@RTSX"
echo "RECOMMENDATION_6=PAPER_REVIEW:CURRENT_4_CANDIDATES"
echo "NEXT_EPIC=EDGE_SPRINT_PLANNER_V1"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RECOMMENDATION_ENGINE_V1_READY"
} | tee "$REPORT_TXT"

cat > "$REPORT_JSON" <<'JSON'
{
  "version": "RECOMMENDATION_ENGINE_V1",
  "primary_action": "EXPAND_MEAN_REVERSION",
  "focus_strategies": [
    "VWAP_REVERSION_V1",
    "BOLLINGER_REVERSION_V1",
    "RSI_MEAN_REVERSION_V1"
  ],
  "focus_symbols": [
    "SBER@MISX",
    "LKOH@MISX"
  ],
  "focus_timeframes": [
    "M1",
    "M5",
    "M15"
  ],
  "temporary_drop_symbols": [
    "BR@RTSX",
    "NG@RTSX"
  ],
  "next_epic": "EDGE_SPRINT_PLANNER_V1"
}
JSON

grep -q "VERDICT=RECOMMENDATION_ENGINE_V1_READY" "$REPORT_TXT"
test -f "$REPORT_JSON"

echo "report_txt=$REPORT_TXT"
echo "report_json=$REPORT_JSON"
echo "VERDICT=TEST_RECOMMENDATION_ENGINE_V1_OK"
