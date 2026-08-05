#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_registry_v3"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER REGISTRY V3 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_decision_owner_registry_v2.sh
scripts/test_regime_owner_confirmation_v1.sh

"$PYTHON" scripts/build_decision_owner_registry_v3.py |
  tee "$LOG"

for file in \
  "$OUT/decision_owner_registry_v3.tsv" \
  "$OUT/decision_owner_edges_v3.tsv" \
  "$OUT/deferred_stages_v3.tsv" \
  "$OUT/deferred_scopes_v3.tsv" \
  "$OUT/decision_owner_contract_v3.txt" \
  "$OUT/unresolved_v3.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

OWNER_COUNT="$(
  tail -n +2 "$OUT/decision_owner_registry_v3.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

REGIME_COUNT="$(
  awk -F '\t' '
      NR > 1 && $1 == "REGIME" {
          count++
      }
      END {
          print count + 0
      }
  ' "$OUT/decision_owner_registry_v3.tsv"
)"

EDGE_COUNT="$(
  tail -n +2 "$OUT/decision_owner_edges_v3.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DEFERRED_STAGE_COUNT="$(
  tail -n +2 "$OUT/deferred_stages_v3.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DEFERRED_SCOPE_COUNT="$(
  tail -n +2 "$OUT/deferred_scopes_v3.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved_v3.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "confirmed_owner_count=$OWNER_COUNT"
echo "confirmed_regime_owner_count=$REGIME_COUNT"
echo "ownership_edge_count=$EDGE_COUNT"
echo "deferred_stage_count=$DEFERRED_STAGE_COUNT"
echo "deferred_scope_count=$DEFERRED_SCOPE_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$OWNER_COUNT" -eq 9 ]]
[[ "$REGIME_COUNT" -eq 1 ]]
[[ "$EDGE_COUNT" -eq 10 ]]
[[ "$DEFERRED_STAGE_COUNT" -eq 4 ]]
[[ "$DEFERRED_SCOPE_COUNT" -eq 1 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fq \
  $'REGIME\tMARKET_REGIME:BR\t' \
  "$OUT/decision_owner_registry_v3.tsv"

grep -Fq \
  "BRRegimeLayer.evaluate" \
  "$OUT/decision_owner_registry_v3.tsv"

grep -Fq \
  $'REGIME\tMARKET_REGIME:GENERIC\tDEFERRED' \
  "$OUT/deferred_scopes_v3.tsv"

grep -Fq \
  "REGIME_GENERIC_OWNER=DEFERRED" \
  "$OUT/decision_owner_contract_v3.txt"

awk -F '\t' '
    NR == 1 {
        next
    }

    $11 != "1" {
        print "ERROR=owner_not_confirmed:" $4
        exit 1
    }

    $12 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $4
        exit 1
    }
' "$OUT/decision_owner_registry_v3.tsv"

grep -Fq \
  "VERDICT=DECISION_OWNER_REGISTRY_V3_READY" \
  "$LOG"

echo "runtime_instrumentation=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_OWNER_REGISTRY_V3_OK"
