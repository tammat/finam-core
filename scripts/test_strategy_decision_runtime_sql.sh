#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export PAGER=cat
export PSQL_PAGER=cat

OUT="/tmp/strategy_decision_report.tsv"

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
    'decision-test-signal-001', 'BRM6@RTSX', 'LONG',
    100, 103, 1,
    3, 2.8, 0.2,
    'INTRADAY', 'BR_CONSERVATIVE_BREAKOUT_M5', 'trend_high_vol',
    300, now() - interval '5 minutes', now(),
    'paper',
    jsonb_build_object(
      'entry_payload', jsonb_build_object(
        'origin', 'decision_runtime_test',
        'signal_id', 'decision-test-signal-001',
        'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
        'horizon', 'INTRADAY',
        'regime', 'trend_high_vol',
        'timeframe', 'M5'
      )
    )
),
(
    'decision-test-signal-002', 'BRM6@RTSX', 'LONG',
    101, 104, 1,
    3, 2.8, 0.2,
    'INTRADAY', 'BR_CONSERVATIVE_BREAKOUT_M5', 'trend_high_vol',
    240, now() - interval '4 minutes', now(),
    'paper',
    jsonb_build_object(
      'entry_payload', jsonb_build_object(
        'origin', 'decision_runtime_test',
        'signal_id', 'decision-test-signal-002',
        'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
        'horizon', 'INTRADAY',
        'regime', 'trend_high_vol',
        'timeframe', 'M5'
      )
    )
),
(
    'decision-test-signal-003', 'BRM6@RTSX', 'LONG',
    102, 105, 1,
    3, 2.8, 0.2,
    'INTRADAY', 'BR_CONSERVATIVE_BREAKOUT_M5', 'trend_high_vol',
    180, now() - interval '3 minutes', now(),
    'paper',
    jsonb_build_object(
      'entry_payload', jsonb_build_object(
        'origin', 'decision_runtime_test',
        'signal_id', 'decision-test-signal-003',
        'strategy', 'BR_CONSERVATIVE_BREAKOUT_M5',
        'horizon', 'INTRADAY',
        'regime', 'trend_high_vol',
        'timeframe', 'M5'
      )
    )
);
SQL

python src/scripts/strategy_decision_report.py \
  --days 30 \
  --min-trades 3 \
  --out "$OUT"

grep -A 20 "РЕШЕНИЯ_ПО_СТРАТЕГИЯМ" "$OUT" | grep "УСИЛИТЬ" >/dev/null
grep -A 20 "УСИЛИТЬ" "$OUT" | grep "BR_CONSERVATIVE_BREAKOUT_M5" >/dev/null

psql "$DATABASE_URL" -P pager=off -v ON_ERROR_STOP=1 <<'SQL'
ROLLBACK;
SQL

echo "OK: отчёт решений видит clean strategy decision"
