#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_ROBUSTNESS_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
WITH base AS (
    SELECT
        s.side,
        s.horizon_bars,
        coalesce(o.block_reason,'UNKNOWN') AS block_reason,
        date_trunc('hour', s.entry_ts) AS hour_bucket,
        s.net_pnl
    FROM research.br_volatility_gate_shadow_simulation_v1 s
    JOIN research.br_volatility_gate_shadow_observation_v1 o
      ON o.observation_id=s.observation_id
    WHERE s.symbol='BRN6@RTSX'
      AND s.side='SELL'
      AND s.outcome <> 'NO_EXIT_BAR'
),
slice AS (
    SELECT
        side,
        horizon_bars,
        block_reason,
        count(*) AS trades,
        sum(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
        sum(CASE WHEN net_pnl < 0 THEN 1 ELSE 0 END) AS losses,
        coalesce(sum(net_pnl),0) AS net_pnl,
        avg(net_pnl) AS expectancy,
        coalesce(sum(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END),0) AS gross_profit,
        abs(coalesce(sum(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END),0)) AS gross_loss
    FROM base
    GROUP BY side,horizon_bars,block_reason
),
top_trade AS (
    SELECT
        side,
        horizon_bars,
        block_reason,
        max(net_pnl) AS max_win,
        min(net_pnl) AS max_loss
    FROM base
    GROUP BY side,horizon_bars,block_reason
),
by_hour AS (
    SELECT
        side,
        horizon_bars,
        block_reason,
        hour_bucket,
        count(*) AS trades,
        coalesce(sum(net_pnl),0) AS hour_net_pnl
    FROM base
    GROUP BY side,horizon_bars,block_reason,hour_bucket
),
hour_concentration AS (
    SELECT DISTINCT ON (side,horizon_bars,block_reason)
        side,
        horizon_bars,
        block_reason,
        hour_bucket,
        trades AS max_hour_trades,
        hour_net_pnl AS max_hour_net_pnl
    FROM by_hour
    ORDER BY side,horizon_bars,block_reason,abs(hour_net_pnl) DESC
),
robustness AS (
    SELECT
        s.side,
        s.horizon_bars,
        s.block_reason,
        s.trades,
        s.wins,
        s.losses,
        round((s.wins::numeric / nullif(s.trades,0)),6) AS winrate,
        round(s.net_pnl,6) AS net_pnl,
        round(s.expectancy,6) AS expectancy,
        CASE
            WHEN s.gross_loss = 0 AND s.gross_profit > 0 THEN NULL
            WHEN s.gross_loss = 0 THEN 0
            ELSE round(s.gross_profit / s.gross_loss,6)
        END AS profit_factor,
        round(t.max_win,6) AS max_win,
        round(t.max_loss,6) AS max_loss,
        round((s.net_pnl - t.max_win),6) AS net_without_max_win,
        h.hour_bucket,
        h.max_hour_trades,
        round(h.max_hour_net_pnl,6) AS max_hour_net_pnl,
        CASE
            WHEN s.trades < 50 THEN 'FAIL_SMALL_SAMPLE'
            WHEN s.net_pnl <= 0 THEN 'FAIL_NON_POSITIVE_NET'
            WHEN s.expectancy <= 0 THEN 'FAIL_NON_POSITIVE_EXPECTANCY'
            WHEN s.gross_loss > 0 AND (s.gross_profit / s.gross_loss) < 1.10 THEN 'FAIL_WEAK_PF'
            WHEN (s.net_pnl - t.max_win) <= 0 THEN 'FRAGILE_MAX_WIN_DEPENDENT'
            ELSE 'PASS'
        END AS robustness_status
    FROM slice s
    JOIN top_trade t
      ON t.side=s.side
     AND t.horizon_bars=s.horizon_bars
     AND t.block_reason=s.block_reason
    LEFT JOIN hour_concentration h
      ON h.side=s.side
     AND h.horizon_bars=s.horizon_bars
     AND h.block_reason=s.block_reason
)
SELECT
'robustness='||
side||'|h'||horizon_bars||'|'||block_reason||
'|trades='||trades||
'|net_pnl='||net_pnl||
'|pf='||coalesce(profit_factor::text,'NULL')||
'|expectancy='||expectancy||
'|net_without_max_win='||net_without_max_win||
'|max_hour='||coalesce(hour_bucket::text,'NULL')||
'|max_hour_net='||coalesce(max_hour_net_pnl::text,'NULL')||
'|status='||robustness_status
FROM robustness
ORDER BY
    CASE robustness_status WHEN 'PASS' THEN 0 ELSE 1 END,
    net_pnl DESC,
    profit_factor DESC NULLS LAST;

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=BR_VOLATILITY_GATE_SHADOW_ROBUSTNESS_V1_READY';
SQL

echo "TEST_BR_VOLATILITY_GATE_SHADOW_ROBUSTNESS_V1_OK"
