#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST UNIVERSE MARKET DATA FRESHNESS AUDIT V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_market_data_freshness_audit_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_market_data_freshness_audit_v1.py
)"

echo "$OUTPUT"

grep -q \
  'mode=research_read_only' \
  <<< "$OUTPUT"

grep -q 'timeframe=M5' <<< "$OUTPUT"
grep -q 'top_n=15' <<< "$OUTPUT"

grep -q \
  'market_data_writes_allowed=0' \
  <<< "$OUTPUT"

grep -q \
  'systemd_changes_allowed=0' \
  <<< "$OUTPUT"

grep -q \
  'backfill_execution_allowed=0' \
  <<< "$OUTPUT"

grep -q 'TOP15_FRESHNESS_ROWS' \
  <<< "$OUTPUT"

grep -q 'FRESHNESS_ROW' \
  <<< "$OUTPUT"

grep -q 'SUMMARY_ROW' \
  <<< "$OUTPUT"

grep -q \
  'readiness_policy_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'market_data_writes_performed=0' \
  <<< "$OUTPUT"

grep -q \
  'backfill_executed=0' \
  <<< "$OUTPUT"

grep -q \
  'systemd_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'runtime_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'execution_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'orders_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'fills_changed=0' \
  <<< "$OUTPUT"

grep -q \
  'micro_live_allowed=0' \
  <<< "$OUTPUT"

grep -q \
'VERDICT=UNIVERSE_MARKET_DATA_FRESHNESS_AUDIT_V1_READY' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_MARKET_DATA_FRESHNESS_AUDIT_V1_OK"

echo
echo "=== STRICT INGESTION CONTRACT ==="

if grep -E \
'FRESHNESS_ROW .*job=.*gold-shadow-validation.*recovery_status=BACKFILL_READY' \
<<< "$OUTPUT"
then
    echo "ERROR=SHADOW_SERVICE_FALSE_BACKFILL_READY"
    exit 1
fi

if grep -E \
'FRESHNESS_ROW .*symbol=GLU6@RTSX .*recovery_status=BACKFILL_READY' \
<<< "$OUTPUT"
then
    echo "ERROR=DISPLAY_NAME_FALSE_BACKFILL_READY"
    exit 1
fi

if grep -E \
'FRESHNESS_ROW .*symbol=MXU6@RTSX .*job=finam-v5-bars-fast.service .*recovery_status=BACKFILL_READY' \
<<< "$OUTPUT"
then
    # Текущий ExecStart подтверждает MXU6=M1, а audit нужен M5.
    echo "ERROR=MXU6_M1_JOB_FALSE_M5_BACKFILL_READY"
    exit 1
fi

echo "VERDICT=STRICT_INGESTION_CONTRACT_OK"
