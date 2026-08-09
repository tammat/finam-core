#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo \
"=== TEST UNIVERSE TRADING CALENDAR FRESHNESS V1 ==="

python -m py_compile \
  src/scripts/research/build_universe_trading_calendar_freshness_v1.py

OUTPUT="$(
  PYTHONPATH=src \
  python \
    src/scripts/research/build_universe_trading_calendar_freshness_v1.py
)"

echo "$OUTPUT"

grep -q 'mode=research_read_only' <<< "$OUTPUT"
grep -q 'timeframe=M5' <<< "$OUTPUT"

grep -q \
  'global_universe_timestamp_used=0' \
  <<< "$OUTPUT"

grep -q \
  'calendar_inferred_from_history=1' \
  <<< "$OUTPUT"

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
  'BTCUSD' \
  'ETHUSD'
do
    grep -q \
      "CALENDAR_FRESHNESS_ROW symbol=${symbol}" \
      <<< "$OUTPUT"
done

# В воскресенье пятничные MOEX equities
# не должны считаться stale только из-за BTC 24x7.
for symbol in \
  'SBERP@MISX' \
  'VTBR@MISX' \
  'NVTK@MISX' \
  'T@MISX' \
  'SBER@MISX' \
  'LKOH@MISX' \
  'PLZL@MISX'
do
    grep -q \
      "CALENDAR_FRESHNESS_ROW symbol=${symbol} .*calendar_mode=SESSION .*missed_expected_sessions=0 .*status=FRESH" \
      <<< "$OUTPUT"
done

grep -q \
  'CALENDAR_FRESHNESS_ROW symbol=BTCUSD .*calendar_mode=CONTINUOUS_24X7 .*status=FRESH' \
  <<< "$OUTPUT"

grep -q \
  'CALENDAR_FRESHNESS_ROW symbol=ETHUSD .*calendar_mode=CONTINUOUS_24X7 .*status=STALE' \
  <<< "$OUTPUT"

grep -q 'SUMMARY_ROW' <<< "$OUTPUT"

grep -q 'readiness_policy_changed=0' <<< "$OUTPUT"
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

grep -q \
'VERDICT=UNIVERSE_TRADING_CALENDAR_FRESHNESS_V1_READY' \
<<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "=== WORKTREE ==="
git status --short

echo
echo \
"VERDICT=TEST_UNIVERSE_TRADING_CALENDAR_FRESHNESS_V1_OK"

echo
echo "=== MOEX WEEKEND CALENDAR GUARD ==="

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
      "CALENDAR_FRESHNESS_ROW symbol=${symbol} .*active_weekdays=.*5" \
      <<< "$OUTPUT"
    then
        echo \
        "ERROR=MOEX_EQUITY_SATURDAY_FALSE_ACTIVE symbol=${symbol}"
        exit 1
    fi

    if grep -q \
      "CALENDAR_FRESHNESS_ROW symbol=${symbol} .*active_weekdays=.*6" \
      <<< "$OUTPUT"
    then
        echo \
        "ERROR=MOEX_EQUITY_SUNDAY_FALSE_ACTIVE symbol=${symbol}"
        exit 1
    fi
done

echo "VERDICT=MOEX_WEEKEND_CALENDAR_GUARD_OK"
