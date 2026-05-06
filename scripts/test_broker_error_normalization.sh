#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
from finam_core.adapters.grpc.orders_client import FinamOrdersClient

c = FinamOrdersClient()

reason, raw = c._normalize_broker_error(
    Exception("INVALID_ARGUMENT: [666] Attention! An uncovered position may arise/increase")
)

assert reason == "BROKER_UNCOVERED_POSITION_WARNING", reason
assert raw["retryable"] is False

reason2, raw2 = c._normalize_broker_error(
    Exception("INVALID_ARGUMENT: [145]No enough coverage. You need 27392.75 RUR Недостаток обеспечения")
)

assert reason2 == "BROKER_NOT_ENOUGH_COVERAGE", reason2
assert raw2["retryable"] is False

print("BROKER_ERROR_NORMALIZATION_OK")
PY
