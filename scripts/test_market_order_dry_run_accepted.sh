#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

FILE="src/finam_core/adapters/grpc/orders_client.py"

grep -q "DRY_RUN_ACCEPTED" "$FILE"
grep -q "real_order_confirm_disabled" "$FILE"
grep -q "market_order_dry_run" "$FILE"
grep -q "place_order_sent" "$FILE"

python -m py_compile src/finam_core/adapters/grpc/orders_client.py

echo "MARKET_ORDER_DRY_RUN_ACCEPTED_TEST_OK"
