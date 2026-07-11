#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PROFIT_FACTORY_KPI_READ_MODEL_V1 ==="
psql -v ON_ERROR_STOP=1 -d finam_core -f sql/analytics/028_profit_factory_kpi_read_model_v1.sql

test_kpi=$(psql -At -F '|' -d finam_core -c "
SELECT eligible_candidates, capital_allocated, expected_profit,
       realized_profit, profit_gap, round(expected_roi,6), round(realized_roi,6)
FROM analytics.profit_factory_kpi_summary_v1
WHERE data_scope='TEST';")

real_kpi_rows=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.profit_factory_kpi_candidate_v1 WHERE data_scope='REAL';")
untrusted_rows=$(psql -At -d finam_core -c "
SELECT count(*) FROM analytics.profit_factory_kpi_candidate_v1 WHERE NOT financial_kpi_eligible;")

test "$test_kpi" = "1|100000.000000|12500.000000|8700.000000|3800.000000|0.125000|0.087000"
test "$real_kpi_rows" = "0"
test "$untrusted_rows" = "0"

echo "test_kpi=$test_kpi"
echo "real_kpi_rows=$real_kpi_rows"
echo "untrusted_rows=$untrusted_rows"
echo "VERDICT=TEST_PROFIT_FACTORY_KPI_READ_MODEL_V1_OK"
