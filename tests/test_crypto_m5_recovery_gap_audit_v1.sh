#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST CRYPTO M5 RECOVERY GAP AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_crypto_m5_recovery_gap_audit_v1.py

OUTPUT="$(
    PYTHONPATH=src \
    python \
      src/scripts/research/build_crypto_m5_recovery_gap_audit_v1.py
)"

echo "$OUTPUT"

grep -q 'CRYPTO_ROW symbol=BTCUSD' <<< "$OUTPUT"
grep -q 'CRYPTO_ROW symbol=ETHUSD' <<< "$OUTPUT"
grep -q 'SERVICE_ROW' <<< "$OUTPUT"
grep -q 'JOURNAL_SUMMARY' <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'backfill_executed=0' <<< "$OUTPUT"
grep -q 'systemd_changed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -Eq \
'VERDICT=CRYPTO_M5_RECOVERY_(COMPLETE|PARTIAL_ETH_STALE|NOT_READY)' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo \
"VERDICT=TEST_CRYPTO_M5_RECOVERY_GAP_AUDIT_V1_OK"
