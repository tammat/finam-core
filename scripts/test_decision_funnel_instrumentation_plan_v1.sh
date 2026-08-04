#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_funnel_instrumentation_plan_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION FUNNEL INSTRUMENTATION PLAN V1 ==="

mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_decision_funnel_instrumentation_plan_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/instrumentation_plan.txt"
  "$OUT/instrumentation_points.tsv"
  "$OUT/signal_id_candidates.tsv"
  "$OUT/transaction_boundaries.tsv"
  "$OUT/recorder_policy.tsv"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

grep -q '^STATUS=PLAN_ONLY$' \
  "$OUT/instrumentation_plan.txt"

grep -q '^RUNTIME_INSTRUMENTATION=0$' \
  "$OUT/instrumentation_plan.txt"

grep -q '^RECORDER_FAILURE_POLICY=FAIL_OPEN$' \
  "$OUT/instrumentation_plan.txt"

grep -q '^MUST_NOT_SEND_ORDER=1$' \
  "$OUT/instrumentation_plan.txt"

grep -q '^MUST_NOT_CHANGE_RUNTIME=1$' \
  "$OUT/instrumentation_plan.txt"

grep -q '^MUST_NOT_SHARE_TRADING_TRANSACTION=1$' \
  "$OUT/instrumentation_plan.txt"

for stage in \
  MARKET_DATA \
  STRATEGY \
  REGIME \
  EDGE \
  RISK \
  PORTFOLIO \
  RUNTIME \
  EXECUTION \
  BROKER \
  FILL
do
    grep -q "^\[$stage\]$" \
      "$OUT/instrumentation_plan.txt"

    grep -q "^$stage"$'\t' \
      "$OUT/recorder_policy.tsv"
done

POLICY_COUNT="$(
  tail -n +2 "$OUT/recorder_policy.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "recorder_policy_count=$POLICY_COUNT"
[[ "$POLICY_COUNT" -eq 10 ]]

awk -F '\t' '
    {
        for (column = 1; column <= NF; column++) {
            sub(/\r$/, "", $column)
        }
    }

    NR == 1 {
        next
    }

    $2 != "FAIL_OPEN" {
        print "ERROR=non_fail_open_stage:" $1
        exit 1
    }

    $4 != "0" || $5 != "0" || $6 != "0" || $7 != "0" {
        print             "ERROR=recorder_authority_violation:"             $1             ":decision=" $4             ":order=" $5             ":runtime=" $6             ":enabled=" $7
        exit 1
    }
' "$OUT/recorder_policy.tsv"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

for marker in \
  "INSERT INTO" \
  "UPDATE " \
  "DELETE FROM" \
  "TRUNCATE " \
  "DROP TABLE" \
  "ALTER TABLE" \
  "systemctl restart" \
  "systemctl start" \
  "systemctl stop" \
  "send_order(" \
  "place_order(" \
  "submit_order("
do
    count="$(
      {
        grep -F "$marker" \
          scripts/audit_decision_funnel_instrumentation_plan_v1.py \
          2>/dev/null || true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_action_marker=$marker count=$count"
    [[ "$count" -eq 0 ]]
done

grep -q \
  '^VERDICT=DECISION_FUNNEL_INSTRUMENTATION_PLAN_V1_READY$' \
  "$LOG"

echo "plan_only=1"
echo "recorder_failure_policy=FAIL_OPEN"
echo "writes_performed=0"
echo "db_writes_performed=0"
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_FUNNEL_INSTRUMENTATION_PLAN_V1_OK"
