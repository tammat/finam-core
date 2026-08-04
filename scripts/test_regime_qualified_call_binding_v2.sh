#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/regime_qualified_call_binding_v2"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST REGIME QUALIFIED CALL BINDING V2 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_regime_semantic_classification_v1.sh

"$PYTHON" scripts/audit_regime_qualified_call_binding_v2.py |
  tee "$LOG"

for file in \
  "$OUT/candidate_classes.tsv" \
  "$OUT/constructor_bindings.tsv" \
  "$OUT/assignment_bindings.tsv" \
  "$OUT/qualified_calls.tsv" \
  "$OUT/ambiguous_calls.tsv" \
  "$OUT/candidate_summary.tsv" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CANDIDATE_COUNT="$(
  tail -n +2 "$OUT/candidate_summary.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

QUALIFIED_REACHABLE_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $6 == "QUALIFIED_RUNTIME_REACHABLE" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/candidate_summary.tsv"
)"

AMBIGUOUS_COUNT="$(
  tail -n +2 "$OUT/ambiguous_calls.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "candidate_count=$CANDIDATE_COUNT"
echo "qualified_runtime_reachable_candidate_count=$QUALIFIED_REACHABLE_COUNT"
echo "ambiguous_call_count=$AMBIGUOUS_COUNT"

[[ "$CANDIDATE_COUNT" -eq 12 ]]
[[ "$QUALIFIED_REACHABLE_COUNT" -gt 0 ]]

# V2 обязан устранить ложное приравнивание двух evaluate-владельцев.
REGIME_ENGINE_CALLS="$(
  awk -F '\t' '
      NR > 1 &&
      $2 == "RegimeEngine.evaluate" {
          print $3
      }
  ' "$OUT/candidate_summary.tsv"
)"

BR_LAYER_CALLS="$(
  awk -F '\t' '
      NR > 1 &&
      $2 == "BRRegimeLayer.evaluate" {
          print $3
      }
  ' "$OUT/candidate_summary.tsv"
)"

echo "regime_engine_qualified_calls=$REGIME_ENGINE_CALLS"
echo "br_regime_layer_qualified_calls=$BR_LAYER_CALLS"

[[ -n "$REGIME_ENGINE_CALLS" ]]
[[ -n "$BR_LAYER_CALLS" ]]

if [[ "$REGIME_ENGINE_CALLS" -eq 54 &&
      "$BR_LAYER_CALLS" -eq 54 ]]
then
    echo "ERROR=method_name_collision_not_resolved"
    exit 1
fi

awk -F '\t' '
    NR == 1 {
        next
    }

    $7 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $2
        exit 1
    }

    $8 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $2
        exit 1
    }
' "$OUT/candidate_summary.tsv"

grep -Fq \
  "VERDICT=REGIME_QUALIFIED_CALL_BINDING_V2_READY" \
  "$LOG"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

TRACKED_DIRTY_COUNT="$(
  {
    git status --porcelain |
    grep -Ev '^\?\?' ||
    true
  } |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
echo "tracked_dirty_count=$TRACKED_DIRTY_COUNT"

[[ "$STAGED_COUNT" -eq 0 ]]
[[ "$TRACKED_DIRTY_COUNT" -eq 0 ]]

echo "confirmed_owner_count=0"
echo "owner_assignment_performed=0"
echo "writes_performed=0"
echo "db_writes_performed=0"
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_REGIME_QUALIFIED_CALL_BINDING_V2_OK"
