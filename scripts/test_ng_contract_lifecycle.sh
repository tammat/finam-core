#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/ng_contract_lifecycle.py \
  src/scripts/ingestion/backfill_ng_lifecycle_bars.py

python - <<'PY'
from finam_core.research.ng_contract_lifecycle import get_ng_symbols, get_ng_contract_window

symbols = get_ng_symbols()
assert "NGM6@RTSX" in symbols
assert "NGZ6@RTSX" in symbols
assert get_ng_contract_window("NGM6@RTSX").start.year == 2026

print("TEST_NG_CONTRACT_LIFECYCLE_OK")
PY
