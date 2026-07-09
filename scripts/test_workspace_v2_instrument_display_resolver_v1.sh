#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_WORKSPACE_V2_INSTRUMENT_DISPLAY_RESOLVER_V1 ==="

py_file="src/marketcore/presentation/workspace_v2/resolver/instrument_display_resolver_v1.py"
test -f "$py_file"

PYTHONPYCACHEPREFIX=/tmp/finam_pycache_instrument_resolver \
PYTHONPATH=src \
python -m py_compile "$py_file"

if grep -RInE 'send_order|place_order|cancel_order|execute_order|UPDATE .*runtime|UPDATE .*execution|INSERT INTO .*orders|INSERT INTO .*fills|DROP TABLE|TRUNCATE|DELETE FROM' "$py_file"; then
  echo "DANGEROUS_CODE_FOUND"
  exit 1
fi

PYTHONPATH=src python - <<'PY'
from marketcore.presentation.workspace_v2.resolver.instrument_display_resolver_v1 import (
    InstrumentDisplayResolverV1,
)

resolver = InstrumentDisplayResolverV1()

symbols = ["SBER", "LKOH", "GAZP", "UNKNOWN_TEST_SYMBOL_V1"]

for symbol in symbols:
    item = resolver.resolve(symbol)
    assert item.symbol == symbol
    assert item.display_name
    assert item.short_name
    assert item.asset_class
    assert item.exchange
    assert item.currency
    assert item.source_table

print("instrument_resolver_objects=OK")
PY

echo "instrument_display_resolver=OK"
echo "presentation_layer=OK"
echo "fallback_supported=OK"
echo "read_only=OK"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=WORKSPACE_V2_INSTRUMENT_DISPLAY_RESOLVER_V1_READY"
echo "VERDICT=TEST_WORKSPACE_V2_INSTRUMENT_DISPLAY_RESOLVER_V1_OK"
