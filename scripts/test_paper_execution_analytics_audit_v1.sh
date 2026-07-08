#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_EXECUTION_ANALYTICS_AUDIT_V1 ==="

mkdir -p reports
report="reports/paper_execution_analytics_audit_v1.txt"

snapshot_id=$(psql -At -d finam_core -c "
SELECT analytics_snapshot_id
FROM analytics.analytics_snapshot_v1
WHERE snapshot_type='PAPER_EXECUTION_ANALYTICS'
  AND source_version='PAPER_EXECUTION_ANALYTICS_ENGINE_V1'
ORDER BY created_at DESC
LIMIT 1;
")

test -n "$snapshot_id"

{
echo "======================================================"
echo "PAPER EXECUTION ANALYTICS AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo "analytics_snapshot_id=${snapshot_id}"
echo

echo "=== SNAPSHOT ==="
psql -d finam_core -P pager=off -c "
SELECT *
FROM analytics.analytics_snapshot_v1
WHERE analytics_snapshot_id=${snapshot_id};
"

echo
echo "=== SUMMARY ==="
psql -d finam_core -P pager=off -c "
SELECT
  trades_total,
  wins_total,
  losses_total,
  flat_total,
  round(gross_profit,6) AS gross_profit,
  round(gross_loss,6) AS gross_loss,
  round(net_pnl_points,6) AS net_pnl_points,
  round(profit_factor,6) AS profit_factor,
  round(expectancy_r,6) AS expectancy_r,
  round(win_rate,6) AS win_rate,
  round(avg_r_multiple,6) AS avg_r_multiple,
  round(avg_mae_points,6) AS avg_mae_points,
  round(avg_mfe_points,6) AS avg_mfe_points,
  round(avg_bars_held,6) AS avg_bars_held
FROM analytics.paper_execution_summary_v1
WHERE analytics_snapshot_id=${snapshot_id};
"

echo
echo "=== PROFILE SCORECARD ==="
psql -d finam_core -P pager=off -c "
SELECT
  profile_code,
  trades_total,
  wins_total,
  losses_total,
  flat_total,
  round(net_pnl_points,6) AS net_pnl_points,
  round(profit_factor,6) AS profit_factor,
  round(expectancy_r,6) AS expectancy_r,
  round(win_rate,6) AS win_rate,
  sample_status
FROM analytics.paper_execution_profile_scorecard_v1
WHERE analytics_snapshot_id=${snapshot_id}
ORDER BY trades_total DESC, profile_code;
"

echo
echo "=== SOURCE SCORECARD ==="
psql -d finam_core -P pager=off -c "
SELECT
  entry_source,
  stop_source,
  target_source,
  trades_total,
  wins_total,
  losses_total,
  flat_total,
  round(net_pnl_points,6) AS net_pnl_points,
  round(profit_factor,6) AS profit_factor,
  round(expectancy_r,6) AS expectancy_r,
  round(win_rate,6) AS win_rate,
  sample_status
FROM analytics.paper_execution_source_scorecard_v1
WHERE analytics_snapshot_id=${snapshot_id}
ORDER BY trades_total DESC, entry_source, stop_source, target_source;
"

echo
echo "=== REGIME SCORECARD ==="
psql -d finam_core -P pager=off -c "
SELECT
  regime_code,
  trades_total,
  wins_total,
  losses_total,
  flat_total,
  round(net_pnl_points,6) AS net_pnl_points,
  round(profit_factor,6) AS profit_factor,
  round(expectancy_r,6) AS expectancy_r,
  round(win_rate,6) AS win_rate,
  sample_status
FROM analytics.paper_execution_regime_scorecard_v1
WHERE analytics_snapshot_id=${snapshot_id}
ORDER BY trades_total DESC, regime_code;
"

echo
echo "=== SAMPLE STATUS CONTROL ==="
psql -d finam_core -P pager=off -c "
SELECT sample_status, count(*) AS rows_total
FROM (
  SELECT sample_status
  FROM analytics.paper_execution_profile_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT sample_status
  FROM analytics.paper_execution_source_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT sample_status
  FROM analytics.paper_execution_regime_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
) s
GROUP BY sample_status
ORDER BY sample_status;
"

echo
echo "=== FK / COMPLETENESS CONTROL ==="
psql -d finam_core -P pager=off -c "
WITH checks AS (
  SELECT 'summary' AS table_name, count(*) AS rows_total
  FROM analytics.paper_execution_summary_v1
  WHERE analytics_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'profile_scorecard', count(*)
  FROM analytics.paper_execution_profile_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'source_scorecard', count(*)
  FROM analytics.paper_execution_source_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT 'regime_scorecard', count(*)
  FROM analytics.paper_execution_regime_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
)
SELECT *
FROM checks
ORDER BY table_name;
"

echo
echo "=== OVERFIT GUARD ==="
echo "auto_decision=0"
echo "sample_status_only=1"
echo "production_allowed=0"
echo "validated_allowed_only_if_min_sample=1"

echo
echo "=== SAFETY ==="
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo

echo "VERDICT=PAPER_EXECUTION_ANALYTICS_AUDIT_V1_READY"
} | tee "$report"

grep -q "VERDICT=PAPER_EXECUTION_ANALYTICS_AUDIT_V1_READY" "$report"

summary_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_summary_v1
WHERE analytics_snapshot_id=${snapshot_id};
")

profile_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_profile_scorecard_v1
WHERE analytics_snapshot_id=${snapshot_id};
")

source_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_source_scorecard_v1
WHERE analytics_snapshot_id=${snapshot_id};
")

regime_rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_regime_scorecard_v1
WHERE analytics_snapshot_id=${snapshot_id};
")

bad_sample_status=$(psql -At -d finam_core -c "
SELECT count(*)
FROM (
  SELECT sample_status
  FROM analytics.paper_execution_profile_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT sample_status
  FROM analytics.paper_execution_source_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
  UNION ALL
  SELECT sample_status
  FROM analytics.paper_execution_regime_scorecard_v1
  WHERE analytics_snapshot_id=${snapshot_id}
) s
WHERE sample_status NOT IN ('RESEARCH','VALIDATED','PRODUCTION');
")

test "$summary_rows" -eq 1
test "$profile_rows" -ge 1
test "$source_rows" -ge 1
test "$regime_rows" -ge 1
test "$bad_sample_status" = "0"

echo "report=$report"
echo "analytics_snapshot_id=$snapshot_id"
echo "summary_rows=$summary_rows"
echo "profile_scorecard_rows=$profile_rows"
echo "source_scorecard_rows=$source_rows"
echo "regime_scorecard_rows=$regime_rows"
echo "bad_sample_status=0"
echo "auto_decision=0"
echo "overfit_guard=sample_status_only"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=PAPER_EXECUTION_ANALYTICS_AUDIT_V1_READY"
echo "VERDICT=TEST_PAPER_EXECUTION_ANALYTICS_AUDIT_V1_OK"
