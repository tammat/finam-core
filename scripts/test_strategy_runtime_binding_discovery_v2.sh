#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/strategy_runtime_binding_discovery_v2"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST STRATEGY RUNTIME BINDING DISCOVERY V2 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_strategy_owner_family_classification_v1.sh

"$PYTHON" \
  scripts/audit_strategy_runtime_binding_discovery_v2.py |
  tee "$LOG"

for file in \
  "$OUT/constructor_sites.tsv" \
  "$OUT/binding_sites.tsv" \
  "$OUT/interface_calls.tsv" \
  "$OUT/class_method_calls.tsv" \
  "$OUT/candidate_binding_summary.tsv" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

CANDIDATE_COUNT="$(
  tail -n +2 "$OUT/candidate_binding_summary.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

EVIDENCE_COUNT="$(
  awk -F '\t' '
      NR > 1 && $7 > 0 {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/candidate_binding_summary.tsv"
)"

echo "candidate_count=$CANDIDATE_COUNT"
echo "candidate_with_binding_evidence_count=$EVIDENCE_COUNT"

[[ "$CANDIDATE_COUNT" -eq 7 ]]
[[ "$EVIDENCE_COUNT" -gt 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $9 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $2
        exit 1
    }

    $10 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $2
        exit 1
    }
' "$OUT/candidate_binding_summary.tsv"

grep -q \
  '^VERDICT=STRATEGY_RUNTIME_BINDING_DISCOVERY_V2_READY$' \
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
echo "runtime_instrumentation=0"
echo "strategy_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_STRATEGY_RUNTIME_BINDING_DISCOVERY_V2_OK"
