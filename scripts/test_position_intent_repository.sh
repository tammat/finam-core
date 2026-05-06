#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.portfolio.position_intent_repository import PositionIntentRepository

r = PositionIntentRepository(ttl_sec=60)

p = r._safe_default("UNKNOWN@MISX")
assert p.horizon == "swing", p
assert p.trade_role == "watch_only", p
assert p.allow_intraday_exit is False, p
assert p.allow_trailing is False, p
assert p.allow_new_buy is False, p
assert p.allow_reduce is False, p
assert p.allow_increase is False, p
assert p.enabled is False, p

print("POSITION_INTENT_REPOSITORY_SAFE_DEFAULT_OK")
PY
