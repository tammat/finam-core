#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export DATABASE_URL="${DATABASE_URL:-postgresql://finam:finam@localhost:5432/finam_core}"

python - <<'PY'
from finam_core.risk.persistent_kill_switch import PersistentKillSwitch

ks = PersistentKillSwitch()
ks.ensure_schema()

ks.deactivate(scope="GLOBAL", reason="test_reset", source="test")
assert ks.is_active() is False

s1 = ks.activate(reason="daily_loss_limit", source="test")
assert s1.active is True
assert ks.is_active() is True

try:
    ks.assert_not_active()
except RuntimeError as exc:
    assert "PERSISTENT_KILL_SWITCH_ACTIVE" in str(exc), exc
    assert "daily_loss_limit" in str(exc), exc
else:
    raise AssertionError("Expected persistent kill switch block")

s2 = ks.deactivate(scope="GLOBAL", reason="manual_clear", source="test")
assert s2.active is False
assert ks.is_active() is False

ks.activate(scope="SYMBOL", symbol="NGH6@RTSX", reason="symbol_mismatch", source="test")
assert ks.is_active(symbol="NGH6@RTSX") is True
assert ks.is_active(symbol="BRM6@RTSX") is False

ks.deactivate(scope="SYMBOL", symbol="NGH6@RTSX", reason="symbol_clear", source="test")
assert ks.is_active(symbol="NGH6@RTSX") is False

print("PERSISTENT_KILL_SWITCH_OK")
PY
