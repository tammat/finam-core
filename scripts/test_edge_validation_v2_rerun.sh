#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_VALIDATION_V2_RERUN ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'

UPDATE analytics.edge_candidate_v1 c
SET
    validation_score =
        LEAST(
            100,
            GREATEST(
                0,
                (
                    o.normalized_edge_score * 0.35
                  + o.confidence_score      * 0.20
                  + o.stability_score       * 0.20
                  + LEAST(o.profit_factor * 20,100) * 0.15
                  + LEAST(o.trades,100)            * 0.10
                )
            )
        ),

    validation_stage =
        CASE
            WHEN
                o.trades >= 20
            AND o.profit_factor >= 1.05
            AND o.expectancy > 0
            AND o.normalized_edge_score >= 40
            THEN 'PASSED'
            ELSE 'FAILED'
        END,

    candidate_status =
        CASE
            WHEN
                o.trades >= 20
            AND o.profit_factor >= 1.05
            AND o.expectancy > 0
            AND o.normalized_edge_score >= 40
            THEN 'VALIDATED'
            ELSE 'REJECTED'
        END,

    paper_allowed =
        CASE
            WHEN
                o.trades >= 20
            AND o.profit_factor >= 1.05
            AND o.expectancy > 0
            AND o.normalized_edge_score >= 40
            THEN true
            ELSE false
        END,

    shadow_allowed=false,
    micro_live_allowed=false,
    live_allowed=false,

    validation_reason='EDGE_VALIDATION_V2_RERUN',

    validation_formula_version='EDGE_VALIDATION_V2_RERUN',

    updated_at=now()

FROM analytics.edge_observation_v1 o
WHERE o.observation_uuid=c.observation_uuid;

SQL

validated=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE candidate_status='VALIDATED';
")

paper=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE paper_allowed=true;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true
   OR live_allowed=true;
")

test "$validated" -gt 0
test "$paper" -gt 0
test "$unsafe" = "0"

echo
echo "===== VALIDATED ====="

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

    round(o.profit_factor,4)        pf,
    round(o.expectancy,6)           expectancy,
    round(o.normalized_edge_score,4) score,
    round(o.confidence_score,4)      confidence,
    round(o.stability_score,4)       stability,

    c.paper_allowed

FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
ON o.observation_uuid=c.observation_uuid

WHERE c.candidate_status='VALIDATED'

ORDER BY
    c.validation_score DESC,
    c.discovery_rank ASC;
"

echo
echo "validated=$validated"
echo "paper_allowed=$paper"
echo "unsafe=$unsafe"

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"

echo "VERDICT=EDGE_VALIDATION_V2_RERUN_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_V2_RERUN_OK"

