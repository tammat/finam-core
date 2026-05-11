#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_protective_order_links.sql
test -f src/finam_core/execution/protective_order_link.py
test -f src/finam_core/execution/protective_order_link_repository.py

grep -q "CREATE TABLE IF NOT EXISTS protective_order_links" sql/20260511_protective_order_links.sql
grep -q "idx_protective_order_links_entry_order_id" sql/20260511_protective_order_links.sql
grep -q "class ProtectiveOrderLink" src/finam_core/execution/protective_order_link.py
grep -q "is_protected" src/finam_core/execution/protective_order_link.py
grep -q "class ProtectiveOrderLinkRepository" src/finam_core/execution/protective_order_link_repository.py
grep -q "PROTECTIVE_ORDER_LINK_SAVE_FAILED" src/finam_core/execution/protective_order_link_repository.py

PYTHONPATH=src python - <<'PY'
from finam_core.execution.protective_order_link import ProtectiveOrderLink

entry_only = ProtectiveOrderLink(symbol="SBER@MISX", side="BUY", qty=1, entry_order_id="entry_1")
with_stop = ProtectiveOrderLink(symbol="SBER@MISX", side="BUY", qty=1, entry_order_id="entry_2", stop_order_id="stop_2")

assert entry_only.has_stop is False
assert entry_only.has_take is False
assert entry_only.is_protected is False
assert with_stop.has_stop is True
assert with_stop.is_protected is True

print("PROTECTIVE_ORDER_LINK_RUNTIME_OK")
PY

python -m py_compile src/finam_core/execution/protective_order_link.py
python -m py_compile src/finam_core/execution/protective_order_link_repository.py

echo "PROTECTIVE_ORDER_LINK_TEST_OK"
