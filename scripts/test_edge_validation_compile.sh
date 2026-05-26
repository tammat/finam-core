#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
    src/finam_core/analytics/edge_validation.py

python - <<'PY'
from finam_core.analytics.edge_validation import build_edge_bucket

bucket = build_edge_bucket(
    symbol="BRM6@RTSX",
    profile="day",
    pnl_values=[10.0, -5.0, 15.0],
)

assert bucket.trades == 3
assert bucket.wins == 2
assert bucket.losses == 1
assert bucket.gross_pnl == 20.0
assert round(bucket.winrate, 4) == 0.6667

print("EDGE_VALIDATION_COMPILE_OK")
PY
