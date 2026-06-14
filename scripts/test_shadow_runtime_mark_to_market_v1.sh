#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

export PYTHONPATH=src

python3 -m py_compile src/scripts/runtime/build_shadow_runtime_mark_to_market_v1.py

python3 src/scripts/runtime/build_shadow_runtime_mark_to_market_v1.py \
  | tee /tmp/shadow_runtime_mark_to_market_v1.log

grep -q "SHADOW RUNTIME MARK TO MARKET V1" /tmp/shadow_runtime_mark_to_market_v1.log
grep -q "MTM_ROW" /tmp/shadow_runtime_mark_to_market_v1.log
grep -q "LKOH@MISX" /tmp/shadow_runtime_mark_to_market_v1.log
grep -q "market_price_source=market_ticks" /tmp/shadow_runtime_mark_to_market_v1.log
grep -q "price_scale_status=" /tmp/shadow_runtime_mark_to_market_v1.log
grep -q "runtime_allow=0" /tmp/shadow_runtime_mark_to_market_v1.log
grep -q "execution_enabled=0" /tmp/shadow_runtime_mark_to_market_v1.log
grep -q "SHADOW_RUNTIME_MARK_TO_MARKET_V1_OK" /tmp/shadow_runtime_mark_to_market_v1.log

psql "$DATABASE_URL" -P pager=off -c "
SELECT
    symbol,
    qty,
    avg_price,
    market_price,
    market_price_source,
    unrealized_pnl,
    total_pnl,
    price_scale_status,
    runtime_allowed,
    execution_enabled
FROM shadow_runtime_mark_to_market
ORDER BY id DESC
LIMIT 5;
"

echo TEST_SHADOW_RUNTIME_MARK_TO_MARKET_V1_OK
