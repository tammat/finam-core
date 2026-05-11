#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

FILE="src/finam_core/adapters/grpc/orders_client.py"

grep -q "ProtectiveOrderLink" "$FILE"
grep -q "ProtectiveOrderLinkRepository" "$FILE"
grep -q "self.protective_link_repository = ProtectiveOrderLinkRepository()" "$FILE"
grep -q 'source="market_order_ack"' "$FILE"
grep -q "entry_order_id=ack.order_id" "$FILE"
grep -q "stop_order_id=None" "$FILE"
grep -q "take_order_id=None" "$FILE"
grep -q 'status="OPEN"' "$FILE"

PYTHONPATH=src python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/adapters/grpc/orders_client.py").read_text(encoding="utf-8")

market_idx = text.index('self.order_ack_logger.log(ack, source="market_order")')
link_idx = text.index("self.protective_link_repository.save", market_idx)

assert link_idx > market_idx
assert 'source="stop_order"' in text
assert 'source="limit_order"' in text

print("PROTECTIVE_ORDER_LINK_AFTER_ENTRY_ACK_RUNTIME_OK")
PY

python -m py_compile src/finam_core/execution/protective_order_link.py
python -m py_compile src/finam_core/execution/protective_order_link_repository.py
python -m py_compile src/finam_core/adapters/grpc/orders_client.py

echo "PROTECTIVE_ORDER_LINK_AFTER_ENTRY_ACK_TEST_OK"
