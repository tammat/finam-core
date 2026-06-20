#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_M1_TO_M5_AGGREGATION_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/run_equity_m1_to_m5_aggregation_v1.py

python3 src/scripts/research/run_equity_m1_to_m5_aggregation_v1.py | tee "$out"

grep -q "VERDICT=EQUITY_M1_TO_M5_AGGREGATION_READY" "$out"
grep -q "TEST_EQUITY_M1_TO_M5_AGGREGATION_V1_OK" "$out"
grep -q '"mode": "dry_run"' "$out"
grep -q '"db_update": 0' "$out"
grep -q '"execution_changed": 0' "$out"

echo "VERDICT=EQUITY_M1_TO_M5_AGGREGATION_DRY_RUN_OK"
echo "TEST_EQUITY_M1_TO_M5_AGGREGATION_V1_OK"
