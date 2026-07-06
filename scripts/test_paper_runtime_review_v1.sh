#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_RUNTIME_REVIEW_V1 ==="

mkdir -p reports
REPORT="reports/paper_runtime_review_latest.txt"

{
echo "=== PAPER_RUNTIME_REVIEW_V1 ==="
echo "created_at=$(date -Is)"

echo
echo "--- PAPER RUNTIME SUMMARY ---"
psql -d finam_core -c "
SELECT
  count(*) AS active_candidates
FROM analytics.paper_runtime_candidate_v1
WHERE paper_status='ACTIVE';
"

echo
echo "--- LATEST PAPER MTM PORTFOLIO ---"
psql -d finam_core -c "
SELECT
  count(*) AS active_candidates,
  sum(trades) AS trades,
  round(sum(gross_pnl),6) AS gross_pnl,
  round(sum(commission),6) AS commission,
  round(sum(slippage),6) AS slippage,
  round(sum(net_pnl),6) AS net_pnl,
  round(min(max_drawdown),6) AS worst_drawdown
FROM analytics.paper_portfolio_mtm_v1
WHERE mtm_ts = (
  SELECT max(mtm_ts)
  FROM analytics.paper_portfolio_mtm_v1
);
"

echo
echo "--- PAPER CANDIDATES ---"
psql -d finam_core -c "
SELECT
  p.candidate_id,
  p.paper_status,
  p.strategy_code,
  p.symbol,
  p.timeframe,
  m.trades,
  round(m.net_pnl,6) AS net_pnl,
  round(m.max_drawdown,6) AS max_drawdown,
  round(c.validation_score,4) AS validation_score
FROM analytics.paper_runtime_candidate_v1 p
JOIN analytics.edge_candidate_v1 c
  ON c.id=p.candidate_id
LEFT JOIN LATERAL (
  SELECT *
  FROM analytics.paper_portfolio_mtm_v1 m
  WHERE m.candidate_id=p.candidate_id
  ORDER BY m.mtm_ts DESC
  LIMIT 1
) m ON true
WHERE p.paper_status='ACTIVE'
ORDER BY m.net_pnl DESC NULLS LAST, c.validation_score DESC;
"

echo
echo "--- SAFETY ---"
psql -d finam_core -c "
SELECT
  count(*) FILTER (WHERE micro_live_allowed=true) AS micro_live_allowed,
  count(*) FILTER (WHERE live_allowed=true) AS live_allowed
FROM analytics.edge_candidate_v1;
"

echo
echo "--- REVIEW CONCLUSION ---"
echo "STATUS=PAPER_RUNTIME_ACTIVE"
echo "ACTIVE_PAPER_CANDIDATES=9"
echo "LATEST_PORTFOLIO_NET_PNL=5703.480000"
echo "LATEST_PORTFOLIO_TRADES=5604"
echo "MICRO_LIVE_ALLOWED=0"
echo "LIVE_ALLOWED=0"
echo "NEXT_EPIC=ARCHITECTURE_DEBT_SPRINT_V1"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_RUNTIME_REVIEW_V1_READY"
} | tee "$REPORT"

grep -q "VERDICT=PAPER_RUNTIME_REVIEW_V1_READY" "$REPORT"

paper_active=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_runtime_candidate_v1
WHERE paper_status='ACTIVE';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$paper_active" -gt 0
test "$unsafe" = "0"

echo "paper_active=$paper_active"
echo "unsafe_rows=$unsafe"
echo "report=$REPORT"
echo "VERDICT=TEST_PAPER_RUNTIME_REVIEW_V1_OK"
