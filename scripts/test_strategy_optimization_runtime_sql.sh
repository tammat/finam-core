#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PAGER=cat
export PSQL_PAGER=cat

OUT="/tmp/strategy_optimization_runtime_report.tsv"

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
VALUES
(
    'runtime-opt-signal-001',
    'BRM6@RTSX',
    'LONG',
    100.0,
    103.0,
    1.0,
    3.0,
    2.8,
    0.2,
    'INTRADAY',
    'BR_CONSERVATIVE_BREAKOUT_M5',
    'trend_high_vol',
    300,
    now() - interval '5 minutes',
    now(),
    'paper',
    jsonb_build_object(
        'entry_fill_id', 'runtime-opt-entry-fill-001',
        'exit_fill_id', 'runtime-opt-exit-fill-001',
        'entry_payload', jsonb_build_object(
            'origin', 'runtime_optimization_test',
            'signal_id', 'runtime-opt-signal-001',
            'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
            'horizon', 'INTRADAY',
            'regime', 'trend_high_vol',
            'timeframe', 'M5'
        ),
        'exit_payload', jsonb_build_object(
            'origin', 'runtime_optimization_test'
        )
    )
),
(
    'runtime-opt-signal-002',
    'BRM6@RTSX',
    'LONG',
    101.0,
    104.0,
    1.0,
    3.0,
    2.8,
    0.2,
    'INTRADAY',
    'BR_CONSERVATIVE_BREAKOUT_M5',
    'trend_high_vol',
    240,
    now() - interval '4 minutes',
    now(),
    'paper',
    jsonb_build_object(
        'entry_fill_id', 'runtime-opt-entry-fill-002',
        'exit_fill_id', 'runtime-opt-exit-fill-002',
        'entry_payload', jsonb_build_object(
            'origin', 'runtime_optimization_test',
            'signal_id', 'runtime-opt-signal-002',
            'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
            'horizon', 'INTRADAY',
            'regime', 'trend_high_vol',
            'timeframe', 'M5'
        ),
        'exit_payload', jsonb_build_object(
            'origin', 'runtime_optimization_test'
        )
    )
),
(
    'runtime-opt-signal-003',
    'BRM6@RTSX',
    'LONG',
    102.0,
    105.0,
    1.0,
    3.0,
    2.8,
    0.2,
    'INTRADAY',
    'BR_CONSERVATIVE_BREAKOUT_M5',
    'trend_high_vol',
    180,
    now() - interval '3 minutes',
    now(),
    'paper',
    jsonb_build_object(
        'entry_fill_id', 'runtime-opt-entry-fill-003',
        'exit_fill_id', 'runtime-opt-exit-fill-003',
        'entry_payload', jsonb_build_object(
            'origin', 'runtime_optimization_test',
            'signal_id', 'runtime-opt-signal-003',
            'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
            'horizon', 'INTRADAY',
            'regime', 'trend_high_vol',
            'timeframe', 'M5'
        ),
        'exit_payload', jsonb_build_object(
            'origin', 'runtime_optimization_test'
        )
    )
);
SQL

python src/scripts/strategy_optimization_report.py \
  --days 30 \
  --min-trades 3 \
  --out "$OUT"

grep -A 20 "ЛУЧШИЕ_СВЯЗКИ" "$OUT" | grep "BR_CONSERVATIVE_BREAKOUT_M5" >/dev/null
grep -A 20 "PNL_ПО_РЕЖИМАМ" "$OUT" | grep "trend_high_vol" >/dev/null
grep -A 20 "КАНДИДАТЫ_НА_УСИЛЕНИЕ" "$OUT" | grep "BR_CONSERVATIVE_BREAKOUT_M5" >/dev/null

psql "$DATABASE_URL" -P pager=off -v ON_ERROR_STOP=1 <<'SQL'
ROLLBACK;
SQL

echo "OK: слой Execution Intelligence видит clean attributed strategy performance"
