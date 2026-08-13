#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

PY="/opt/finam-core/venv/bin/python"
SCRIPT="src/scripts/run_targeted_entry_exit_oos_v1.py"
OUT="/tmp/targeted_entry_exit_oos_executor_v1.out"

echo "=== TEST TARGETED ENTRY EXIT OOS EXECUTOR V1 ==="

PYTHONPATH=src "$PY" -m py_compile "$SCRIPT"
git diff --check -- "$SCRIPT"

EDGE_SEARCH_TARGET_SYMBOL="BRQ6@RTSX" \
EDGE_SEARCH_TARGET_STRATEGY="BR_CONSERVATIVE_BREAKOUT" \
EDGE_SEARCH_TARGET_SIDE="LONG" \
PYTHONPATH=src "$PY" "$SCRIPT" \
  | tee "$OUT"

grep -q '^target_symbol=BRQ6@RTSX$' "$OUT"

grep -q \
'^target_strategy=BR_CONSERVATIVE_BREAKOUT$' \
"$OUT"

grep -q '^target_side=LONG$' "$OUT"
grep -q '^targeted_research_only_forced=1$' "$OUT"

grep -q \
'^VERDICT=ENTRY_EXIT_TARGETED_RESEARCH_ONLY_V1_READY$' \
"$OUT"

grep -q '^optimizer_returncode=0$' "$OUT"
grep -q '^targeted_optimizer_verdict_confirmed=1$' "$OUT"

grep -q '^execution_changed=0$' "$OUT"
grep -q '^orders_changed=0$' "$OUT"
grep -q '^fills_changed=0$' "$OUT"
grep -q '^micro_live_allowed=0$' "$OUT"

grep -q \
'^VERDICT=TARGETED_ENTRY_EXIT_OOS_EXECUTOR_V1_READY$' \
"$OUT"

echo \
"VERDICT=TEST_TARGETED_ENTRY_EXIT_OOS_EXECUTOR_V1_OK"
