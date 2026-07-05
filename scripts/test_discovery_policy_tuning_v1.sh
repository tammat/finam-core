#!/usr/bin/env bash
set -euo pipefail

echo "=== DISCOVERY_POLICY_TUNING_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
UPDATE analytics.edge_discovery_rule_v1
SET threshold_value=20,
    weight=0.15,
    updated_at=now()
WHERE rule_code='RULE_TRADES_MIN_V1';

UPDATE analytics.edge_discovery_rule_v1
SET threshold_value=1.05,
    weight=0.25,
    updated_at=now()
WHERE rule_code='RULE_PF_MIN_V1';

UPDATE analytics.edge_discovery_rule_v1
SET threshold_value=40,
    weight=0.20,
    updated_at=now()
WHERE rule_code='RULE_SCORE_MIN_V1';

UPDATE analytics.edge_discovery_rule_v1
SET threshold_value=40,
    weight=0.15,
    updated_at=now()
WHERE rule_code='RULE_CONFIDENCE_MIN_V1';

UPDATE analytics.edge_discovery_rule_v1
SET threshold_value=40,
    weight=0.10,
    updated_at=now()
WHERE rule_code='RULE_STABILITY_MIN_V1';
SQL

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_discovery_rule_rank_v1.py | tee /tmp/discovery_policy_tuning_v1.txt

grep -q "VERDICT=EDGE_DISCOVERY_RULE_RANK_V1_READY" /tmp/discovery_policy_tuning_v1.txt

candidates=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_candidate_v1;
")

validated=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_candidate_v1
WHERE candidate_status='VALIDATED';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$candidates" -gt 4
test "$unsafe" = "0"

psql -d finam_core -c "
SELECT
  c.discovery_rank,
  c.candidate_class,
  c.candidate_status,
  c.validation_stage,
  c.strategy_code,
  c.symbol,
  c.timeframe,
  o.trades,
  round(o.profit_factor,4) AS pf,
  round(o.expectancy,6) AS expectancy,
  round(o.normalized_edge_score,4) AS score
FROM analytics.edge_candidate_v1 c
JOIN analytics.edge_observation_v1 o
  ON o.observation_uuid=c.observation_uuid
ORDER BY c.discovery_score DESC, c.discovery_rank ASC
LIMIT 30;
"

echo "candidates_total=$candidates"
echo "validated_total=$validated"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DISCOVERY_POLICY_TUNING_V1_OK"
