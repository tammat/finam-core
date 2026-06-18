#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST SIGNAL STRATEGY ATTRIBUTION GATE V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"

python3 -m py_compile \
  src/finam_core/strategy/signal_strategy_attribution_gate_v1.py \
  src/scripts/research/apply_signal_strategy_discovery_events_v1.py

PYTHONPATH=src python3 - <<'PY'
from finam_core.strategy.signal_strategy_attribution_gate_v1 import SignalStrategyAttributionGateV1

gate = SignalStrategyAttributionGateV1()

cases = [
    {
        "name": "explicit_payload",
        "symbol": "BRN6@RTSX",
        "payload": {
            "strategy": "BR_CONSERVATIVE_BREAKOUT",
            "timeframe": "LIVE",
            "continuous_symbol": "BR_CONT",
        },
        "expected_allowed": True,
        "expected_strategy": "BR_CONSERVATIVE_BREAKOUT",
    },
    {
        "name": "br_reason",
        "symbol": "BRN6@RTSX",
        "payload": {
            "reason": "BR_M5_BREAKOUT_UP_trend_high_vol",
            "timeframe": "M5",
        },
        "expected_allowed": True,
        "expected_strategy": "BR_CONSERVATIVE_BREAKOUT",
    },
    {
        "name": "ng_symbol",
        "symbol": "NGQ6@RTSX",
        "payload": {
            "reason": "support_reversal",
            "timeframe": "M1",
        },
        "expected_allowed": True,
        "expected_strategy": "NG_CONSERVATIVE_BREAKOUT_M1",
    },
    {
        "name": "usdrub_symbol",
        "symbol": "USDRUBF@RTSX",
        "payload": {
            "reason": "regime_signal",
            "timeframe": "LIVE",
        },
        "expected_allowed": True,
        "expected_strategy": "USDRUB_REGIME",
    },
    {
        "name": "unknown_signal",
        "symbol": "UNKNOWN@RTSX",
        "payload": {
            "reason": "new_pattern_unknown_market_structure",
            "timeframe": "M5",
        },
        "expected_allowed": False,
        "expected_strategy": None,
    },
]

for case in cases:
    decision = gate.resolve(symbol=case["symbol"], payload=case["payload"])
    print(
        "ATTRIBUTION_CASE "
        f"name={case['name']} "
        f"symbol={case['symbol']} "
        f"allowed={int(decision.allowed)} "
        f"strategy={decision.strategy} "
        f"timeframe={decision.timeframe} "
        f"continuous_symbol={decision.continuous_symbol} "
        f"reason={decision.reason} "
        f"source={decision.source} "
        f"discovery_required={int(decision.discovery_required)}"
    )

    if decision.allowed != case["expected_allowed"]:
        raise SystemExit(f"FAIL: allowed mismatch for {case['name']}")

    if decision.strategy != case["expected_strategy"]:
        raise SystemExit(f"FAIL: strategy mismatch for {case['name']}")

print("SIGNAL_STRATEGY_ATTRIBUTION_GATE_V1_OK")
PY

PYTHONPATH=src python3 src/scripts/research/apply_signal_strategy_discovery_events_v1.py \
  | tee /tmp/signal_strategy_discovery_events_v1_dry_run.log

grep -q "SIGNAL_STRATEGY_DISCOVERY_EVENTS_V1_OK" /tmp/signal_strategy_discovery_events_v1_dry_run.log
grep -q "VERDICT=SIGNAL_STRATEGY_DISCOVERY_EVENTS_DRY_RUN_READY" /tmp/signal_strategy_discovery_events_v1_dry_run.log

echo TEST_SIGNAL_STRATEGY_ATTRIBUTION_GATE_V1_OK
