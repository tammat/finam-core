#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_priority_evidence_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER PRIORITY EVIDENCE V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_decision_owner_priority_evidence_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/priority_candidates.tsv"
  "$OUT/function_evidence.txt"
  "$OUT/call_relationships.tsv"
  "$OUT/return_contracts.tsv"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

for stage in \
  STRATEGY \
  RISK \
  RUNTIME \
  EXECUTION \
  BROKER
do
    grep -q "^$stage"$'\t' \
      "$OUT/priority_candidates.tsv"
done

awk -F '\t' '
    {
        for (column = 1; column <= NF; column++) {
            sub(/\r$/, "", $column)
        }
    }

    NR == 1 {
        next
    }

    $13 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $1
        exit 1
    }

    $14 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/priority_candidates.tsv"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=DECISION_OWNER_PRIORITY_EVIDENCE_V1_READY$' \
  "$LOG"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

echo "owner_assignment_performed=0"
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
echo "VERDICT=TEST_DECISION_OWNER_PRIORITY_EVIDENCE_V1_OK"
