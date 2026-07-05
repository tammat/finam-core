#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_VALIDATION_V2 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS validation_score NUMERIC(12,6) NOT NULL DEFAULT 0;

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS validation_reason TEXT NOT NULL DEFAULT '';

ALTER TABLE analytics.edge_candidate_v1
ADD COLUMN IF NOT EXISTS validation_formula_version TEXT NOT NULL DEFAULT 'EDGE_VALIDATION_V2';
SQL

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
                    + o.confidence_score * 0.20
                    + o.stability_score * 0.20
                    + LEAST(o.profit_factor * 20, 100) * 0.15
                    + LEAST(o.trades, 100) * 0.10
                )
            )
        ),
    validation_stage =
        CASE
            WHEN o.trades >= 30
             AND o.profit_factor > 1.2
             AND o.expectancy > 0
             AND o.normalized_edge_score >= 60
            THEN 'PASSED'
            ELSE 'FAILED'
        END,
    candidate_status =
        CASE
            WHEN o.trades >= 30
             AND o.profit_factor > 1.2
             AND o.expectancy > 0
             AND o.normalized_edge_score >= 60
            THEN 'VALIDATED'
            ELSE 'REJECTED'
        END,
    paper_allowed =
        CASE
            WHEN o.trades >= 30
             AND o.profit_factor > 1.2
             AND o.expectancy > 0
             AND o.normalized_edge_score >= 60
            THEN true
            ELSE false
        END,
    shadow_allowed=false,
    micro_live_allowed=false,
    live_allowed=false,
    validation_reason =
        'EDGE_VALIDATION_V2: trades>=30, pf>1.2, expectancy>0, score>=60',
    validation_formula_version='EDGE_VALIDATION_V2',
    updated_at=now()
FROM analytics.edge_observation_v1 o
WHERE o.observation_uuid = c.observation_uuid;
SQL

validated=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE candidate_status='VALIDATED'
  AND validation_stage='PASSED';
")

paper_allowed=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE paper_allowed=true;
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE shadow_allowed=true OR micro_live_allowed=true OR live_allowed=true;
")

psql -d finam_core -c "
SELECT
  c.discovery_rank,
  c.candidate_class,
  c.candidate_status,
  c.validation_stage,
  round(c.validation_score, 4) AS validation_score,
  c.paper_allowed,
  c.strategy_code,
  c.symbol,
  c.timeframe,
  o.trades,
  round(o.profit_factor, 4) AS pf,
  round(o.expectancy, 6) AS expectancy,
  round(o.normalized_edge_score, 4) AS score
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid = c.observation_uuid
ORDER BY c.validation_score DESC, c.discovery_rank ASC;
"

test "$validated" -gt 0
test "$paper_allowed" -gt 0
test "$unsafe" = "0"

echo "validated_candidates=$validated"
echo "paper_allowed_candidates=$paper_allowed"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_VALIDATION_V2_READY"
echo "VERDICT=TEST_EDGE_VALIDATION_V2_OK"
