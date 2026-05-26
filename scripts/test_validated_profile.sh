#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/analytics/validated_profile.py

python - <<'PY'
from finam_core.analytics.validated_profile import is_validated_profile

assert is_validated_profile(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    hour_utc=9,
)

assert not is_validated_profile(
    symbol="BRM6@RTSX",
    strategy="BR_CONSERVATIVE_BREAKOUT",
    timeframe="M5",
    hour_utc=15,
)

print("VALIDATED_PROFILE_OK")
PY
