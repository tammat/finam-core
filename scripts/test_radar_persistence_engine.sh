#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.data.radar_persistence_engine import RadarPersistenceEngine

engine = RadarPersistenceEngine()

rows = [
    {"ts": "2026-05-08 10:00:00", "symbol": "YDEX@MISX", "score": 4.0, "relative_strength": 2.0},
    {"ts": "2026-05-08 10:30:00", "symbol": "YDEX@MISX", "score": 5.5, "relative_strength": 3.0},
    {"ts": "2026-05-08 11:00:00", "symbol": "YDEX@MISX", "score": 7.2, "relative_strength": 4.0},
]

res = engine.classify(rows)

assert res is not None
assert res.symbol == "YDEX@MISX"
assert res.appearances == 3
assert res.score_delta > 1.0
assert res.state == "STRONG_INTRADAY", res

rows2 = [
    {"ts": "2026-05-08 10:00:00", "symbol": "SBER@MISX", "score": 5.0, "relative_strength": 1.0},
    {"ts": "2026-05-08 10:30:00", "symbol": "SBER@MISX", "score": 4.6, "relative_strength": 0.8},
    {"ts": "2026-05-08 11:00:00", "symbol": "SBER@MISX", "score": 3.5, "relative_strength": 0.2},
]

res2 = engine.classify(rows2)

assert res2 is not None
assert res2.state == "FADING", res2

print("RADAR_PERSISTENCE_ENGINE_OK")
PY
