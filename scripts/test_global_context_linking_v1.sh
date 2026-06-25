#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_CONTEXT_LINKING_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_global_context_linking_v1.py

src/scripts/research/build_global_context_linking_v1.py \
  | tee /tmp/global_context_linking_v1.out

grep -q "GLOBAL_CONTEXT_LINKING_V1" /tmp/global_context_linking_v1.out
grep -q "context_links=" /tmp/global_context_linking_v1.out
grep -q "context_missing=" /tmp/global_context_linking_v1.out
grep -q "context_codes=FX_USDRUB,ENERGY_BR" /tmp/global_context_linking_v1.out
grep -q "db_update=1" /tmp/global_context_linking_v1.out
grep -q "runtime_changed=0" /tmp/global_context_linking_v1.out
grep -q "execution_changed=0" /tmp/global_context_linking_v1.out
grep -q "real_trading_enabled=0" /tmp/global_context_linking_v1.out
grep -q "orders_sent=0" /tmp/global_context_linking_v1.out
grep -q "VERDICT=GLOBAL_CONTEXT_LINKING_OK" /tmp/global_context_linking_v1.out

echo "TEST_GLOBAL_CONTEXT_LINKING_V1_OK"
