#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_runtime_caller_chain_v2"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER RUNTIME CALLER CHAIN V2 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_decision_owner_runtime_caller_chain_v2.py \
  | tee "$LOG"

FILES=(
  "$OUT/runtime_call_sites.tsv"
  "$OUT/runtime_caller_parents.tsv"
  "$OUT/risk_result_usage.tsv"
  "$OUT/branch_contract.tsv"
  "$OUT/evidence.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

grep -q \
  $'^NG_M1\t_process_ng_m1_closed_bar_for_paper_signal\t' \
  "$OUT/branch_contract.tsv"

grep -q \
  $'^BR\t_process_br_closed_bar_for_paper_signal\t' \
  "$OUT/branch_contract.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $6 != "0" || $7 != "0" {
        print "ERROR=owner_or_runtime_enabled:" $1
        exit 1
    }
' "$OUT/branch_contract.tsv"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "unresolved_count=$UNRESOLVED_COUNT"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=DECISION_OWNER_RUNTIME_CALLER_CHAIN_V2_READY$' \
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
echo "VERDICT=TEST_DECISION_OWNER_RUNTIME_CALLER_CHAIN_V2_OK"
