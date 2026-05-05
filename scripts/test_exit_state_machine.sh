#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.strategy.exit_engine import ExitStateMachine

sm = ExitStateMachine(ttl_sec=30)

sm.on_position("BRM6@RTSX", 1.0)

ok, reason = sm.allow_request("BRM6@RTSX", "SELL", 1.0, "time_exit")
assert ok, reason

ok, reason = sm.allow_request("BRM6@RTSX", "SELL", 1.0, "time_exit")
assert not ok
assert reason == "duplicate_exit_request_active"

sm.on_fill("BRM6@RTSX")
sm.on_position("BRM6@RTSX", 0.0)

ok, reason = sm.allow_request("BRM6@RTSX", "SELL", 1.0, "time_exit")
assert ok, reason

print("EXIT_STATE_MACHINE_OK")
PY
