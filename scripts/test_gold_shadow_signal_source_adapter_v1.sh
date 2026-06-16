#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_gold_shadow_signal_source_adapter_v1.py

python3 src/scripts/runtime/build_gold_shadow_signal_source_adapter_v1.py \
  | tee /tmp/gold_shadow_signal_source_adapter_v1.log

grep -q "GOLD SHADOW SIGNAL SOURCE ADAPTER V1" /tmp/gold_shadow_signal_source_adapter_v1.log
grep -q "ADAPTER_ROW" /tmp/gold_shadow_signal_source_adapter_v1.log
grep -q "GDU6@RTSX" /tmp/gold_shadow_signal_source_adapter_v1.log
grep -q "runtime_allow=0" /tmp/gold_shadow_signal_source_adapter_v1.log
grep -q "execution_enabled=0" /tmp/gold_shadow_signal_source_adapter_v1.log
grep -q "GOLD_SHADOW_SIGNAL_SOURCE_ADAPTER_V1_OK" /tmp/gold_shadow_signal_source_adapter_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    strategy,
    COUNT(*) AS signals,
    MIN(signal_ts) AS first_ts,
    MAX(signal_ts) AS last_ts,
    bool_or(execution_enabled) AS any_execution_enabled
FROM gold_shadow_signals
WHERE symbol='GDU6@RTSX'
GROUP BY symbol, strategy;
"

echo TEST_GOLD_SHADOW_SIGNAL_SOURCE_ADAPTER_V1_OK
