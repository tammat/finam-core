#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

WINDOW="${1:-60 minutes}"
JOURNAL_SINCE="${2:-60 minutes ago}"
LOG_FILE="/tmp/ngq6_forward_accumulation_verify_v2.log"

echo "=== NGQ6 FORWARD ACCUMULATION VERIFY V2 ==="
echo "mode=diagnostic"
echo "window=${WINDOW}"
echo "journal_since=${JOURNAL_SINCE}"
echo "runtime_allow=0"
echo "execution_enabled=0"

echo
echo "=== 1. RUNTIME ACTIVE UNIVERSE ==="
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
where symbol='NGQ6@RTSX'
order by updated_at desc;
"

echo
echo "=== 2. RECENT NGQ6 BARS ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    timeframe,
    count(*) bars,
    max(ts) last_bar
from market_bars
where symbol='NGQ6@RTSX'
  and timeframe in ('M1','M5','H1')
group by 1,2
order by timeframe;
"

echo
echo "=== 3. COLLECT PIPELINE LOGS ==="
journalctl -u finam-paper-pipeline.service --since "${JOURNAL_SINCE}" --no-pager | \
grep -E "NGQ6@RTSX|PIPE_NGQ6_M1_BAR_HANDLER_TRACE_V1|PIPE_NG_M1_STRATEGY_INIT|PIPE_SMART_ENTRY|PIPE_BREAKOUT_DETECTED|PIPE_NG_SMART_ENTRY_QUALITY|NG_PAPER_ACCUMULATION_BYPASS|PIPE_RISK_CTX|PIPE_NG_EXEC_TRACE_AFTER_RISK_OK|PIPE_NG_EXEC_TRACE_BEFORE_PORTFOLIO_GATE|PIPE_TRADE_EXEC|PIPE_FILLED paper|PIPE_RISK_REJECT|PIPE_TRADE_LIMIT_BLOCK|PIPE_POSITION_BLOCK|PIPE_PORTFOLIO|PIPE_CLUSTER|PIPE_COOLDOWN_BLOCK" \
> "${LOG_FILE}" || true

tail -180 "${LOG_FILE}" || true

