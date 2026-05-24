#!/usr/bin/env bash
set -euo pipefail

grep -q "CREATE TABLE IF NOT EXISTS strategy_performance" scripts/migrate_strategy_performance_v1.sh
grep -q "UNIQUE(strategy, symbol, timeframe, regime, trade_source)" scripts/migrate_strategy_performance_v1.sh
grep -q "profit_factor" scripts/migrate_strategy_performance_v1.sh
grep -q "sharpe_like" scripts/migrate_strategy_performance_v1.sh
grep -q "max_drawdown" scripts/migrate_strategy_performance_v1.sh

echo "STRATEGY_PERFORMANCE_TABLE_TEST_OK"
