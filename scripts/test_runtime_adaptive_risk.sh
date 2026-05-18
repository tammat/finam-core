#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/runtime_adaptive_risk.py

python - <<'PY'
from finam_core.runtime.runtime_adaptive_risk import RuntimeAdaptiveRisk


class Cursor:
    def __init__(self, row):
        self.row = row

    def execute(self, *_args, **_kwargs):
        pass

    def fetchone(self):
        return self.row

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class Conn:
    def __init__(self, row):
        self.row = row

    def cursor(self):
        return Cursor(self.row)


allow = RuntimeAdaptiveRisk(Conn(("РАЗРЕШИТЬ", 1.0, "ok", "p1"))).decide(
    regime="trend_down:high_vol",
    policy_id="p1",
)
assert allow.allowed is True
assert allow.risk_multiplier == 1.0

limited = RuntimeAdaptiveRisk(Conn(("ОГРАНИЧИТЬ", 0.5, "limited", "p1"))).decide(
    regime="trend_down:normal_vol",
    policy_id="p1",
)
assert limited.allowed is True
assert limited.risk_multiplier == 0.5

blocked = RuntimeAdaptiveRisk(Conn(("ЗАПРЕТИТЬ", 0.0, "bad", "p1"))).decide(
    regime="range:low_vol",
    policy_id="p1",
)
assert blocked.allowed is False
assert blocked.risk_multiplier == 0.0

missing = RuntimeAdaptiveRisk(Conn(None)).decide(
    regime="UNKNOWN",
    policy_id="p1",
)
assert missing.allowed is True
assert missing.risk_multiplier == 1.0
assert missing.decision == "НЕТ_ПОЛИТИКИ"

print("OK: runtime adaptive risk")
PY
