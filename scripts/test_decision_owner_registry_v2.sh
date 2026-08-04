#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_registry_v2"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER REGISTRY V2 ==="

REQUIRED_FILES=(
  scripts/build_decision_owner_registry_v2.py
  scripts/test_decision_owner_registry_v1.sh
  scripts/test_strategy_owner_confirmation_v1.sh
)

for file in "${REQUIRED_FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=required_file_missing:$file"
        exit 1
    }
done

rm -rf "$OUT"
mkdir -p "$OUT"

scripts/test_decision_owner_registry_v1.sh
scripts/test_strategy_owner_confirmation_v1.sh

"$PYTHON" \
  scripts/build_decision_owner_registry_v2.py \
  | tee "$LOG"

FILES=(
  "$OUT/decision_owner_registry_v2.tsv"
  "$OUT/decision_owner_edges_v2.tsv"
  "$OUT/decision_owner_contract_v2.txt"
  "$OUT/deferred_stages_v2.tsv"
  "$OUT/unresolved_v2.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

OWNER_COUNT="$(
  tail -n +2 "$OUT/decision_owner_registry_v2.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

STRATEGY_OWNER_COUNT="$(
  awk -F '\t' '
      NR > 1 && $1 == "STRATEGY" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/decision_owner_registry_v2.tsv"
)"

STRATEGY_FAMILY_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $1 == "STRATEGY" &&
      $9 != "" {
          families[$9] = 1
      }

      END {
          print length(families)
      }
  ' "$OUT/decision_owner_registry_v2.tsv"
)"

DEFERRED_COUNT="$(
  tail -n +2 "$OUT/deferred_stages_v2.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

EDGE_COUNT="$(
  tail -n +2 "$OUT/decision_owner_edges_v2.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved_v2.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "confirmed_owner_count=$OWNER_COUNT"
echo "strategy_owner_count=$STRATEGY_OWNER_COUNT"
echo "strategy_family_count=$STRATEGY_FAMILY_COUNT"
echo "deferred_stage_count=$DEFERRED_COUNT"
echo "ownership_edge_count=$EDGE_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$OWNER_COUNT" -eq 8 ]]
[[ "$STRATEGY_OWNER_COUNT" -eq 4 ]]
[[ "$STRATEGY_FAMILY_COUNT" -eq 3 ]]
[[ "$DEFERRED_COUNT" -eq 5 ]]
[[ "$EDGE_COUNT" -eq 8 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

for symbol in \
  "BrConservativeBreakout.on_signal_bar" \
  "NgConservativeBreakoutM1.on_signal_bar" \
  "MeanReversionEquity.on_quote" \
  "VolatilityBreakoutEquity.on_quote" \
  "PortfolioRiskGate.check" \
  "_execute_br_signal_in_paper" \
  "ExecutionDispatcher" \
  "FinamOrdersClient"
do
    grep -Fq \
      "$symbol" \
      "$OUT/decision_owner_registry_v2.tsv" || {
          echo "ERROR=owner_symbol_missing:$symbol"
          exit 1
      }
done

grep -Fq \
  $'STRATEGY\tTRADE_INTENT:BR\t' \
  "$OUT/decision_owner_registry_v2.tsv"

grep -Fq \
  $'STRATEGY\tTRADE_INTENT:NG\t' \
  "$OUT/decision_owner_registry_v2.tsv"

grep -Fq \
  $'STRATEGY\tTRADE_INTENT:EQUITY\t' \
  "$OUT/decision_owner_registry_v2.tsv"

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
' "$OUT/decision_owner_registry_v2.tsv"

DUPLICATE_IDENTITY_COUNT="$(
  tail -n +2 "$OUT/decision_owner_registry_v2.tsv" |
  awk -F '\t' '
      {
          key = $1 FS $2 FS $4
          count[key]++
      }

      END {
          duplicates = 0

          for (key in count) {
              if (count[key] > 1) {
                  duplicates++
              }
          }

          print duplicates
      }
  '
)"

echo "duplicate_owner_identity_count=$DUPLICATE_IDENTITY_COUNT"
[[ "$DUPLICATE_IDENTITY_COUNT" -eq 0 ]]

for contract in \
  "CONFIRMED_OWNER_COUNT=8" \
  "BASE_OWNER_COUNT=4" \
  "STRATEGY_OWNER_COUNT=4" \
  "STRATEGY_FAMILY_COUNT=3" \
  "DEFERRED_STAGE_COUNT=5" \
  "DUPLICATE_OWNER_IDENTITY_COUNT=0" \
  "UNRESOLVED_COUNT=0" \
  "RUNTIME_INSTRUMENTATION=0"
do
    grep -Fq \
      "$contract" \
      "$OUT/decision_owner_contract_v2.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "VERDICT=DECISION_OWNER_REGISTRY_V2_READY" \
  "$LOG"

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

echo "owner_assignment_performed=1"
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
echo "VERDICT=TEST_DECISION_OWNER_REGISTRY_V2_OK"
