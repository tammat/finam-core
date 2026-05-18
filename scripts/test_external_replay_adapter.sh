#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/replay/external_replay_adapter.py

python - <<'PY'
from finam_core.replay.external_replay_adapter import ExternalReplayAdapter

adapter = ExternalReplayAdapter()

events = adapter.load_events(
    symbol="SBER@MISX",
    timeframe="D1",
    date_from="2025-05-15",
    date_to="2025-05-16",
)

assert len(events) > 0

e = events[0]

assert e.symbol == "SBER@MISX"
assert e.close > 0
assert e.volume >= 0

print("EVENTS:", len(events))
print("FIRST:", e)
print("OK: external replay adapter")
PY
