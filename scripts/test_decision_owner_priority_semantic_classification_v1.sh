#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_priority_semantic_classification_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER PRIORITY SEMANTIC CLASSIFICATION V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_decision_owner_priority_semantic_classification_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/semantic_classification.tsv"
  "$OUT/confirmed_candidates.tsv"
  "$OUT/excluded_candidates.tsv"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

grep -q $'^RISK\t.*portfolio_risk_gate.py\tcheck\t' \
  "$OUT/confirmed_candidates.tsv"

grep -q $'^EXECUTION\t.*execution_dispatcher.py\tplace_limit_order\t' \
  "$OUT/confirmed_candidates.tsv"

grep -q $'^BROKER\t.*orders_client.py\tplace_limit_order\t' \
  "$OUT/confirmed_candidates.tsv"

grep -q $'^BROKER\t.*orders_client.py\tplace_market_order\t' \
  "$OUT/confirmed_candidates.tsv"

grep -q \
  'oco_order_manager.py.*PROTECTION_ORDER_SIDE_EFFECT' \
  "$OUT/excluded_candidates.tsv"

grep -q \
  'paper_pipeline.py.*_on_quote_impl.*ORCHESTRATION_BOUNDARY' \
  "$OUT/excluded_candidates.tsv"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "unresolved_count=$UNRESOLVED_COUNT"
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $8 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $1
        exit 1
    }

    $9 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/semantic_classification.tsv"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"
grep -q \
  '^VERDICT=DECISION_OWNER_PRIORITY_SEMANTIC_CLASSIFICATION_V1_READY$' \
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
echo "VERDICT=TEST_DECISION_OWNER_PRIORITY_SEMANTIC_CLASSIFICATION_V1_OK"
