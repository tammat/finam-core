#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_CANDIDATE_REVIEW_V1 ==="

validated=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE candidate_status='VALIDATED'
  AND validation_stage='PASSED'
  AND paper_allowed=true;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true
   OR live_allowed=true;
")

test "$validated" -gt 0
test "$unsafe" = "0"

echo "--- VALIDATED PAPER CANDIDATES ---"
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
  round(o.profit_factor, 4) AS pf,
  round(o.expectancy, 6) AS expectancy,
  round(o.normalized_edge_score, 4) AS score,
  round(o.confidence_score, 4) AS confidence,
  round(o.stability_score, 4) AS stability,
  c.paper_allowed,
  c.shadow_allowed,
  c.micro_live_allowed,
  c.live_allowed
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid = c.observation_uuid
WHERE c.candidate_status='VALIDATED'
  AND c.validation_stage='PASSED'
  AND c.paper_allowed=true
ORDER BY c.validation_score DESC, c.discovery_rank ASC;
"

echo "--- TRADE SAMPLE ---"
psql -d finam_core -c "
SELECT
  t.strategy_code,
  t.symbol,
  t.timeframe,
  t.trade_no,
  t.side,
  t.entry_ts,
  t.exit_ts,
  round(t.entry_price, 4) AS entry_price,
  round(t.exit_price, 4) AS exit_price,
  round(t.net_pnl, 6) AS net_pnl
FROM analytics.research_trade_v1 t
JOIN analytics.edge_candidate_v1 c
  ON c.research_code=t.research_code
WHERE c.candidate_status='VALIDATED'
ORDER BY t.strategy_code, t.symbol, t.timeframe, t.trade_no
LIMIT 80;
"

echo "validated_paper_candidates=$validated"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_CANDIDATE_REVIEW_V1_READY"
echo "VERDICT=TEST_PAPER_CANDIDATE_REVIEW_V1_OK"
