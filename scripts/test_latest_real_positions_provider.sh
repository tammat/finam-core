#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.portfolio.latest_real_positions_provider import LatestRealPositionsProvider

positions = LatestRealPositionsProvider().get_positions()

assert len(positions) >= 1

symbols = {p.symbol for p in positions}

assert "BRM6" in symbols
assert "NGK6" in symbols

for p in positions:
    print(p)

print("LATEST_REAL_POSITIONS_PROVIDER_OK")
PY
