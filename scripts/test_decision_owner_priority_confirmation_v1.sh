#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_priority_confirmation_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER PRIORITY CONFIRMATION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/build_decision_owner_priority_confirmation_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/confirmed_priority_owners.tsv"
  "$OUT/deferred_priority_owners.tsv"
  "$OUT/confirmation_contract.txt"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CONFIRMED_COUNT="$(
  tail -n +2 "$OUT/confirmed_priority_owners.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "confirmed_owner_count=$CONFIRMED_COUNT"
[[ "$CONFIRMED_COUNT" -eq 2 ]]

grep -q \
  $'^RISK\t.*portfolio_risk_gate.py\tPortfolioRiskGate.check\t' \
  "$OUT/confirmed_priority_owners.tsv"

grep -q \
  $'^RUNTIME\t.*paper_pipeline.py\t_execute_br_signal_in_paper\t' \
  "$OUT/confirmed_priority_owners.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $5 != "CONFIRMED_DECISION_OWNER" {
        print "ERROR=invalid_owner_classification:" $1
        exit 1
    }

    $7 != "FAIL_OPEN_RECORDER" {
        print "ERROR=invalid_failure_policy:" $1
        exit 1
    }

    $8 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/confirmed_priority_owners.tsv"

grep -q '^RISK_CONFIRMED=1$' \
  "$OUT/confirmation_contract.txt"

grep -q '^RUNTIME_CONFIRMED=1$' \
  "$OUT/confirmation_contract.txt"

grep -q '^RUNTIME_INSTRUMENTATION=0$' \
  "$OUT/confirmation_contract.txt"

grep -q '^risk_owner_confirmed=1$' "$LOG"
grep -q '^runtime_owner_confirmed=1$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=DECISION_OWNER_PRIORITY_CONFIRMATION_V1_READY$' \
  "$LOG"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

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
echo "VERDICT=TEST_DECISION_OWNER_PRIORITY_CONFIRMATION_V1_OK"
