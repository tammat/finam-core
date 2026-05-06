#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.features.volume_features import BarVolumeFeatureEngine

engine = BarVolumeFeatureEngine(lookback=5, confirm_ratio=1.5)

bars = [{"volume": 100} for _ in range(5)]
bars.append({"volume": 200})

f = engine.evaluate(bars)

assert f.current_volume == 200.0, f
assert f.avg_volume == 100.0, f
assert f.rel_volume == 2.0, f
assert f.volume_confirmed is True, f
assert f.reason == "volume_confirmed", f

bars = [{"volume": 100} for _ in range(5)]
bars.append({"volume": 120})

f = engine.evaluate(bars)

assert f.volume_confirmed is False, f
assert f.reason == "volume_too_low", f

print("BAR_VOLUME_FEATURES_OK")
PY
