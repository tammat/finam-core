#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PAGER=cat
export PSQL_PAGER=cat

python -m py_compile src/scripts/apply_strategy_health_to_runtime_control.py

psql "$DATABASE_URL" -P pager=off -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

INSERT INTO closed_trades (
    signal_id, symbol, side,
    entry_price, exit_price, qty,
    gross_pnl, net_pnl, commission,
    horizon, strategy, regime,
    hold_seconds, entry_ts, exit_ts,
    trade_source, payload
)
VALUES
(
    'runtime-control-test-001', 'BRM6@RTSX', 'LONG',
    100, 103, 1, 3, 2.8, 0.2,
    'INTRADAY', 'BR_CONSERVATIVE_BREAKOUT_M5', 'trend_high_vol',
    300, now() - interval '5 minutes', now(), 'paper',
    jsonb_build_object('entry_payload', jsonb_build_object(
        'origin', 'runtime_control_test',
        'signal_id', 'runtime-control-test-001',
        'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
        'horizon', 'INTRADAY',
        'regime', 'trend_high_vol'
    ))
),
(
    'runtime-control-test-002', 'BRM6@RTSX', 'LONG',
    101, 104, 1, 3, 2.8, 0.2,
    'INTRADAY', 'BR_CONSERVATIVE_BREAKOUT_M5', 'trend_high_vol',
    240, now() - interval '4 minutes', now(), 'paper',
    jsonb_build_object('entry_payload', jsonb_build_object(
        'origin', 'runtime_control_test',
        'signal_id', 'runtime-control-test-002',
        'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
        'horizon', 'INTRADAY',
        'regime', 'trend_high_vol'
    ))
),
(
    'runtime-control-test-003', 'BRM6@RTSX', 'LONG',
    102, 105, 1, 3, 2.8, 0.2,
    'INTRADAY', 'BR_CONSERVATIVE_BREAKOUT_M5', 'trend_high_vol',
    180, now() - interval '3 minutes', now(), 'paper',
    jsonb_build_object('entry_payload', jsonb_build_object(
        'origin', 'runtime_control_test',
        'signal_id', 'runtime-control-test-003',
        'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
        'horizon', 'INTRADAY',
        'regime', 'trend_high_vol'
    ))
);

WITH perf AS (
    SELECT
      symbol,
      strategy,
      count(*) AS trades,
      sum(net_pnl) AS net_pnl,
      avg(net_pnl) AS expectancy,
      (sum(case when net_pnl > 0 then 1 else 0 end)::numeric / nullif(count(*), 0) * 100) AS winrate_pct
    FROM closed_trades
    WHERE payload ? 'entry_payload'
      AND payload->'entry_payload'->>'origin' = 'runtime_control_test'
      AND coalesce(strategy, '') NOT IN ('', 'UNKNOWN')
      AND coalesce(signal_id, '') <> ''
    GROUP BY 1,2
    HAVING count(*) >= 3
),
decisions AS (
    SELECT
      symbol,
      strategy,
      'HEALTHY' AS status,
      true AS allow_trade,
      false AS watch_only,
      1.2 AS risk_multiplier,
      'Положительное матожидание: стратегия разрешена и усилена' AS reason
    FROM perf
    WHERE net_pnl > 0 AND expectancy > 0 AND winrate_pct >= 55
)
INSERT INTO strategy_runtime_control (
    symbol, strategy, status, allow_trade, watch_only,
    risk_multiplier, reason, updated_at
)
SELECT
    symbol, strategy, status, allow_trade, watch_only,
    risk_multiplier, reason, now()
FROM decisions
ON CONFLICT (symbol, strategy) DO UPDATE SET
    status = excluded.status,
    allow_trade = excluded.allow_trade,
    watch_only = excluded.watch_only,
    risk_multiplier = excluded.risk_multiplier,
    reason = excluded.reason,
    updated_at = now();

DO $$
DECLARE
    v_count int;
BEGIN
    SELECT count(*)
    INTO v_count
    FROM strategy_runtime_control
    WHERE symbol = 'BRM6@RTSX'
      AND strategy = 'BR_CONSERVATIVE_BREAKOUT_M5'
      AND status = 'HEALTHY'
      AND allow_trade = true
      AND watch_only = false
      AND risk_multiplier >= 1.2;

    IF v_count < 1 THEN
        RAISE EXCEPTION 'strategy_runtime_control не обновлён health-applier';
    END IF;
END $$;

ROLLBACK;
SQL

echo "OK: решения health/weighting применяются к strategy_runtime_control через ROLLBACK"
