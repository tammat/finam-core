#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST ETHUSD BACKFILL PATH AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_ethusd_backfill_path_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_ethusd_backfill_path_audit_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=research_read_only' \
  <<< "$OUTPUT"

grep -q \
  'unit=finam-crypto-backfill.service' \
  <<< "$OUTPUT"

grep -q 'SERVICE_ROW' <<< "$OUTPUT"
grep -q 'SERVICE_EXEC_ROW' <<< "$OUTPUT"
grep -q 'EXECUTION_CHAIN_ROWS' <<< "$OUTPUT"

grep -q \
  'MARKET_DATA_ROW symbol=BTCUSD' \
  <<< "$OUTPUT"

grep -q \
  'MARKET_DATA_ROW symbol=ETHUSD' \
  <<< "$OUTPUT"

grep -q 'JOURNAL_SUMMARY' <<< "$OUTPUT"

grep -q 'btc_target_confirmed=' <<< "$OUTPUT"
grep -q 'eth_target_confirmed=' <<< "$OUTPUT"
grep -q 'btc_fresh=' <<< "$OUTPUT"
grep -q 'eth_fresh=' <<< "$OUTPUT"

grep -q 'backfill_executed=0' <<< "$OUTPUT"
grep -q \
  'market_data_writes_performed=0' \
  <<< "$OUTPUT"

grep -q 'systemd_changed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=ETHUSD_BACKFILL_PATH_(TARGET_NOT_CONFIGURED|TARGET_CONFIGURED_BUT_STALE|FRESH|REVIEW_REQUIRED)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_ETHUSD_BACKFILL_PATH_AUDIT_V1_OK"

echo
echo "=== EXECUTION CHAIN CONTRACT ==="

grep -q \
  'EXECUTION_CHAIN_ROW path=/opt/finam-core/scripts/ops/crypto_daily_backfill_job_v1.sh' \
  <<< "$OUTPUT"

if grep -q \
  'VERDICT=ETHUSD_BACKFILL_PATH_TARGET_NOT_CONFIGURED' \
  <<< "$OUTPUT"
then
    if grep -q \
      'ETH_JOURNAL_ROW .*symbol=ETHUSD' \
      <<< "$OUTPUT"
    then
        echo \
        "ERROR=ETH_TARGET_FALSE_NEGATIVE_WITH_JOURNAL_EVIDENCE"
        exit 1
    fi
fi

echo "VERDICT=ETHUSD_EXECUTION_CHAIN_CONTRACT_OK"
