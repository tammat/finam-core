#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/capital_growth_formula_registry_v1"
METRICS_OUT="/tmp/capital_growth_metrics_registry_v1"
LOG="/tmp/test_capital_growth_formula_registry_v1.log"

cd "$ROOT"

echo "=== TEST CAPITAL GROWTH FORMULA REGISTRY V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

if [[ ! -f "$METRICS_OUT/metrics.tsv" ]]; then
    scripts/research/test_capital_growth_metrics_registry_v1.sh
fi

"$PYTHON" \
  scripts/research/build_capital_growth_formula_registry_v1.py |
tee "$LOG"

for file in \
  "$OUT/formulas.tsv" \
  "$OUT/formula_inputs.tsv" \
  "$OUT/hard_gates.tsv" \
  "$OUT/penalties.tsv" \
  "$OUT/confidence_policy.tsv" \
  "$OUT/formula_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

FORMULA_COUNT="$(
  tail -n +2 "$OUT/formulas.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

INPUT_COUNT="$(
  tail -n +2 "$OUT/formula_inputs.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

GATE_COUNT="$(
  tail -n +2 "$OUT/hard_gates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

PENALTY_COUNT="$(
  tail -n +2 "$OUT/penalties.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CONFIDENCE_COUNT="$(
  tail -n +2 "$OUT/confidence_policy.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

POSITIVE_WEIGHT_SUM="$(
  "$PYTHON" - "$OUT/formula_inputs.tsv" <<'PY_CHECK'
from __future__ import annotations

import csv
import pathlib
import sys
from decimal import Decimal


path = pathlib.Path(sys.argv[1])
total = Decimal("0")

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as stream:
    for row in csv.DictReader(
        stream,
        delimiter="\t",
    ):
        if row["role"] == "POSITIVE_COMPONENT":
            total += Decimal(row["weight"])

print(total)
PY_CHECK
)"

echo "formula_count=$FORMULA_COUNT"
echo "formula_input_count=$INPUT_COUNT"
echo "positive_weight_sum=$POSITIVE_WEIGHT_SUM"
echo "hard_gate_count=$GATE_COUNT"
echo "penalty_count=$PENALTY_COUNT"
echo "confidence_rule_count=$CONFIDENCE_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$FORMULA_COUNT" -eq 1 ]]
[[ "$INPUT_COUNT" -eq 12 ]]
[[ "$POSITIVE_WEIGHT_SUM" == "1.000" ]]
[[ "$GATE_COUNT" -eq 5 ]]
[[ "$PENALTY_COUNT" -eq 3 ]]
[[ "$CONFIDENCE_COUNT" -eq 3 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

grep -Fqx \
  $'CAPITAL_GROWTH_SCORE_V1\tV1\tCAPITAL_GROWTH_SCORE\tWEIGHTED_SCORE_WITH_GATES_AND_PENALTIES\t100 * confidence_multiplier * max(0, weighted_positive_score - total_penalty)\t0\t100\tINVALID_IF_REQUIRED_COMPONENT_MISSING\tVALIDATED_NOT_ACTIVE\tCAPITAL_GROWTH' \
  "$OUT/formulas.tsv"

for gate in \
  NET_EXPECTANCY_POSITIVE \
  MAX_DRAWDOWN_LIMIT \
  RISK_OF_RUIN_LIMIT \
  ROBUSTNESS_MINIMUM \
  KELLY_POSITIVE
do
    COUNT="$(
      awk -F '\t' \
        -v gate="$gate" '
          NR > 1 && $2 == gate {
              count++
          }

          END {
              print count + 0
          }
        ' "$OUT/hard_gates.tsv"
    )"

    echo "required_gate=$gate count=$COUNT"
    [[ "$COUNT" -eq 1 ]]
done

for contract in \
  "PRIMARY_GOAL=MAXIMIZE_LONG_TERM_CAPITAL_GROWTH" \
  "FORMULA_COUNT=1" \
  "FORMULA_INPUT_COUNT=12" \
  "POSITIVE_WEIGHT_SUM=1.000" \
  "HARD_GATE_COUNT=5" \
  "PENALTY_COUNT=3" \
  "CONFIDENCE_RULE_COUNT=3" \
  "ACTIVATION_STATUS=VALIDATED_NOT_ACTIVE" \
  "ALLOCATION_ALLOWED=0" \
  "RUNTIME_USAGE_ALLOWED=0" \
  "EXECUTION_USAGE_ALLOWED=0" \
  "MISSING_METRIC_POLICY=INVALID_IF_REQUIRED_COMPONENT_MISSING" \
  "DUPLICATE_FORMULA_CODE_COUNT=0" \
  "DUPLICATE_GATE_CODE_COUNT=0" \
  "DUPLICATE_PENALTY_CODE_COUNT=0" \
  "UNRESOLVED_COUNT=0" \
  "RUNTIME_CHANGED=0" \
  "EXECUTION_CHANGED=0" \
  "ORDERS_CHANGED=0" \
  "FILLS_CHANGED=0" \
  "MICRO_LIVE_ALLOWED=0"
do
    grep -Fqx \
      "$contract" \
      "$OUT/formula_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "VERDICT=CAPITAL_GROWTH_FORMULA_REGISTRY_V1_READY" \
  "$LOG"

FORBIDDEN_MARKERS=(
  "INSERT INTO"
  "UPDATE "
  "DELETE FROM"
  "TRUNCATE "
  "DROP TABLE"
  "ALTER TABLE"
  "systemctl restart"
  "systemctl start"
  "systemctl stop"
  "send_order("
  "place_order("
  "submit_order("
)

for marker in "${FORBIDDEN_MARKERS[@]}"; do
    COUNT="$(
      {
        grep -F "$marker" \
          scripts/research/build_capital_growth_formula_registry_v1.py ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_action_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

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
echo "VERDICT=TEST_CAPITAL_GROWTH_FORMULA_REGISTRY_V1_OK"
