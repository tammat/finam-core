#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST TREND PULLBACK RUNNER CONTRACT AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_trend_pullback_runner_contract_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_trend_pullback_runner_contract_audit_v1.py
)"

echo "$OUTPUT"

grep -q \
  'component=strategy_execution_runner' \
  <<< "$OUTPUT"

grep -q \
  'component=postgresql_edge_backtest_adapter' \
  <<< "$OUTPUT"

grep -q \
  'runner_support_confirmed=' \
  <<< "$OUTPUT"

grep -q \
  'canonical_adapter_confirmed=' \
  <<< "$OUTPUT"

grep -q 'backtest_performed=0' <<< "$OUTPUT"
grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=TREND_PULLBACK_(CANONICAL_ADAPTER_CONFIRMED_RUNNER_UNSUPPORTED|RUNNER_AND_ADAPTER_CONTRACT_CONFIRMED|CONTRACT_REVIEW_REQUIRED)' \
<<< "$OUTPUT"

echo
echo "=== PARAMETER SENSITIVITY SAFETY GUARD ==="

# Три различных TREND_PULLBACK variants не должны считаться
# валидными, если runner вообще не поддерживает этот strategy code.
if grep -q \
  'runner_support_confirmed=0' \
  <<< "$OUTPUT"
then
    echo \
    "VERDICT=TREND_PULLBACK_CURRENT_SCREEN_INVALID_BY_RUNNER_CONTRACT"
fi

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo \
"VERDICT=TEST_TREND_PULLBACK_RUNNER_CONTRACT_AUDIT_V1_OK"
