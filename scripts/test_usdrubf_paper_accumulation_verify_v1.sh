#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== USDRUBF PAPER ACCUMULATION VERIFY V1 ==="
echo "mode=diagnostic"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo "STEP_1_SERVICE_ENV"
sudo systemctl show finam-paper-pipeline.service -p Environment --no-pager | tr ' ' '\n' | \
grep -E "ENABLE_USDRUBF_PAPER_ACCUMULATION_BYPASS_V1|EXECUTION_MODE|EXECUTION_ENABLED|REAL_TRADING_ENABLED" || true

echo "STEP_2_SERVICE_STATUS"
systemctl is-active finam-paper-pipeline.service

echo "STEP_3_RECENT_USDRUBF_LOGS"
journalctl -u finam-paper-pipeline.service --since "30 minutes ago" --no-pager | \
grep -E "USDRUBF_PAPER_ACCUMULATION_BYPASS|USDRUBF@RTSX|PIPE_SMART_ENTRY|PIPE_TREND_BLOCK|PIPE_TREND_ADVISORY_CONTINUE|PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2|PIPE_EDGE_GATE_STRICT_MODE|PIPE_RISK_OK|PaperExecution|FILL|TRADE" | tail -200 || true

echo "STEP_4_RECENT_USDRUBF_TRADES"
psql "$DATABASE_URL" -c "
select
    created_at,
    side,
    origin,
    strategy,
    timeframe,
    qty,
    price
from trades
where symbol='USDRUBF@RTSX'
  and created_at >= now() - interval '30 minutes'
order by created_at desc;
"

echo "STEP_5_LAST_USDRUBF_BARS"
psql "$DATABASE_URL" -c "
select
    symbol,
    timeframe,
    count(*) bars,
    max(ts) last_bar
from market_bars
where symbol='USDRUBF@RTSX'
group by 1,2
order by max(ts) desc;
"

echo "USDRUBF_PAPER_ACCUMULATION_VERIFY_V1_OK"
