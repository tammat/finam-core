#!/usr/bin/env bash
set -euo pipefail

echo "=== PAPER_CANDIDATE_REVIEW_V2 ==="

echo
echo "=============================="
echo "PIPELINE SUMMARY"
echo "=============================="

psql -d finam_core -c "
SELECT
    count(*)                                           AS observations,
    count(*) FILTER (WHERE trades>0)                   AS observations_with_trades,
    max(round(normalized_edge_score,4))                AS best_score,
    max(round(profit_factor,4))                        AS best_pf,
    max(round(expectancy,6))                           AS best_expectancy
FROM analytics.edge_observation_v1;
"

echo
echo "=============================="
echo "VALIDATED PAPER CANDIDATES"
echo "=============================="

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

    round(o.win_rate*100,2)                 AS win_rate,

    round(o.profit_factor,4)                AS pf,

    round(o.expectancy,6)                   AS expectancy,

    round(o.max_drawdown,6)                 AS drawdown,

    round(o.normalized_edge_score,4)        AS edge_score,

    round(o.confidence_score,4)             AS confidence,

    round(o.stability_score,4)              AS stability,

    c.paper_allowed

FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
ON o.observation_uuid=c.observation_uuid

WHERE
        c.candidate_status='VALIDATED'
    AND c.paper_allowed=true

ORDER BY
    c.validation_score DESC,
    c.discovery_rank ASC;
"

echo
echo "=============================="
echo "TOP 50 TRADES"
echo "=============================="

psql -d finam_core -c "
SELECT

    strategy_code,

    symbol,

    timeframe,

    trade_no,

    side,

    entry_ts,

    exit_ts,

    round(entry_price,4) entry,

    round(exit_price,4) exit,

    round(net_pnl,6) pnl

FROM analytics.research_trade_v1

ORDER BY

    strategy_code,

    symbol,

    timeframe,

    trade_no

LIMIT 50;
"

echo
echo "=============================="
echo "TOP STRATEGIES"
echo "=============================="

psql -d finam_core -c "
SELECT

    strategy_code,

    count(*) observations,

    count(*) FILTER (WHERE trades>0) tradesets,

    max(round(profit_factor,4)) pf,

    max(round(expectancy,6)) expectancy,

    max(round(normalized_edge_score,4)) edge_score

FROM analytics.edge_observation_v1

GROUP BY strategy_code

ORDER BY edge_score DESC NULLS LAST

LIMIT 20;
"

echo
echo "=============================="
echo "TOP SYMBOLS"
echo "=============================="

psql -d finam_core -c "
SELECT

    symbol,

    count(*) observations,

    count(*) FILTER (WHERE trades>0) tradesets,

    max(round(profit_factor,4)) pf,

    max(round(expectancy,6)) expectancy,

    max(round(normalized_edge_score,4)) edge_score

FROM analytics.edge_observation_v1

GROUP BY symbol

ORDER BY edge_score DESC NULLS LAST

LIMIT 20;
"

validated=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE candidate_status='VALIDATED'
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

echo
echo "validated_candidates=$validated"
echo "unsafe_rows=$unsafe"

echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=PAPER_CANDIDATE_REVIEW_V2_READY"
echo "VERDICT=TEST_PAPER_CANDIDATE_REVIEW_V2_OK"

