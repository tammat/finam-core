#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_TRADE_PAIRING_V2_START"

python -m py_compile src/scripts/analytics/build_trade_pairing_v2.py

python src/scripts/analytics/build_trade_pairing_v2.py \
  --window-days 365 \
  --reset | tee /tmp/trade_pairing_v2.out

grep -q "TRADE_PAIRING_V2_LOADED" /tmp/trade_pairing_v2.out
grep -q "TRADE_PAIRING_V2_SUMMARY" /tmp/trade_pairing_v2.out
grep -q "TRADE_PAIRING_V2_OK" /tmp/trade_pairing_v2.out

psql "$DATABASE_URL" -c "
SELECT
    symbol,
    strategy,
    timeframe,
    origin,
    COUNT(*) AS rows,
    ROUND(SUM(net_pnl)::numeric, 6) AS net_pnl
FROM analytics_strategy_trades_v2
GROUP BY symbol, strategy, timeframe, origin
ORDER BY rows DESC;
"

echo "TEST_TRADE_PAIRING_V2_OK"
