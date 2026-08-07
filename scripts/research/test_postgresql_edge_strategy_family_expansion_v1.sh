#!/usr/bin/env bash
set -euo pipefail

ROOT="/opt/finam-core"
PYTHON="$ROOT/venv/bin/python"
ADAPTER="src/finam_core/research/postgresql_edge_backtest_adapter_v1.py"
BUILDER="scripts/research/build_postgresql_edge_strategy_family_expansion_v1.py"

BATCH_ID="TEST_PG_EDGE_FAMILY_EXPANSION_V1"
OUT="/tmp/postgresql_edge_strategy_family_expansion_v1/$BATCH_ID"
LOG="/tmp/test_postgresql_edge_strategy_family_expansion_v1.log"

cd "$ROOT"

rm -rf "$OUT"
rm -f "$LOG"

PYTHONPATH=src \
"$PYTHON" -m py_compile \
  "$ADAPTER" \
  "$BUILDER"

PYTHONPATH=src \
"$PYTHON" "$ADAPTER" --self-test |
tee "$LOG"

PYTHONPATH=src \
"$PYTHON" "$BUILDER" \
  --symbols "LKOH@MISX" \
  --timeframes "M5" \
  --commission-per-side "1.5" \
  --slippage-bps "2.0" \
  --bar-limit 20000 \
  --batch-id "$BATCH_ID" \
  --max-tasks 48 \
  --plan-only |
tee -a "$LOG"

for file in \
  "$OUT/search_plan.tsv" \
  "$OUT/contract.txt" \
  "$OUT/unresolved.tsv"
do
    [[ -f "$file" ]]
done

TASK_COUNT="$(
  tail -n +2 "$OUT/search_plan.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

MEAN_REVERSION_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $3 == "MEAN_REVERSION_ZSCORE_V1" {
          count++
      }
      END { print count + 0 }
  ' "$OUT/search_plan.tsv"
)"

TREND_PULLBACK_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $3 == "TREND_PULLBACK_V1" {
          count++
      }
      END { print count + 0 }
  ' "$OUT/search_plan.tsv"
)"

VOLATILITY_BREAKOUT_COUNT="$(
  awk -F '\t' '
      NR > 1 &&
      $3 == "VOLATILITY_BREAKOUT_FILTERED_V1" {
          count++
      }
      END { print count + 0 }
  ' "$OUT/search_plan.tsv"
)"

UNIQUE_HASH_COUNT="$(
  awk -F '\t' '
      NR > 1 { seen[$6] = 1 }
      END {
          for (key in seen) count++
          print count + 0
      }
  ' "$OUT/search_plan.tsv"
)"

UNRESOLVED_COUNT="$(
  tail -n +2 "$OUT/unresolved.tsv" |
  sed '/^$/d' |
  wc -l |
  tr -d ' '
)"

echo "task_count=$TASK_COUNT"
echo "mean_reversion_count=$MEAN_REVERSION_COUNT"
echo "trend_pullback_count=$TREND_PULLBACK_COUNT"
echo "volatility_breakout_count=$VOLATILITY_BREAKOUT_COUNT"
echo "unique_parameter_hash_count=$UNIQUE_HASH_COUNT"
echo "unresolved_count=$UNRESOLVED_COUNT"

[[ "$TASK_COUNT" -eq 48 ]]
[[ "$MEAN_REVERSION_COUNT" -eq 16 ]]
[[ "$TREND_PULLBACK_COUNT" -eq 16 ]]
[[ "$VOLATILITY_BREAKOUT_COUNT" -eq 16 ]]
[[ "$UNIQUE_HASH_COUNT" -eq 48 ]]
[[ "$UNRESOLVED_COUNT" -eq 0 ]]

for strategy in \
  "MEAN_REVERSION_ZSCORE_V1" \
  "TREND_PULLBACK_V1" \
  "VOLATILITY_BREAKOUT_FILTERED_V1"
do
    grep -Fq "$strategy" "$ADAPTER"
    grep -Fq "$strategy" "$OUT/search_plan.tsv"
done

grep -Fqx "TASK_COUNT=48" "$OUT/contract.txt"
grep -Fqx "MEAN_REVERSION_TASK_COUNT=16" "$OUT/contract.txt"
grep -Fqx "TREND_PULLBACK_TASK_COUNT=16" "$OUT/contract.txt"
grep -Fqx "VOLATILITY_BREAKOUT_TASK_COUNT=16" "$OUT/contract.txt"
grep -Fqx "PLAN_ONLY=1" "$OUT/contract.txt"
grep -Fqx "DATABASE=POSTGRESQL_ONLY" "$OUT/contract.txt"
grep -Fqx "OOS_ALLOWED=0" "$OUT/contract.txt"
grep -Fqx "SHADOW_ALLOWED=0" "$OUT/contract.txt"
grep -Fqx "PAPER_ALLOWED=0" "$OUT/contract.txt"

for marker in \
  "sqlite3" \
  "bars.sqlite" \
  "send_order(" \
  "place_order(" \
  "submit_order(" \
  "execution_enabled = true" \
  "micro_live_allowed = true"
do
    COUNT="$(
      {
        grep -F "$marker" "$ADAPTER" "$BUILDER" ||
        true
      } |
      wc -l |
      tr -d ' '
    )"

    echo "forbidden_marker=$marker count=$COUNT"
    [[ "$COUNT" -eq 0 ]]
done

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_SELF_TEST_OK" \
  "$LOG"

grep -Fq \
  "VERDICT=POSTGRESQL_EDGE_STRATEGY_FAMILY_EXPANSION_V1_READY" \
  "$LOG"

echo "db_writes_performed=0"
echo "strategy_changed=1"
echo "risk_engine_changed=0"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_POSTGRESQL_EDGE_STRATEGY_FAMILY_EXPANSION_V1_OK"
