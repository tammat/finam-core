#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_MOEX_M1_M5_BACKFILL_V1 ==="

out="$(mktemp)"

python3 -m py_compile src/scripts/research/run_equity_moex_m1_m5_backfill_v1.py

python3 src/scripts/research/run_equity_moex_m1_m5_backfill_v1.py --days 5 | tee "$out"

grep -q "VERDICT=EQUITY_MOEX_M1_M5_BACKFILL_READY" "$out"
grep -q "TEST_EQUITY_MOEX_M1_M5_BACKFILL_V1_OK" "$out"
grep -q '"mode": "dry_run"' "$out"
grep -q '"db_update": 0' "$out"
grep -q '"execution_changed": 0' "$out"

echo "VERDICT=EQUITY_MOEX_M1_M5_BACKFILL_DRY_RUN_OK"
echo "TEST_EQUITY_MOEX_M1_M5_BACKFILL_V1_OK"
