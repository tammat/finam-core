#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST IMOEX2 MXU6 SIGNAL REPLAY CONTRACT V1 ==="

python -m py_compile \
  src/scripts/research/build_imoex2_mxu6_signal_replay_contract_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python src/scripts/research/build_imoex2_mxu6_signal_replay_contract_v1.py
)"

echo "$OUTPUT"

grep -q 'signal_symbol=IMOEX2' <<< "$OUTPUT"
grep -q 'execution_symbol=MXU6@RTSX' <<< "$OUTPUT"

grep -q 'BAR_ROW' <<< "$OUTPUT"
grep -q 'TRADE_ROW' <<< "$OUTPUT"

grep -q 'economic_verdict_allowed=0' <<< "$OUTPUT"
grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=IMOEX2_MXU6_SIGNAL_REPLAY_(CONTRACT_READY|ALIGNMENT_INSUFFICIENT|TRADE_CONTRACT_REVIEW|NO_SAMPLE_TRADES)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_IMOEX2_MXU6_SIGNAL_REPLAY_CONTRACT_V1_OK"
