#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== NG RUNTIME SYMBOL ROUTING AUDIT V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo "STATIC_NG_M1_SYMBOLS"
grep -n "ng_m1_breakout_symbol\|bar.symbol != self.ng_m1_breakout_symbol\|NgConservativeBreakoutM1" \
  src/finam_core/pipelines/paper_pipeline.py

echo
echo "RUNTIME_ACTIVE_NG"
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    priority,
    is_enabled,
    source,
    updated_at
from runtime_active_universe
where symbol like 'NG%'
order by priority desc, symbol;
"

echo "NG_RUNTIME_SYMBOL_ROUTING_AUDIT_V1_OK"
