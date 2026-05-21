#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python - <<'PY'
from finam_core.analytics.trade_quality import (
    calculate_trade_quality,
)

qualities = calculate_trade_quality(
    pnls=[10, -5, 20],
    mfes=[20, 5, 25],
    maes=[-2, -10, -3],
)

assert len(qualities) == 3

assert qualities[0].efficiency == 0.5
assert qualities[1].efficiency == -1.0
assert qualities[2].efficiency == 0.8

print("TEST_TRADE_QUALITY_OK")
PY
