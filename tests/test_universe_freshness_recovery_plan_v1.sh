#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST UNIVERSE FRESHNESS RECOVERY PLAN V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_freshness_recovery_plan_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_freshness_recovery_plan_v1.py
)"

echo "$OUTPUT"

grep -q 'mode=read_only_plan' <<< "$OUTPUT"
grep -q 'timeframe=M5' <<< "$OUTPUT"
grep -q 'targets=10' <<< "$OUTPUT"

for symbol in \
  'SBERP@MISX' \
  'VTBR@MISX' \
  'NVTK@MISX' \
  'T@MISX' \
  'SBER@MISX' \
  'LKOH@MISX' \
  'PLZL@MISX' \
  'IMOEX' \
  'RTSI' \
  'ETHUSD'
do
    grep -q \
      "RECOVERY_PLAN_ROW symbol=${symbol}" \
      <<< "$OUTPUT"
done

grep -q 'RECOVERY_EXEC_ROW' <<< "$OUTPUT"
grep -q 'RECOVERY_JOURNAL_ROW' <<< "$OUTPUT"
grep -q 'SUMMARY_ROW' <<< "$OUTPUT"

grep -q 'recovery_commands_executed=0' <<< "$OUTPUT"
grep -q 'backfill_executed=0' <<< "$OUTPUT"
grep -q 'market_data_writes_performed=0' <<< "$OUTPUT"
grep -q 'systemd_changed=0' <<< "$OUTPUT"
grep -q 'runtime_changed=0' <<< "$OUTPUT"
grep -q 'execution_changed=0' <<< "$OUTPUT"
grep -q 'orders_changed=0' <<< "$OUTPUT"
grep -q 'fills_changed=0' <<< "$OUTPUT"
grep -q 'micro_live_allowed=0' <<< "$OUTPUT"

grep -q \
'VERDICT=UNIVERSE_FRESHNESS_RECOVERY_PLAN_V1_READY' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_FRESHNESS_RECOVERY_PLAN_V1_OK"

echo
echo "=== SEMANTIC RECOVERY CONTRACT ==="

# ETHUSD точно не может быть PLAN_READY:
# target настроен, job успешен, но M5 остаётся stale.
if grep -q \
  'RECOVERY_PLAN_ROW symbol=ETHUSD .*status=PLAN_READY' \
  <<< "$OUTPUT"
then
    echo "ERROR=ETHUSD_FALSE_PLAN_READY"
    exit 1
fi

grep -q \
  'RECOVERY_PLAN_ROW symbol=ETHUSD .*status=REVIEW_REQUIRED .*reason=ETHUSD_TARGET_CONFIGURED_BUT_STALE' \
  <<< "$OUTPUT"

# IMOEX/RTSI имеют работающий online ingestion.
# В воскресенье им не нужен blind backfill.
for symbol in IMOEX RTSI
do
    if grep -q \
      "RECOVERY_PLAN_ROW symbol=${symbol} .*status=PLAN_READY" \
      <<< "$OUTPUT"
    then
        echo "ERROR=${symbol}_FALSE_PLAN_READY"
        exit 1
    fi

    grep -q \
      "RECOVERY_PLAN_ROW symbol=${symbol} .*status=NO_RECOVERY_REQUIRED" \
      <<< "$OUTPUT"
done

# MOEX equities нельзя объявлять recovery-ready,
# пока нет calendar-aware freshness contract.
for symbol in \
  'SBERP@MISX' \
  'VTBR@MISX' \
  'NVTK@MISX' \
  'T@MISX' \
  'SBER@MISX' \
  'LKOH@MISX' \
  'PLZL@MISX'
do
    if grep -q \
      "RECOVERY_PLAN_ROW symbol=${symbol} .*status=PLAN_READY" \
      <<< "$OUTPUT"
    then
        echo "ERROR=${symbol}_FALSE_PLAN_READY"
        exit 1
    fi
done

echo "VERDICT=UNIVERSE_FRESHNESS_RECOVERY_SEMANTIC_CONTRACT_OK"

echo
