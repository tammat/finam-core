#!/usr/bin/env bash
set -euo pipefail

echo "=== EQUITY_BREAKOUT_PROFILE_TIMEFRAME_PROBE_V1 ==="

python3 - <<'PY'
from src.scripts.research.build_multi_asset_breakout_watch_v2 import resolve_instrument_signal_profile

symbols = ["NVTK@MISX", "OZON@MISX", "T@MISX", "X5@MISX", "PLZL@MISX", "LKOH@MISX"]

for symbol in symbols:
    profile = resolve_instrument_signal_profile(symbol, "M5")
    print(
        f"PROFILE symbol={symbol} "
        f"input_tf=M5 "
        f"profile_timeframe={profile.timeframe} "
        f"asset_class={profile.asset_class} "
        f"atr_min_pct={profile.atr_min_pct} "
        f"volume_mult={profile.volume_mult}"
    )

print("VERDICT=EQUITY_BREAKOUT_PROFILE_TIMEFRAME_PROBE_READY")
print("TEST_EQUITY_BREAKOUT_PROFILE_TIMEFRAME_PROBE_V1_OK")
PY
