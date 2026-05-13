#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

if grep -R "PlaceOrder\|place_order\|TradeAPI\|OrdersService\|place_market_order\|place_limit_order" -n src/finam_core/ai; then
  echo "ERROR: AI layer contains trading API references"
  exit 1
fi

echo "OK: AI layer has no trading API references"
