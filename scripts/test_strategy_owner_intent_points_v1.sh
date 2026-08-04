#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
OUT="/tmp/strategy_owner_intent_points_v1"
LOG="$OUT/test_output.log"

cd "$ROOT"

echo "=== TEST STRATEGY OWNER INTENT POINTS V1 ==="

rm -rf "$OUT"
mkdir -p "$OUT"

"$PYTHON" \
  scripts/audit_strategy_owner_intent_points_v1.py \
  | tee "$LOG"

FILES=(
  "$OUT/strategy_files.tsv"
  "$OUT/strategy_methods.tsv"
  "$OUT/signal_constructors.tsv"
  "$OUT/signal_returns.tsv"
  "$OUT/direction_assignments.tsv"
  "$OUT/strategy_calls.tsv"
  "$OUT/owner_candidates.tsv"
  "$OUT/excluded_candidates.tsv"
  "$OUT/evidence.txt"
  "$OUT/unresolved.tsv"
)

for file in "${FILES[@]}"; do
    [[ -f "$file" ]] || {
        echo "ERROR=output_missing:$file"
        exit 1
    }
done

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

CANDIDATE_COUNT="$(
  tail -n +2 "$OUT/owner_candidates.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

TRADE_INTENT_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $14 == "TRADE_INTENT_OWNER_CANDIDATE" {
          count++
      }

      END {
          print count + 0
      }
  ' "$OUT/owner_candidates.tsv"
)"

echo "owner_candidate_count=$CANDIDATE_COUNT"
echo "trade_intent_owner_candidate_count=$TRADE_INTENT_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$UNRESOLVED_COUNT" -eq 0 ]]

# Оркестратор и downstream-владельцы не могут стать Strategy Owner.
KNOWN_OWNER_VIOLATIONS="$(
  awk -F '\t' '
      NR == 1 {
          next
      }

      $14 != "TRADE_INTENT_OWNER_CANDIDATE" {
          next
      }

      $5 == "_on_quote_impl" ||
      $5 == "_execute_br_signal_in_paper" ||
      $5 ~ /ExecutionDispatcher/ ||
      $5 ~ /PortfolioRiskGate/ ||
      $5 ~ /FinamOrdersClient/ {
          print $5
      }
  ' "$OUT/owner_candidates.tsv"
)"

if [[ -n "$KNOWN_OWNER_VIOLATIONS" ]]; then
    echo "ERROR=known_non_strategy_owner_selected"
    printf '%s\n' "$KNOWN_OWNER_VIOLATIONS"
    exit 1
fi

# Equity-класс не должен классифицироваться как BR из-за слова breakout.
FALSE_BR_EQUITY_COUNT="$(
  "$PYTHON" - "$OUT/owner_candidates.tsv" <<'PY_CHECK'
from __future__ import annotations

import csv
import pathlib
import sys


path = pathlib.Path(sys.argv[1])
count = 0

with path.open(
    "r",
    encoding="utf-8",
    newline="",
) as stream:
    for row in csv.DictReader(stream, delimiter="\t"):
        family = (row.get("family") or "").strip()
        source_path = (row.get("path") or "").strip()
        class_name = (row.get("class_name") or "").strip()

        is_equity = (
            "/equities/" in source_path
            or "Equity" in class_name
        )

        if family == "BR" and is_equity:
            count += 1

print(count)
PY_CHECK
)"

echo "false_br_equity_count=$FALSE_BR_EQUITY_COUNT"
[[ "$FALSE_BR_EQUITY_COUNT" -eq 0 ]]

awk -F '\t' '
    NR == 1 {
        next
    }

    $15 != "0" {
        print "ERROR=owner_prematurely_confirmed:" $5
        exit 1
    }

    $16 != "0" {
        print "ERROR=runtime_instrumentation_enabled:" $5
        exit 1
    }
' "$OUT/owner_candidates.tsv"

grep -q '^confirmed_owner_count=0$' "$LOG"
grep -q '^owner_assignment_performed=0$' "$LOG"
grep -q '^runtime_instrumentation=0$' "$LOG"

grep -q \
  '^VERDICT=STRATEGY_OWNER_INTENT_POINTS_V1_READY$' \
  "$LOG"

for marker in \
  "INSERT INTO" \
  "UPDATE " \
  "DELETE FROM" \
  "TRUNCATE " \
  "DROP TABLE" \
  "ALTER TABLE" \
  "systemctl restart" \
  "systemctl start" \
  "systemctl stop"
do
    count="$(
      {
        grep -F "$marker" \
          scripts/audit_strategy_owner_intent_points_v1.py \
          2>/dev/null || true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_action_marker=$marker count=$count"
    [[ "$count" -eq 0 ]]
done

STAGED_COUNT="$(
  git diff --cached --name-only |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "staged_count=$STAGED_COUNT"
[[ "$STAGED_COUNT" -eq 0 ]]

echo "confirmed_owner_count=0"
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
echo "VERDICT=TEST_STRATEGY_OWNER_INTENT_POINTS_V1_OK"
