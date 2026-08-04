#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/decision_owner_registry_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST DECISION OWNER REGISTRY V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/build_decision_owner_registry_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/decision_owner_registry_v1.tsv"
  "$OUT/decision_owner_edges_v1.tsv"
  "$OUT/decision_owner_contract_v1.txt"
  "$OUT/deferred_stages_v1.tsv"
  "$OUT/unresolved_v1.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

OWNER_COUNT="$(
  tail -n +2 \
    "$OUT/decision_owner_registry_v1.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DEFERRED_COUNT="$(
  tail -n +2 \
    "$OUT/deferred_stages_v1.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

UNRESOLVED_COUNT="$(
  tail -n +2 \
    "$OUT/unresolved_v1.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "confirmed_owner_count=$OWNER_COUNT"
echo "deferred_stage_count=$DEFERRED_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$OWNER_COUNT" -eq 4 ]]
[[ "$DEFERRED_COUNT" -eq 6 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -q \
  $'^RISK\tDECISION_GATE\t.*portfolio_risk_gate.py\tPortfolioRiskGate.check\t' \
  "$OUT/decision_owner_registry_v1.tsv"

grep -q \
  $'^RUNTIME\tDECISION_GATE\t.*paper_pipeline.py\t_execute_br_signal_in_paper\t' \
  "$OUT/decision_owner_registry_v1.tsv"

grep -q \
  $'^EXECUTION\tEXECUTION_DOMAIN_STATUS\t.*execution_dispatcher.py\tExecutionDispatcher\t' \
  "$OUT/decision_owner_registry_v1.tsv"

grep -q \
  $'^BROKER\tBROKER_PROTOCOL_RESULT\t.*orders_client.py\tFinamOrdersClient\t' \
  "$OUT/decision_owner_registry_v1.tsv"

awk -F '\t' '
    NR == 1 {
        next
    }

    $9 != "1" {
        print "ERROR=owner_not_confirmed:" $1
        exit 1
    }

    $10 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $1
        exit 1
    }
' "$OUT/decision_owner_registry_v1.tsv"

DUPLICATE_COUNT="$(
  tail -n +2 \
    "$OUT/decision_owner_registry_v1.tsv" |
  cut -f1 |
  sort |
  uniq -d |
  wc -l |
  tr -d ' '
)"

echo "duplicate_stage_owner_count=$DUPLICATE_COUNT"
[[ "$DUPLICATE_COUNT" -eq 0 ]]

grep -q \
  '^CONFIRMED_OWNER_COUNT=4$' \
  "$OUT/decision_owner_contract_v1.txt"

grep -q \
  '^DUPLICATE_STAGE_OWNER_COUNT=0$' \
  "$OUT/decision_owner_contract_v1.txt"

grep -q \
  '^DEFERRED_STAGE_COUNT=6$' \
  "$OUT/decision_owner_contract_v1.txt"

grep -q \
  '^UNRESOLVED_COUNT=0$' \
  "$OUT/decision_owner_contract_v1.txt"

grep -q \
  '^RUNTIME_INSTRUMENTATION=0$' \
  "$OUT/decision_owner_contract_v1.txt"

grep -q \
  '^confirmed_owner_count=4$' \
  "$LOG"

grep -q \
  '^duplicate_stage_owner_count=0$' \
  "$LOG"

grep -q \
  '^unresolved_count=0$' \
  "$LOG"

grep -q \
  '^VERDICT=DECISION_OWNER_REGISTRY_V1_READY$' \
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
echo "broker_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_DECISION_OWNER_REGISTRY_V1_OK"
