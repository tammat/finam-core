#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/runtime/active_policy_reader.py

python - <<'PY'
from finam_core.runtime.active_policy_reader import ActivePolicyRuntimeReader


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


reader = ActivePolicyRuntimeReader(Conn((
    "active-conservative-policy-v1",
    "conservative",
    "SELECTIVE",
    55.7,
    111.6,
    37.2,
    0.6667,
    True,
)))

d = reader.get_active(objective="conservative")

assert d is not None
assert d.selected_mode == "SELECTIVE"
assert d.active is True

missing = ActivePolicyRuntimeReader(Conn(None)).get_active(objective="risk")
assert missing is None

print("OK: active policy reader")
PY
