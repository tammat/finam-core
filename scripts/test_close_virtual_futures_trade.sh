#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export ENABLE_TRADE_SIGNAL_ALERTS=0

python -m scripts.close_virtual_futures_trade \
  --symbol BRN6@RTSX \
  --side BUY \
  --entry-price 80.0 \
  --exit-price 82.0 \
  --qty 1 \
  --stop-loss 79.0 \
  --take-profit 82.0 \
  --reason test_manual_close | grep "VIRTUAL_TRADE_CLOSED"

echo "CLOSE_VIRTUAL_FUTURES_TRADE_OK"
