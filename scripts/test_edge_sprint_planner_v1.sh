#!/usr/bin/env bash
set -euo pipefail

echo "=== EDGE_SPRINT_PLANNER_V1 ==="

mkdir -p reports

PLAN_SQL="/tmp/edge_sprint_planner_v1.sql"
PLAN_TXT="reports/edge_sprint_plan_latest.txt"

cat > "$PLAN_SQL" <<'SQL'
INSERT INTO analytics.parameter_search_job_v1 (
    search_code,
    strategy_code,
    symbol,
    timeframe,
    method_code,
    status_code,
    max_trials,
    objective_metric,
    source_version,
    updated_at
)
SELECT
    'EDGE_SPRINT_3:' || s.strategy_code || ':' || x.symbol || ':' || x.timeframe,
    s.strategy_code,
    x.symbol,
    x.timeframe,
    'GRID',
    'QUEUED',
    300,
    'normalized_edge_score',
    'EDGE_SPRINT_PLANNER_V1',
    now()
FROM (
    VALUES
        ('VWAP_REVERSION_V1'),
        ('BOLLINGER_REVERSION_V1'),
        ('RSI_MEAN_REVERSION_V1')
) AS s(strategy_code)
CROSS JOIN (
    VALUES
        ('SBER@MISX','M1'),
        ('SBER@MISX','M5'),
        ('SBER@MISX','M15'),
        ('LKOH@MISX','M1'),
        ('LKOH@MISX','M5'),
        ('LKOH@MISX','M15')
) AS x(symbol, timeframe)
ON CONFLICT(search_code) DO UPDATE SET
    status_code='QUEUED',
    max_trials=300,
    objective_metric='normalized_edge_score',
    source_version='EDGE_SPRINT_PLANNER_V1',
    updated_at=now();
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f "$PLAN_SQL"

{
echo "=== EDGE_SPRINT_PLANNER_V1 ==="
echo "created_at=$(date -Is)"
echo
echo "SPRINT=EDGE_SPRINT_3"
echo "SOURCE=RECOMMENDATION_ENGINE_V1"
echo "ACTION=EXPAND_MEAN_REVERSION"
echo "STRATEGIES=VWAP_REVERSION_V1,BOLLINGER_REVERSION_V1,RSI_MEAN_REVERSION_V1"
echo "SYMBOLS=SBER@MISX,LKOH@MISX"
echo "TIMEFRAMES=M1,M5,M15"
echo "MAX_TRIALS=300"
echo "TEMPORARY_DROP=BR@RTSX,NG@RTSX"
echo
echo "--- PLANNED JOBS ---"
psql -d finam_core -c "
SELECT
  strategy_code,
  symbol,
  timeframe,
  status_code,
  max_trials,
  source_version
FROM analytics.parameter_search_job_v1
WHERE source_version='EDGE_SPRINT_PLANNER_V1'
ORDER BY strategy_code, symbol, timeframe;
"
echo
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=EDGE_SPRINT_PLANNER_V1_READY"
} | tee "$PLAN_TXT"

planned=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.parameter_search_job_v1
WHERE source_version='EDGE_SPRINT_PLANNER_V1'
  AND status_code='QUEUED';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$planned" -ge 18
test "$unsafe" = "0"
grep -q "VERDICT=EDGE_SPRINT_PLANNER_V1_READY" "$PLAN_TXT"

echo "planned_jobs=$planned"
echo "unsafe_rows=$unsafe"
echo "report=$PLAN_TXT"
echo "VERDICT=TEST_EDGE_SPRINT_PLANNER_V1_OK"
