#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

SYMBOL="${1:-BRM6@RTSX}"
STRATEGY="${2:-br_conservative_breakout}"
TIMEFRAME="${3:-M5}"
COMMISSION="${4:-0.0001}"

python scripts/analytics/build_trade_statistics.py \
  --symbol "$SYMBOL" \
  --strategy "$STRATEGY" \
  --timeframe "$TIMEFRAME" \
  --fallback-commission-rate "$COMMISSION" \
  --migrate

python scripts/analytics/build_equity_curve.py \
  --symbol "$SYMBOL" \
  --strategy "$STRATEGY" \
  --timeframe "$TIMEFRAME"

python scripts/analytics/build_drawdown_summary.py \
  --symbol "$SYMBOL" \
  --strategy "$STRATEGY" \
  --timeframe "$TIMEFRAME" \
  --fallback-commission-rate "$COMMISSION" \
  --migrate

python scripts/analytics/build_intrabar_trade_quality.py \
  --symbol "$SYMBOL" \
  --strategy "$STRATEGY" \
  --timeframe "$TIMEFRAME" \
  --migrate

python scripts/analytics/build_exit_optimization.py \
  --symbol "$SYMBOL" \
  --strategy "$STRATEGY" \
  --timeframe "$TIMEFRAME" \
  --migrate

python scripts/analytics/build_exit_policy_simulation.py \
  --symbol "$SYMBOL" \
  --strategy "$STRATEGY" \
  --timeframe "$TIMEFRAME" \
  --migrate

python scripts/analytics/select_exit_policy.py \
  --symbol "$SYMBOL" \
  --strategy "$STRATEGY" \
  --timeframe "$TIMEFRAME" \
  --min-profit-factor 1.2 \
  --max-allowed-drawdown -10 \
  --migrate

echo "ANALYTICS_REFRESH_ALL_OK symbol=$SYMBOL strategy=$STRATEGY timeframe=$TIMEFRAME"
