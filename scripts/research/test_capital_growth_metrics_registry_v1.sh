#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/capital_growth_metrics_registry_v1"
LOG="/tmp/test_capital_growth_metrics_registry_v1.log"

cd "$ROOT"

echo "=== TEST CAPITAL GROWTH METRICS REGISTRY V1 ==="

rm -rf "$OUT"
rm -f "$LOG"

"$PYTHON" \
  scripts/research/build_capital_growth_metrics_registry_v1.py |
tee "$LOG"

for file in \
  "$OUT/metrics.tsv" \
  "$OUT/metric_dependencies.tsv" \
  "$OUT/lifecycle_usage.tsv" \
  "$OUT/registry_contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

METRIC_COUNT="$(
  tail -n +2 "$OUT/metrics.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

DEPENDENCY_COUNT="$(
  tail -n +2 "$OUT/metric_dependencies.tsv" |
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

DUPLICATE_METRIC_CODE_COUNT="$(
  awk -F '\t' '
      NR > 1 {
          count[$1]++
      }

      END {
          duplicates = 0

          for (code in count) {
              if (count[code] > 1) {
                  duplicates += count[code] - 1
              }
          }

          print duplicates + 0
      }
  ' "$OUT/metrics.tsv"
)"

echo "metric_count=$METRIC_COUNT"
echo "dependency_count=$DEPENDENCY_COUNT"
echo "duplicate_metric_code_count=$DUPLICATE_METRIC_CODE_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$METRIC_COUNT" -eq 16 ]]
[[ "$DEPENDENCY_COUNT" -eq 16 ]]
[[ "$DUPLICATE_METRIC_CODE_COUNT" -eq 0 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

REQUIRED_METRICS=(
  NET_EXPECTANCY
  PROFIT_FACTOR
  MAX_DRAWDOWN
  RECOVERY_FACTOR
  EXPECTED_CAGR
  MAR_RATIO
  ULCER_INDEX
  RISK_OF_RUIN
  KELLY_FRACTION
  CAPITAL_EFFICIENCY
  ROBUSTNESS_SCORE
  LIQUIDITY_SCORE
  EXECUTION_QUALITY_SCORE
  CAPACITY_SCORE
  CORRELATION_PENALTY
  CAPITAL_GROWTH_SCORE
)

for metric in "${REQUIRED_METRICS[@]}"; do
    COUNT="$(
      awk -F '\t' \
        -v metric="$metric" '
          NR > 1 && $1 == metric {
              count++
          }

          END {
              print count + 0
          }
        ' "$OUT/metrics.tsv"
    )"

    echo "required_metric=$metric count=$COUNT"
    [[ "$COUNT" -eq 1 ]]
done

"$PYTHON" - "$OUT/metrics.tsv" <<'PY_CHECK'
from __future__ import annotations

import csv
import pathlib
import sys


path = pathlib.Path(sys.argv[1])

allowed_levels = {
    "PRIMARY",
    "DERIVED",
    "COMPOSITE",
}

allowed_directions = {
    "HIGHER_IS_BETTER",
    "LOWER_IS_BETTER",
    "HIGHER_IS_BETTER_WITH_CAP",
}

errors: list[str] = []

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as stream:
    rows = list(
        csv.DictReader(
            stream,
            delimiter="\t",
        )
    )

for row in rows:
    code = (row.get("metric_code") or "").strip()

    required_fields = (
        "metric_name_ru",
        "category",
        "metric_level",
        "formula",
        "unit",
        "direction",
        "minimum_sample",
        "calculation_window",
        "null_policy",
        "source_relation",
        "source_fields",
        "update_frequency",
        "lifecycle_usage",
        "normalization",
        "owner_stage",
        "version",
    )

    for field in required_fields:
        if not (row.get(field) or "").strip():
            errors.append(
                f"{code}:FIELD_MISSING:{field}"
            )

    if row.get("metric_level") not in allowed_levels:
        errors.append(
            f"{code}:INVALID_LEVEL"
        )

    if row.get("direction") not in allowed_directions:
        errors.append(
            f"{code}:INVALID_DIRECTION"
        )

    try:
        minimum_sample = int(
            row.get("minimum_sample") or ""
        )
    except ValueError:
        errors.append(
            f"{code}:INVALID_MINIMUM_SAMPLE"
        )
    else:
        if minimum_sample < 0:
            errors.append(
                f"{code}:NEGATIVE_MINIMUM_SAMPLE"
            )

if errors:
    for error in errors:
        print(f"ERROR={error}")

    raise SystemExit(1)

print("metric_contract_validation=OK")
PY_CHECK

for contract in \
  "PRIMARY_GOAL=MAXIMIZE_LONG_TERM_CAPITAL_GROWTH" \
  "DATABASE=POSTGRESQL_ONLY" \
  "METRIC_INLINE_CREATION_ALLOWED=0" \
  "METRIC_COUNT=16" \
  "CATEGORY_COUNT=7" \
  "PRIMARY_METRIC_COUNT=4" \
  "DERIVED_METRIC_COUNT=11" \
  "COMPOSITE_METRIC_COUNT=1" \
  "DEPENDENCY_COUNT=16" \
  "DUPLICATE_METRIC_CODE_COUNT=0" \
  "REQUIRED_METRIC_MISSING_COUNT=0" \
  "UNRESOLVED_COUNT=0" \
  "CAPITAL_GROWTH_SCORE_FORMULA_STATUS=DEFERRED_TO_FORMULA_REGISTRY_V1" \
  "RUNTIME_CHANGED=0" \
  "EXECUTION_CHANGED=0" \
  "ORDERS_CHANGED=0" \
  "FILLS_CHANGED=0" \
  "MICRO_LIVE_ALLOWED=0"
do
    grep -Fqx \
      "$contract" \
      "$OUT/registry_contract.txt" || {
          echo "ERROR=contract_missing:$contract"
          exit 1
      }
done

grep -Fq \
  "VERDICT=CAPITAL_GROWTH_METRICS_REGISTRY_V1_READY" \
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
          scripts/research/build_capital_growth_metrics_registry_v1.py ||
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
echo "VERDICT=TEST_CAPITAL_GROWTH_METRICS_REGISTRY_V1_OK"
