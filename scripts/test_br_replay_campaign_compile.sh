#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/run_br_replay_campaign.py

python - <<'PY'
from datetime import timezone
from scripts.run_br_replay_campaign import build_windows, parse_dt

start = parse_dt("2026-05-19")
end = parse_dt("2026-05-26")
windows = build_windows(start, end, 3)

assert len(windows) == 3
assert windows[0].from_ts.tzinfo is not None
assert windows[0].from_ts.tzinfo == timezone.utc
assert windows[-1].to_ts == end

print("BR_REPLAY_CAMPAIGN_COMPILE_OK")
PY
