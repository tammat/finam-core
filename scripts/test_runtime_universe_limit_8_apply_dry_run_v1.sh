#!/usr/bin/env bash
set -euo pipefail

echo "=== RUNTIME_UNIVERSE_LIMIT_8_APPLY_DRY_RUN_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/build_runtime_universe_limit_8_apply_dry_run_v1.py
python3 src/scripts/research/build_runtime_universe_limit_8_apply_dry_run_v1.py | tee "$out"

grep -q "VERDICT=RUNTIME_UNIVERSE_LIMIT_8_APPLY_DRY_RUN_READY" "$out"
grep -q "TEST_RUNTIME_UNIVERSE_LIMIT_8_APPLY_DRY_RUN_V1_OK" "$out"
grep -q '"mode": "dry_run"' "$out"
grep -q '"db_update": 0' "$out"
grep -q '"runtime_changed": 0' "$out"
grep -q '"execution_changed": 0' "$out"
grep -q '"target_limit": 8' "$out"
grep -q '"RUNTIME_ACTIVE_UNIVERSE_LIMIT": "8"' "$out"
grep -q '"RUNTIME_MAX_SYMBOLS": "8"' "$out"

echo "VERDICT=RUNTIME_UNIVERSE_LIMIT_8_APPLY_DRY_RUN_TEST_OK"
echo "TEST_RUNTIME_UNIVERSE_LIMIT_8_APPLY_DRY_RUN_V1_OK"
