#!/usr/bin/env bash
set -euo pipefail

echo "=== RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_PLAN_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_runtime_universe_allocator_max_symbols_plan_v1.py
python3 src/scripts/research/build_runtime_universe_allocator_max_symbols_plan_v1.py | tee "$out"

grep -q "VERDICT=RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_PLAN_READY" "$out"
grep -q "TEST_RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_PLAN_V1_OK" "$out"
grep -q '"mode": "plan_only"' "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"
grep -q '"recommended_limit": 8' "$out"
grep -q 'RUNTIME_ACTIVE_UNIVERSE_LIMIT' "$out"
grep -q 'RUNTIME_MAX_SYMBOLS' "$out"

echo "VERDICT=RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_PLAN_TEST_OK"
echo "TEST_RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_PLAN_V1_OK"
