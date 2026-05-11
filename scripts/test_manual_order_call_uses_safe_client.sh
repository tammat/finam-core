#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

grep -q "from finam_core.adapters.grpc.orders_client import FinamOrdersClient" src/scripts/manual_order_call.py
grep -q "FinamOrdersClient()" src/scripts/manual_order_call.py
grep -q "place_market_order" src/scripts/manual_order_call.py

! grep -q "from finam_core.adapters.grpc.orders import" src/scripts/manual_order_call.py
! grep -q "stub.PlaceOrder" src/scripts/manual_order_call.py

python -m py_compile src/scripts/manual_order_call.py

echo "MANUAL_ORDER_CALL_USES_SAFE_CLIENT_TEST_OK"
