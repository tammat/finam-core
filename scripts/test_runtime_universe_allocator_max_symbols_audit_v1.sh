#!/usr/bin/env bash
set -euo pipefail

echo "=== RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_AUDIT_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_runtime_universe_allocator_max_symbols_audit_v1.py
python3 src/scripts/research/build_runtime_universe_allocator_max_symbols_audit_v1.py | tee "$out"

grep -q "VERDICT=RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_AUDIT_READY" "$out"
grep -q "TEST_RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_AUDIT_V1_OK" "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"
grep -q '"max_symbols": 5' "$out"
grep -q '"max_symbols": 8' "$out"
grep -q '"max_symbols": 10' "$out"

echo "VERDICT=RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_AUDIT_TEST_OK"
echo "TEST_RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_AUDIT_V1_OK"
