#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_MARKET_BARS_V2 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_multi_asset_compression_follow_through_market_bars_v2.py

PYTHONPATH=src \
RUNTIME_ALLOW_TRADING=0 EXECUTION_ENABLED=0 REAL_TRADING_ENABLED=0 \
python3 src/scripts/research/build_multi_asset_compression_follow_through_market_bars_v2.py \
  --migrate --save | tee "$out"

grep -q "VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_MARKET_BARS_V2_READY" "$out"
grep -q "TEST_MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_MARKET_BARS_V2_OK" "$out"
grep -q "db_update=1" "$out"
grep -q "runtime_changed=0" "$out"
grep -q "execution_changed=0" "$out"
grep -q "telegram_send=0" "$out"

psql "$DATABASE_URL" -c "
select
  count(*) as rows,
  count(*) filter (where status='SUCCESS') as success,
  count(*) filter (where status='FAILURE') as failure,
  count(*) filter (where status='WAITING') as waiting,
  min(return_pct) as min_return_pct,
  max(return_pct) as max_return_pct
from analytics_multi_asset_compression_follow_through_market_bars_v2;
"

echo "VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_MARKET_BARS_V2_TEST_OK"
echo "TEST_MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_MARKET_BARS_V2_OK"
