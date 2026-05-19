#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/capital_growth_telegram_digest.py \
  src/scripts/send_capital_growth_digest.py

python - <<'PY'
from finam_core.runtime.capital_growth_telegram_digest import (
    CapitalGrowthTelegramDigest,
    GrowthDigestRow,
)

text = CapitalGrowthTelegramDigest().build(
    profile="growth",
    rows=[
        GrowthDigestRow(
            symbol="SBER@MISX",
            decision="ALERT",
            score=84,
            expected_value=2.5,
            risk_pct=0.012,
            qty=37,
            rr=2.3,
            mode="GROWTH_A_GRADE",
            reason="top setup",
        )
    ],
)

assert "SBER@MISX" in text
assert "GROWTH_A_GRADE" in text

print(text)
print("OK: capital growth digest")
PY
