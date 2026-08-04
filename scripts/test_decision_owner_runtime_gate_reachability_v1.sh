#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_runtime_gate_reachability_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER RUNTIME GATE REACHABILITY V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_decision_owner_runtime_gate_reachability_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/runtime_gate_callers.tsv"
  "$OUT/risk_gate_bindings.tsv"
  "$OUT/execution_path.tsv"
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
  '^pipeline_to_runtime_gate_classification=' \
  "$LOG"

awk -F '\t' '
    NR == 1 {
        next
    }

    $6 != "0" || $7 != "0" {
        print "ERROR=owner_or_runtime_enabled"
        exit 1
    }
' "$OUT/execution_path.tsv"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=DECISION_OWNER_RUNTIME_GATE_REACHABILITY_V1_READY$' \
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
echo "VERDICT=TEST_DECISION_OWNER_RUNTIME_GATE_REACHABILITY_V1_OK"
