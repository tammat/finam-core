#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

PIPE="src/finam_core/pipelines/paper_pipeline.py"
CLIENT="src/finam_core/adapters/grpc/orders_client.py"

grep -q "class RealPositionQtyProvider" "$PIPE"
grep -q "get_position_qty_pair" "$PIPE"
grep -q "broker_qty" "$PIPE"
grep -q "local_qty" "$PIPE"
grep -q "FinamOrdersClient(position_qty_provider=RealPositionQtyProvider(self))" "$PIPE"
grep -q "_resolve_position_qty_pair" "$CLIENT"
grep -q "position_qty_provider=None" "$CLIENT"

python -m py_compile src/finam_core/pipelines/paper_pipeline.py
python -m py_compile src/finam_core/adapters/grpc/orders_client.py

echo "REAL_POSITION_QTY_PROVIDER_WIRING_TEST_OK"
