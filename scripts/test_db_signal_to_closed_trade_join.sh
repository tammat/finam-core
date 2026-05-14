#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PAGER=cat
export PSQL_PAGER=cat

python -m py_compile src/scripts/run_closed_trade_report.py

psql "$DATABASE_URL" -P pager=off -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;

INSERT INTO signals (
    signal_id,
    symbol,
    side,
    strategy,
    horizon,
    timeframe,
    regime,
    status,
    payload
)
VALUES (
    'db-test-signal-001',
    'BRM6@RTSX',
    'BUY',
    'BR_CONSERVATIVE_BREAKOUT_M5',
    'INTRADAY',
    'M5',
    'trend_high_vol',
    'FILLED',
    '{"test": true}'::jsonb
)
ON CONFLICT (signal_id) DO NOTHING;

INSERT INTO trades (
    symbol,
    side,
    qty,
    price,
    commission,
    fill_id,
    origin,
    trade_source,
    payload
)
VALUES
(
    'BRM6@RTSX',
    'BUY',
    1,
    100,
    0.1,
    'db-test-entry-fill-001',
    'paper',
    'paper',
    '{"paper_only": true, "execution_type": "paper"}'::jsonb
),
(
    'BRM6@RTSX',
    'SELL',
    1,
    102,
    0.1,
    'db-test-exit-fill-001',
    'paper',
    'paper',
    '{"paper_only": true, "execution_type": "paper"}'::jsonb
);

INSERT INTO signal_fills (
    signal_id,
    fill_id,
    symbol,
    side,
    qty,
    price
)
VALUES
(
    'db-test-signal-001',
    'db-test-entry-fill-001',
    'BRM6@RTSX',
    'BUY',
    1,
    100
),
(
    'db-test-signal-001',
    'db-test-exit-fill-001',
    'BRM6@RTSX',
    'SELL',
    1,
    102
);

WITH enriched AS (
    SELECT
        t.fill_id,
        coalesce(t.payload, '{}'::jsonb) ||
        jsonb_strip_nulls(
            jsonb_build_object(
                'signal_id', s.signal_id,
                'strategy', s.strategy,
                'horizon', s.horizon,
                'regime', s.regime,
                'timeframe', s.timeframe
            )
        ) as payload
    FROM trades t
    LEFT JOIN signal_fills sf
        ON sf.fill_id = t.fill_id
    LEFT JOIN signals s
        ON s.signal_id = sf.signal_id
    WHERE t.fill_id in ('db-test-entry-fill-001', 'db-test-exit-fill-001')
)
SELECT
    count(*) as rows_count,
    count(*) filter (where payload->>'signal_id' = 'db-test-signal-001') as with_signal_id,
    count(*) filter (where payload->>'strategy' = 'BR_CONSERVATIVE_BREAKOUT_M5') as with_strategy,
    count(*) filter (where payload->>'horizon' = 'INTRADAY') as with_horizon,
    count(*) filter (where payload->>'regime' = 'trend_high_vol') as with_regime
FROM enriched;

DO $$
DECLARE
    v_rows int;
    v_signal int;
    v_strategy int;
    v_horizon int;
    v_regime int;
BEGIN
    WITH enriched AS (
        SELECT
            t.fill_id,
            coalesce(t.payload, '{}'::jsonb) ||
            jsonb_strip_nulls(
                jsonb_build_object(
                    'signal_id', s.signal_id,
                    'strategy', s.strategy,
                    'horizon', s.horizon,
                    'regime', s.regime,
                    'timeframe', s.timeframe
                )
            ) as payload
        FROM trades t
        LEFT JOIN signal_fills sf
            ON sf.fill_id = t.fill_id
        LEFT JOIN signals s
            ON s.signal_id = sf.signal_id
        WHERE t.fill_id in ('db-test-entry-fill-001', 'db-test-exit-fill-001')
    )
    SELECT
        count(*),
        count(*) filter (where payload->>'signal_id' = 'db-test-signal-001'),
        count(*) filter (where payload->>'strategy' = 'BR_CONSERVATIVE_BREAKOUT_M5'),
        count(*) filter (where payload->>'horizon' = 'INTRADAY'),
        count(*) filter (where payload->>'regime' = 'trend_high_vol')
    INTO v_rows, v_signal, v_strategy, v_horizon, v_regime
    FROM enriched;

    IF v_rows <> 2 OR v_signal <> 2 OR v_strategy <> 2 OR v_horizon <> 2 OR v_regime <> 2 THEN
        RAISE EXCEPTION 'metadata join failed rows=% signal=% strategy=% horizon=% regime=%',
            v_rows, v_signal, v_strategy, v_horizon, v_regime;
    END IF;
END $$;

ROLLBACK;
SQL

echo "OK: db signal -> signal_fills -> trades metadata join"
