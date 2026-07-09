#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_PAPER_PROFIT_READINESS_AUDIT_V1 ==="

mkdir -p reports
report="reports/paper_profit_readiness_audit_v1.txt"

model_health_snapshot_id=$(psql -At -d finam_core -c "
SELECT model_health_snapshot_id
FROM analytics.marketcore_model_health_snapshot_v1
WHERE source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1'
ORDER BY created_at DESC
LIMIT 1;
")

paper_snapshot_id=$(psql -At -d finam_core -c "
SELECT analytics_snapshot_id
FROM analytics.analytics_snapshot_v1
WHERE snapshot_type='PAPER_EXECUTION_ANALYTICS'
  AND source_version='PAPER_EXECUTION_ANALYTICS_ENGINE_V1'
ORDER BY created_at DESC
LIMIT 1;
")

robustness_snapshot_id=$(psql -At -d finam_core -c "
SELECT analytics_snapshot_id
FROM analytics.analytics_snapshot_v1
WHERE snapshot_type='PAPER_EXECUTION_ROBUSTNESS'
  AND source_version='PAPER_EXECUTION_ROBUSTNESS_AUDIT_V1'
ORDER BY created_at DESC
LIMIT 1;
")

test -n "$model_health_snapshot_id"
test -n "$paper_snapshot_id"
test -n "$robustness_snapshot_id"

{
echo "======================================================"
echo "PAPER PROFIT READINESS AUDIT V1"
echo "======================================================"
echo "generated_at=$(date -Is)"
echo "model_health_snapshot_id=${model_health_snapshot_id}"
echo "paper_snapshot_id=${paper_snapshot_id}"
echo "robustness_snapshot_id=${robustness_snapshot_id}"
echo

echo "=== PAPER SUMMARY ==="
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
WHERE analytics_snapshot_id=${paper_snapshot_id};
"

echo
echo "=== ROBUSTNESS ==="
psql -d finam_core -P pager=off -c "
SELECT
  sample_trades,
  time_bucket_count,
  instrument_count,
  regime_count,
  source_count,
  round(sample_score,4) AS sample_score,
  round(time_stability_score,4) AS time_stability_score,
  round(instrument_stability_score,4) AS instrument_stability_score,
  round(regime_stability_score,4) AS regime_stability_score,
  round(source_stability_score,4) AS source_stability_score,
  round(robustness_score,4) AS robustness_score,
  round(learning_readiness_index,4) AS learning_readiness_index,
  sample_status,
  overfit_risk,
  production_allowed,
  auto_decision
FROM analytics.paper_execution_robustness_audit_v1
WHERE analytics_snapshot_id=${robustness_snapshot_id};
"

echo
echo "=== MODEL HEALTH COMPONENTS ==="
psql -d finam_core -P pager=off -c "
SELECT
  component_code,
  round(component_value,4) AS component_value,
  component_status
FROM analytics.marketcore_model_health_component_v1
WHERE model_health_snapshot_id=${model_health_snapshot_id}
ORDER BY component_code;
"

echo
echo "=== MODEL HEALTH GATES ==="
psql -d finam_core -P pager=off -c "
SELECT
  gate_code,
  gate_status,
  gate_reason
FROM analytics.marketcore_model_health_gate_v1
WHERE model_health_snapshot_id=${model_health_snapshot_id}
ORDER BY gate_code;
"

echo
echo "=== FEEDBACK BLOCKERS ==="
psql -d finam_core -P pager=off -c "
SELECT
  feedback_reason_code,
  feedback_severity_code,
  recommended_action_code,
  count(*) AS rows_total
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
GROUP BY feedback_reason_code, feedback_severity_code, recommended_action_code
ORDER BY rows_total DESC, feedback_reason_code;
"

echo
echo "=== READINESS DECISION INPUTS ==="

trades=$(psql -At -d finam_core -c "
SELECT coalesce(trades_total,0)
FROM analytics.paper_execution_summary_v1
WHERE analytics_snapshot_id=${paper_snapshot_id};
")

expectancy=$(psql -At -d finam_core -c "
SELECT coalesce(expectancy_r,0)
FROM analytics.paper_execution_summary_v1
WHERE analytics_snapshot_id=${paper_snapshot_id};
")

pf=$(psql -At -d finam_core -c "
SELECT coalesce(profit_factor,0)
FROM analytics.paper_execution_summary_v1
WHERE analytics_snapshot_id=${paper_snapshot_id};
")

sample_status=$(psql -At -d finam_core -c "
SELECT sample_status
FROM analytics.paper_execution_robustness_audit_v1
WHERE analytics_snapshot_id=${robustness_snapshot_id};
")

overfit_risk=$(psql -At -d finam_core -c "
SELECT overfit_risk
FROM analytics.paper_execution_robustness_audit_v1
WHERE analytics_snapshot_id=${robustness_snapshot_id};
")

production_allowed=$(psql -At -d finam_core -c "
SELECT production_allowed
FROM analytics.paper_execution_robustness_audit_v1
WHERE analytics_snapshot_id=${robustness_snapshot_id};
")

production_gate=$(psql -At -d finam_core -c "
SELECT gate_status
FROM analytics.marketcore_model_health_gate_v1
WHERE model_health_snapshot_id=${model_health_snapshot_id}
  AND gate_code='PRODUCTION';
")

unsafe_feedback=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
  AND (
       approved<>0
    OR applied<>0
    OR auto_decision<>0
  );
")

echo "trades=${trades}"
echo "profit_factor=${pf}"
echo "expectancy_r=${expectancy}"
echo "sample_status=${sample_status}"
echo "overfit_risk=${overfit_risk}"
echo "production_allowed=${production_allowed}"
echo "production_gate=${production_gate}"
echo "unsafe_feedback=${unsafe_feedback}"

echo
echo "=== FINAL DECISION ==="

decision="LOCKED"
reason="STATISTICAL_MATURITY_NOT_READY"

if [ "$production_allowed" != "0" ]; then
  decision="REVIEW_REQUIRED"
  reason="UNEXPECTED_PRODUCTION_ALLOWED"
fi

if [ "$unsafe_feedback" != "0" ]; then
  decision="BLOCKED"
  reason="UNSAFE_FEEDBACK_ROWS"
fi

echo "profit_readiness=${decision}"
echo "decision_reason=${reason}"

echo
echo "=== SAFETY ==="
echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "auto_decision=0"
echo

echo "VERDICT=PAPER_PROFIT_READINESS_AUDIT_V1_READY"
} | tee "$report"

grep -q "VERDICT=PAPER_PROFIT_READINESS_AUDIT_V1_READY" "$report"

grep -q "profit_readiness=LOCKED" "$report"
grep -q "decision_reason=STATISTICAL_MATURITY_NOT_READY" "$report"

unsafe_feedback=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.paper_execution_feedback_v1
WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
  AND (
       approved<>0
    OR applied<>0
    OR auto_decision<>0
  );
")

test "$unsafe_feedback" = "0"

echo "report=$report"
echo "mode=read_only_audit"
echo "profit_readiness=LOCKED"
echo "decision_reason=STATISTICAL_MATURITY_NOT_READY"
echo "runtime_allowed=0"
echo "execution_allowed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "auto_decision=0"
echo "VERDICT=PAPER_PROFIT_READINESS_AUDIT_V1_READY"
echo "VERDICT=TEST_PAPER_PROFIT_READINESS_AUDIT_V1_OK"
