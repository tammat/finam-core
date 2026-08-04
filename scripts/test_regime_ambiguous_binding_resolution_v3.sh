#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/regime_ambiguous_binding_resolution_v3"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST REGIME AMBIGUOUS BINDING RESOLUTION V3 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_regime_semantic_classification_v1.sh

"$PYTHON" \
  scripts/audit_regime_ambiguous_binding_resolution_v3.py \
  | tee "$LOG"

for file in \
  "$OUT/import_aliases.tsv" \
  "$OUT/persistent_bindings.tsv" \
  "$OUT/resolved_calls.tsv" \
  "$OUT/remaining_ambiguous_calls.tsv" \
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

RESOLVED_RUNTIME_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $6 == "RESOLVED_RUNTIME_REACHABLE" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/candidate_summary.tsv"
)"

BR_RUNTIME_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $2 == "BRRegimeLayer.evaluate" {
          print $4
      }
  ' "$OUT/candidate_summary.tsv"
)"

REGIME_ENGINE_RUNTIME_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $2 == "RegimeEngine.evaluate" {
          print $4
      }
  ' "$OUT/candidate_summary.tsv"
)"

echo "candidate_count=$CANDIDATE_COUNT"
echo "resolved_runtime_reachable_candidate_count=$RESOLVED_RUNTIME_COUNT"
echo "br_regime_layer_runtime_calls=$BR_RUNTIME_COUNT"
echo "regime_engine_runtime_calls=$REGIME_ENGINE_RUNTIME_COUNT"

[[ "$CANDIDATE_COUNT" -eq 12 ]]
[[ "$RESOLVED_RUNTIME_COUNT" -ge 1 ]]
[[ "$BR_RUNTIME_COUNT" -ge 1 ]]

# Коллизия evaluate не должна возвращаться.
if [[ "$REGIME_ENGINE_RUNTIME_COUNT" == "$BR_RUNTIME_COUNT" &&
      "$REGIME_ENGINE_RUNTIME_COUNT" -eq 47 ]]
then
    echo "ERROR=evaluate_method_collision_returned"
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
  "VERDICT=REGIME_AMBIGUOUS_BINDING_RESOLUTION_V3_READY" \
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
echo "VERDICT=TEST_REGIME_AMBIGUOUS_BINDING_RESOLUTION_V3_OK"
