#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_BR_VOLATILITY_GATE_SHADOW_TEMPORAL_STABILITY_V1 ==="

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL'
WITH pass_slices AS (
    SELECT *
    FROM (
        VALUES
            ('SELL'::text, 15::int, 'br_volatility_too_low'::text),
            ('SELL'::text, 15::int, 'compression_watch_active'::text),
            ('SELL'::text, 3::int, 'compression_watch_active'::text)
    ) AS v(side, horizon_bars, block_reason)
),
base AS (
    SELECT
        s.side,
        s.horizon_bars,
        coalesce(o.block_reason,'UNKNOWN') AS block_reason,
        s.entry_ts::date AS trade_day,
        date_trunc('hour', s.entry_ts) AS hour_bucket,
        s.net_pnl
    FROM research.br_volatility_gate_shadow_simulation_v1 s
    JOIN research.br_volatility_gate_shadow_observation_v1 o
      ON o.observation_id=s.observation_id
    JOIN pass_slices p
      ON p.side=s.side
     AND p.horizon_bars=s.horizon_bars
     AND p.block_reason=coalesce(o.block_reason,'UNKNOWN')
    WHERE s.symbol='BRN6@RTSX'
      AND s.outcome <> 'NO_EXIT_BAR'
),
slice_total AS (
    SELECT
        side,
        horizon_bars,
        block_reason,
        count(*) AS trades,
        coalesce(sum(net_pnl),0) AS net_pnl,
        avg(net_pnl) AS expectancy,
        coalesce(sum(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END),0) AS gross_profit,
        abs(coalesce(sum(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END),0)) AS gross_loss
    FROM base
    GROUP BY side,horizon_bars,block_reason
),
by_day AS (
    SELECT
        side,
        horizon_bars,
        block_reason,
        trade_day,
        count(*) AS trades,
        coalesce(sum(net_pnl),0) AS day_net_pnl
    FROM base
    GROUP BY side,horizon_bars,block_reason,trade_day
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
max_day AS (
    SELECT DISTINCT ON (side,horizon_bars,block_reason)
        side,horizon_bars,block_reason,trade_day,trades,day_net_pnl
    FROM by_day
    ORDER BY side,horizon_bars,block_reason,abs(day_net_pnl) DESC
),
max_hour AS (
    SELECT DISTINCT ON (side,horizon_bars,block_reason)
        side,horizon_bars,block_reason,hour_bucket,trades,hour_net_pnl
    FROM by_hour
    ORDER BY side,horizon_bars,block_reason,abs(hour_net_pnl) DESC
),
loo_day AS (
    SELECT
        t.side,
        t.horizon_bars,
        t.block_reason,
        d.trade_day AS removed_day,
        count(b.*) FILTER (WHERE b.trade_day <> d.trade_day) AS trades_after_remove,
        coalesce(sum(b.net_pnl) FILTER (WHERE b.trade_day <> d.trade_day),0) AS net_after_remove
    FROM slice_total t
    JOIN by_day d
      ON d.side=t.side
     AND d.horizon_bars=t.horizon_bars
     AND d.block_reason=t.block_reason
    JOIN base b
      ON b.side=t.side
     AND b.horizon_bars=t.horizon_bars
     AND b.block_reason=t.block_reason
    GROUP BY t.side,t.horizon_bars,t.block_reason,d.trade_day
),
loo_hour AS (
    SELECT
        t.side,
        t.horizon_bars,
        t.block_reason,
        h.hour_bucket AS removed_hour,
        count(b.*) FILTER (WHERE b.hour_bucket <> h.hour_bucket) AS trades_after_remove,
        coalesce(sum(b.net_pnl) FILTER (WHERE b.hour_bucket <> h.hour_bucket),0) AS net_after_remove
    FROM slice_total t
    JOIN by_hour h
      ON h.side=t.side
     AND h.horizon_bars=t.horizon_bars
     AND h.block_reason=t.block_reason
    JOIN base b
      ON b.side=t.side
     AND b.horizon_bars=t.horizon_bars
     AND b.block_reason=t.block_reason
    GROUP BY t.side,t.horizon_bars,t.block_reason,h.hour_bucket
),
worst_loo_day AS (
    SELECT DISTINCT ON (side,horizon_bars,block_reason)
        side,horizon_bars,block_reason,removed_day,trades_after_remove,net_after_remove
    FROM loo_day
    ORDER BY side,horizon_bars,block_reason,net_after_remove ASC
),
worst_loo_hour AS (
    SELECT DISTINCT ON (side,horizon_bars,block_reason)
        side,horizon_bars,block_reason,removed_hour,trades_after_remove,net_after_remove
    FROM loo_hour
    ORDER BY side,horizon_bars,block_reason,net_after_remove ASC
),
final AS (
    SELECT
        t.side,
        t.horizon_bars,
        t.block_reason,
        t.trades,
        round(t.net_pnl,6) AS net_pnl,
        round(t.expectancy,6) AS expectancy,
        CASE
            WHEN t.gross_loss = 0 AND t.gross_profit > 0 THEN NULL
            WHEN t.gross_loss = 0 THEN 0
            ELSE round(t.gross_profit / t.gross_loss,6)
        END AS profit_factor,
        md.trade_day AS max_day,
        round(md.day_net_pnl,6) AS max_day_net,
        mh.hour_bucket AS max_hour,
        round(mh.hour_net_pnl,6) AS max_hour_net,
        wd.removed_day AS worst_removed_day,
        round(wd.net_after_remove,6) AS worst_day_removed_net,
        wh.removed_hour AS worst_removed_hour,
        round(wh.net_after_remove,6) AS worst_hour_removed_net,
        CASE
            WHEN wd.net_after_remove <= 0 THEN 'FAIL_DAY_CONCENTRATION'
            WHEN wh.net_after_remove <= 0 THEN 'FAIL_HOUR_CONCENTRATION'
            ELSE 'PASS_TEMPORAL_STABILITY'
        END AS temporal_status
    FROM slice_total t
    JOIN max_day md
      ON md.side=t.side AND md.horizon_bars=t.horizon_bars AND md.block_reason=t.block_reason
    JOIN max_hour mh
      ON mh.side=t.side AND mh.horizon_bars=t.horizon_bars AND mh.block_reason=t.block_reason
    JOIN worst_loo_day wd
      ON wd.side=t.side AND wd.horizon_bars=t.horizon_bars AND wd.block_reason=t.block_reason
    JOIN worst_loo_hour wh
      ON wh.side=t.side AND wh.horizon_bars=t.horizon_bars AND wh.block_reason=t.block_reason
)
SELECT
'temporal='||
side||'|h'||horizon_bars||'|'||block_reason||
'|trades='||trades||
'|net_pnl='||net_pnl||
'|pf='||coalesce(profit_factor::text,'NULL')||
'|max_day='||max_day||
'|max_day_net='||max_day_net||
'|max_hour='||max_hour||
'|max_hour_net='||max_hour_net||
'|worst_day_removed_net='||worst_day_removed_net||
'|worst_hour_removed_net='||worst_hour_removed_net||
'|status='||temporal_status
FROM final
ORDER BY
    CASE temporal_status WHEN 'PASS_TEMPORAL_STABILITY' THEN 0 ELSE 1 END,
    net_pnl DESC;

SELECT 'runtime_changed=0';
SELECT 'execution_changed=0';
SELECT 'orders_changed=0';
SELECT 'fills_changed=0';
SELECT 'micro_live_allowed=0';
SELECT 'VERDICT=BR_VOLATILITY_GATE_SHADOW_TEMPORAL_STABILITY_V1_READY';
SQL

echo "TEST_BR_VOLATILITY_GATE_SHADOW_TEMPORAL_STABILITY_V1_OK"
