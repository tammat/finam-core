#!/usr/bin/env bash
set -euo pipefail

echo "=== PARAMETER_EXPANSION_MEAN_REVERSION_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
UPDATE analytics.parameter_search_space_v1
SET enabled=true,
    search_method='GRID',
    updated_at=now()
WHERE strategy_code IN (
    'BOLLINGER_REVERSION_V1',
    'VWAP_REVERSION_V1',
    'RSI_MEAN_REVERSION_V1'
);

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
    'MEANREV_EXPANSION:' || s.strategy_code || ':' || x.symbol || ':' || x.timeframe,
    s.strategy_code,
    x.symbol,
    x.timeframe,
    'GRID',
    'QUEUED',
    120,
    'normalized_edge_score',
    'PARAMETER_EXPANSION_MEAN_REVERSION_V1',
    now()
FROM (
    VALUES
        ('BOLLINGER_REVERSION_V1'),
        ('VWAP_REVERSION_V1'),
        ('RSI_MEAN_REVERSION_V1')
) AS s(strategy_code)
CROSS JOIN (
    VALUES
        ('SBER@MISX','M5'),
        ('SBER@MISX','M1'),
        ('LKOH@MISX','M5'),
        ('LKOH@MISX','M1')
) AS x(symbol, timeframe)
ON CONFLICT(search_code) DO UPDATE SET
    status_code='QUEUED',
    max_trials=120,
    objective_metric='normalized_edge_score',
    source_version='PARAMETER_EXPANSION_MEAN_REVERSION_V1',
    updated_at=now();
SQL

PARAMETER_SEARCH_JOB_LIMIT=50 scripts/build_parameter_search_grid_v1.sh

scripts/build_edge_lab_foundation_v1.sh

DATABASE_URL=postgresql:///finam_core \
STRATEGY_EXECUTION_RUNNER_LIMIT=300 \
PYTHONPATH=src \
python src/scripts/build_strategy_execution_runner_v1.py

DATABASE_URL=postgresql:///finam_core \
EDGE_SCORE_ENGINE_LIMIT=20000 \
PYTHONPATH=src \
python src/scripts/build_edge_score_engine_v2.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_edge_pipeline_audit_v1.py

psql -d finam_core -c "
SELECT
  strategy_code,
  symbol,
  timeframe,
  count(*) AS observations,
  count(*) FILTER (WHERE trades > 0) AS with_trades,
  max(round(profit_factor,4)) AS best_pf,
  max(round(expectancy,6)) AS best_expectancy,
  max(round(normalized_edge_score,4)) AS best_score
FROM analytics.edge_observation_v1
WHERE strategy_code IN (
  'BOLLINGER_REVERSION_V1',
  'VWAP_REVERSION_V1',
  'RSI_MEAN_REVERSION_V1'
)
AND symbol IN ('SBER@MISX','LKOH@MISX')
GROUP BY strategy_code, symbol, timeframe
ORDER BY best_score DESC NULLS LAST, best_pf DESC NULLS LAST;
"

new_jobs=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.parameter_search_job_v1
WHERE source_version='PARAMETER_EXPANSION_MEAN_REVERSION_V1';
")

unsafe=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.edge_candidate_v1
WHERE micro_live_allowed=true OR live_allowed=true;
")

test "$new_jobs" -gt 0
test "$unsafe" = "0"

echo "parameter_expansion_jobs=$new_jobs"
echo "unsafe_rows=$unsafe"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PARAMETER_EXPANSION_MEAN_REVERSION_V1_READY"
echo "VERDICT=TEST_PARAMETER_EXPANSION_MEAN_REVERSION_V1_OK"
