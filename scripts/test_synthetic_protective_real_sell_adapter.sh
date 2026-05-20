#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_synthetic_protective_real_sell_adapter.py

grep -q "SYNTHETIC_PROTECTIVE_SELL_ENABLED" src/scripts/run_synthetic_protective_real_sell_adapter.py
grep -q "SYNTH_PROTECTIVE_REAL_SELL_DRY_RUN_WOULD_SEND" src/scripts/run_synthetic_protective_real_sell_adapter.py
grep -q "synthetic_protective_real_sell" src/scripts/run_synthetic_protective_real_sell_adapter.py
grep -q "place_market_order" src/scripts/run_synthetic_protective_real_sell_adapter.py
grep -q "place_limit_order" src/scripts/run_synthetic_protective_real_sell_adapter.py

echo "OK: synthetic protective real sell adapter"
