#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

python3 - <<'PY'
from datetime import datetime, timezone

from finam_core.analytics.exit_reason_trusted_window_policy_v1 import (
    ExitReasonTrustedWindowPolicyV1,
)

p = ExitReasonTrustedWindowPolicyV1()

assert p.evaluate(
    "BR",
    datetime(2026,6,4,tzinfo=timezone.utc)
).trusted is False

assert p.evaluate(
    "BR",
    datetime(2026,6,5,tzinfo=timezone.utc)
).trusted is True

assert p.evaluate(
    "NG",
    datetime(2026,6,2,tzinfo=timezone.utc)
).trusted is False

assert p.evaluate(
    "NG",
    datetime(2026,6,3,tzinfo=timezone.utc)
).trusted is True

print("EXIT_REASON_TRUSTED_WINDOW_POLICY_V1_OK")
PY

echo TEST_EXIT_REASON_TRUSTED_WINDOW_POLICY_V1_OK
