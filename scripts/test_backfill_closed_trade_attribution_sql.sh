#!/usr/bin/env bash
set -euo pipefail

export PAGER=cat
export PSQL_PAGER=cat

psql "$DATABASE_URL" -P pager=off -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

INSERT INTO signals (
    signal_id, symbol, side, strategy, horizon, timeframe, regime, status, payload
)
VALUES (
    'bf-test-signal-001',
    'BRM6@RTSX',
    'BUY',
    'BR_CONSERVATIVE_BREAKOUT_M5',
    'INTRADAY',
    'M5',
    'trend_high_vol',
    'FILLED',
    '{}'::jsonb
)
ON CONFLICT (signal_id) DO NOTHING;

INSERT INTO signal_fills (
    signal_id, fill_id, symbol, side, qty, price
)
VALUES (
    'bf-test-signal-001',
    'bf-test-entry-fill-001',
    'BRM6@RTSX',
    'BUY',
    1,
    100
);

INSERT INTO closed_trades (
    signal_id, symbol, side,
    entry_price, exit_price, qty,
    gross_pnl, net_pnl, commission,
    horizon, strategy, regime,
    entry_ts, exit_ts, trade_source, payload
)
VALUES (
    NULL,
    'BRM6@RTSX',
    'LONG',
    100,
    102,
    1,
    2,
    1.8,
    0.2,
    NULL,
    'UNKNOWN',
    'UNKNOWN',
    now() - interval '5 minutes',
    now(),
    'paper',
    jsonb_build_object(
      'entry_fill_id', 'bf-test-entry-fill-001',
      'exit_fill_id', 'bf-test-exit-fill-001',
      'entry_payload', '{}'::jsonb,
      'exit_payload', '{}'::jsonb
    )
);

WITH matched AS (
    SELECT
        ct.id as closed_trade_id,
        s.signal_id,
        s.strategy,
        s.horizon,
        s.regime
    FROM closed_trades ct
    JOIN signal_fills sf
      ON sf.fill_id = ct.payload->>'entry_fill_id'
      OR sf.fill_id = ct.payload->>'exit_fill_id'
    JOIN signals s
      ON s.signal_id = sf.signal_id
    WHERE ct.payload->>'entry_fill_id' = 'bf-test-entry-fill-001'
)
UPDATE closed_trades ct
SET
    signal_id = matched.signal_id,
    strategy = matched.strategy,
    horizon = matched.horizon,
    regime = matched.regime,
    payload = jsonb_set(
        coalesce(ct.payload, '{}'::jsonb),
        '{attribution_backfill}',
        jsonb_build_object(
            'source', 'signal_fills',
            'signal_id', matched.signal_id,
            'strategy', matched.strategy,
            'horizon', matched.horizon,
            'regime', matched.regime
        ),
        true
    )
FROM matched
WHERE ct.id = matched.closed_trade_id;

DO $$
DECLARE
    v_count int;
BEGIN
    SELECT count(*)
    INTO v_count
    FROM closed_trades
    WHERE signal_id = 'bf-test-signal-001'
      AND strategy = 'BR_CONSERVATIVE_BREAKOUT_M5'
      AND horizon = 'INTRADAY'
      AND regime = 'trend_high_vol'
      AND payload ? 'attribution_backfill';

    IF v_count <> 1 THEN
        RAISE EXCEPTION 'backfill attribution failed count=%', v_count;
    END IF;
END $$;

ROLLBACK;
SQL

echo "OK: closed trade attribution backfill SQL rollback"
