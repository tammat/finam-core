#!/usr/bin/env bash
set -euo pipefail

export PAGER=cat
export PSQL_PAGER=cat

psql "$DATABASE_URL" -P pager=off -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

INSERT INTO closed_trades (
    signal_id,
    symbol,
    side,
    entry_price,
    exit_price,
    qty,
    gross_pnl,
    net_pnl,
    commission,
    horizon,
    strategy,
    regime,
    hold_seconds,
    entry_ts,
    exit_ts,
    trade_source,
    payload
)
VALUES (
    'clean-sql-test-signal-001',
    'BRM6@RTSX',
    'LONG',
    100.0,
    102.0,
    1.0,
    2.0,
    1.8,
    0.2,
    'INTRADAY',
    'BR_CONSERVATIVE_BREAKOUT_M5',
    'trend_high_vol',
    300,
    now() - interval '5 minutes',
    now(),
    'paper',
    jsonb_build_object(
        'entry_payload', jsonb_build_object(
            'origin', 'synthetic_clean_sql_test',
            'signal_id', 'clean-sql-test-signal-001',
            'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
            'horizon', 'INTRADAY',
            'regime', 'trend_high_vol',
            'timeframe', 'M5'
        ),
        'exit_payload', jsonb_build_object(
            'origin', 'synthetic_clean_sql_test'
        )
    )
);

WITH clean AS (
    SELECT
      coalesce(payload->'entry_payload'->>'origin',
               payload->'entry_payload'->>'trade_source',
               payload->'entry_payload'->>'execution_type',
               trade_source,
               'unknown') as source,
      symbol,
      strategy,
      horizon,
      regime,
      count(*) as closed_trades,
      round(sum(net_pnl)::numeric, 4) as net_pnl
    FROM closed_trades
    WHERE signal_id = 'clean-sql-test-signal-001'
      AND payload ? 'entry_payload'
      AND coalesce(payload->'entry_payload'->>'origin', '') <> 'backfill_from_fills'
      AND coalesce(strategy, payload->'entry_payload'->>'strategy', '') not in ('', 'UNKNOWN')
      AND coalesce(signal_id, payload->'entry_payload'->>'signal_id', '') <> ''
    GROUP BY 1,2,3,4,5
)
SELECT * FROM clean;

DO $$
DECLARE
    v_count int;
    v_pnl numeric;
BEGIN
    SELECT count(*), coalesce(sum(net_pnl), 0)
    INTO v_count, v_pnl
    FROM closed_trades
    WHERE signal_id = 'clean-sql-test-signal-001'
      AND payload ? 'entry_payload'
      AND coalesce(strategy, payload->'entry_payload'->>'strategy', '') not in ('', 'UNKNOWN')
      AND coalesce(signal_id, payload->'entry_payload'->>'signal_id', '') <> '';

    IF v_count <> 1 OR v_pnl <> 1.8 THEN
        RAISE EXCEPTION 'clean closed trades performance failed count=% pnl=%', v_count, v_pnl;
    END IF;
END $$;

ROLLBACK;
SQL

echo "OK: clean closed trades performance SQL rollback test"