handler_allowed=$(grep -c "PIPE_NGQ6_M1_BAR_HANDLER_TRACE_V1 symbol=NGQ6@RTSX allowed=True" "${LOG_FILE}" || true)
handler_blocked=$(grep -c "PIPE_NGQ6_M1_BAR_HANDLER_TRACE_V1 symbol=NGQ6@RTSX allowed=False" "${LOG_FILE}" || true)
strategy_init=$(grep -c "PIPE_NG_M1_STRATEGY_INIT symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
breakouts=$(grep -c "PIPE_BREAKOUT_DETECTED .*symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
smart_entries=$(grep -c "PIPE_SMART_ENTRY .*symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
quality_allow=$(grep -c "PIPE_NG_SMART_ENTRY_QUALITY_GATE_V1 symbol=NGQ6@RTSX .*allowed=1" "${LOG_FILE}" || true)
quality_block=$(grep -c "PIPE_NG_SMART_ENTRY_QUALITY_BLOCK_V1 symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
paper_bypass=$(grep -c "NG_PAPER_ACCUMULATION_BYPASS symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
risk_ctx=$(grep -c "PIPE_RISK_CTX symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
risk_after=$(grep -c "PIPE_NG_EXEC_TRACE_AFTER_RISK_OK symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
portfolio_before=$(grep -c "PIPE_NG_EXEC_TRACE_BEFORE_PORTFOLIO_GATE symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
trade_exec=$(grep -c "PIPE_TRADE_EXEC symbol=NGQ6@RTSX" "${LOG_FILE}" || true)
fills=$(grep -c "PIPE_FILLED paper NGQ6@RTSX" "${LOG_FILE}" || true)
risk_reject=$(grep -c "PIPE_RISK_REJECT" "${LOG_FILE}" || true)
trade_limit_symbol=$(grep -c "PIPE_TRADE_LIMIT_BLOCK_SYMBOL NGQ6@RTSX" "${LOG_FILE}" || true)
trade_limit_global=$(grep -c "PIPE_TRADE_LIMIT_BLOCK_GLOBAL" "${LOG_FILE}" || true)
position_block=$(grep -c "PIPE_POSITION_BLOCK" "${LOG_FILE}" || true)
portfolio_block=$(grep -c "PIPE_PORTFOLIO" "${LOG_FILE}" || true)
cluster_block=$(grep -c "PIPE_CLUSTER" "${LOG_FILE}" || true)
cooldown_block=$(grep -c "PIPE_COOLDOWN_BLOCK" "${LOG_FILE}" || true)

db_trades=$(psql "$DATABASE_URL" -At -c "
select count(*)
from trades
where symbol='NGQ6@RTSX'
  and created_at >= now() - interval '${WINDOW}';
")

echo
echo "=== 4. STAGE COUNTS ==="
echo "handler_allowed=${handler_allowed}"
echo "handler_blocked=${handler_blocked}"
echo "strategy_init=${strategy_init}"
echo "breakouts=${breakouts}"
echo "smart_entries=${smart_entries}"
echo "quality_allow=${quality_allow}"
echo "quality_block=${quality_block}"
echo "paper_bypass=${paper_bypass}"
echo "risk_ctx=${risk_ctx}"
echo "risk_after=${risk_after}"
echo "portfolio_before=${portfolio_before}"
echo "trade_exec=${trade_exec}"
echo "fills=${fills}"
echo "db_trades=${db_trades}"
echo "risk_reject=${risk_reject}"
echo "trade_limit_symbol=${trade_limit_symbol}"
echo "trade_limit_global=${trade_limit_global}"
echo "position_block=${position_block}"
echo "portfolio_block=${portfolio_block}"
echo "cluster_block=${cluster_block}"
echo "cooldown_block=${cooldown_block}"

echo
echo "=== 5. RECENT NGQ6 TRADES ==="
psql "$DATABASE_URL" -c "
select
    created_at,
    symbol,
    strategy,
    timeframe,
    side,
    origin,
    trade_source,
    qty,
    price
from trades
where symbol='NGQ6@RTSX'
  and created_at >= now() - interval '${WINDOW}'
order by created_at desc
limit 50;
"

echo
echo "=== 6. CURRENT CLEAN V3 NGQ6 ==="
psql "$DATABASE_URL" -c "
select
    symbol,
    strategy,
    timeframe,
    clean_trades,
    trade_days,
    v3_full_chains,
    round(v3_net_pnl,6) as pnl,
    round(v3_net_pnl / nullif(v3_full_chains,0),6) as expectancy,
    accumulation_status
from clean_paper_accumulation_tracker_v1
where symbol='NGQ6@RTSX'
order by strategy,timeframe;
"

echo
echo "=== 7. VERDICT ==="

if [ "${handler_allowed}" = "0" ]; then
    echo "VERDICT=NO_NGQ6_HANDLER_ROUTE"
elif [ "${smart_entries}" = "0" ]; then
    echo "VERDICT=HANDLER_OK_NO_SMART_ENTRY"
elif [ "${quality_allow}" = "0" ] && [ "${quality_block}" != "0" ]; then
    echo "VERDICT=QUALITY_GATE_BLOCKING_NGQ6"
elif [ "${risk_after}" != "0" ] && [ "${trade_exec}" = "0" ]; then
    echo "VERDICT=AFTER_RISK_BEFORE_EXEC_BLOCK"
elif [ "${trade_exec}" != "0" ] && [ "${fills}" = "0" ]; then
    echo "VERDICT=TRADE_EXEC_WITHOUT_FILL"
elif [ "${fills}" != "0" ] && [ "${db_trades}" = "0" ]; then
    echo "VERDICT=FILL_NOT_PERSISTED_TO_TRADES"
elif [ "${db_trades}" != "0" ]; then
    echo "VERDICT=NGQ6_FORWARD_TRADES_OK"
else
    echo "VERDICT=UNKNOWN_NGQ6_FLOW_STATE"
fi

echo "NGQ6_FORWARD_ACCUMULATION_VERIFY_V2_OK"
