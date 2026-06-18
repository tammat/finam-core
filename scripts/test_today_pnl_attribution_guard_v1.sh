#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST TODAY PNL ATTRIBUTION GUARD V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile src/finam_core/storage/trade_context_guard_v1.py

PYTHONPATH=src python3 - <<'PY'
from finam_core.storage.trade_context_guard_v1 import TradeContextGuardV1

guard = TradeContextGuardV1()

cases = [
    {
        "name": "complete_context",
        "symbol": "USDRUBF@RTSX",
        "strategy": "USDRUB_REGIME",
        "timeframe": "LIVE",
        "continuous_symbol": "USDRUB_CONT",
        "payload": {},
        "expected_allowed": True,
        "expected_strategy": "USDRUB_REGIME",
    },
    {
        "name": "payload_restore",
        "symbol": "USDRUBF@RTSX",
        "strategy": None,
        "timeframe": None,
        "continuous_symbol": None,
        "payload": {
            "trade_context_snapshot": {
                "strategy": "USDRUB_REGIME",
                "timeframe": "LIVE",
                "continuous_symbol": "USDRUB_CONT",
            }
        },
        "expected_allowed": True,
        "expected_strategy": "USDRUB_REGIME",
    },
    {
        "name": "known_route_restore",
        "symbol": "NGM6@RTSX",
        "strategy": None,
        "timeframe": None,
        "continuous_symbol": None,
        "payload": {},
        "expected_allowed": True,
        "expected_strategy": "NG_CONSERVATIVE_BREAKOUT_M1",
    },
    {
        "name": "unknown_route_reject",
        "symbol": "UNKNOWN@RTSX",
        "strategy": None,
        "timeframe": None,
        "continuous_symbol": None,
        "payload": {},
        "expected_allowed": False,
        "expected_strategy": "UNKNOWN",
    },
]

for case in cases:
    decision = guard.normalize(
        symbol=case["symbol"],
        strategy=case["strategy"],
        timeframe=case["timeframe"],
        continuous_symbol=case["continuous_symbol"],
        payload=case["payload"],
    )

    print(
        "GUARD_CASE "
        f"name={case['name']} "
        f"allowed={int(decision.allowed)} "
        f"strategy={decision.strategy} "
        f"timeframe={decision.timeframe} "
        f"continuous_symbol={decision.continuous_symbol} "
        f"reason={decision.reason}"
    )

    assert decision.allowed is case["expected_allowed"], case
    assert decision.strategy == case["expected_strategy"], case

print("TODAY_PNL_ATTRIBUTION_GUARD_V1_OK")
PY

echo TEST_TODAY_PNL_ATTRIBUTION_GUARD_V1_OK
