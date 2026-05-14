#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real_dry_run
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1
export BROKER_CATEGORY=KSUR
export ENABLE_REAL_EXECUTION_SAFETY_GATE=0
export DISABLE_PERSISTENT_KILL_SWITCH_FOR_TESTS=1

python - <<'PY'
from finam_core.execution.execution_dispatcher import ExecutionDispatcher
from finam_core.execution.real_execution import RealOrderResult


class MockKillSwitch:
    def is_active(self, symbol=None):
        return False


class MockFuturesGate:
    def check(self, symbol=None, execution_mode=None):
        class Decision:
            allowed = True
            reason = "allowed"
        return Decision()


class MockMarginGate:
    def check(self, **kwargs):
        class Decision:
            allowed = True
            reason = "allowed"
            required_margin = 0.0
            margin_utilization_after = 0.0
        return Decision()


class MockRealExecution:
    def execute(self, intent=None, market_state=None):
        return RealOrderResult(
            symbol=intent["symbol"],
            side=intent["side"],
            qty=float(intent["qty"]),
            price=float(intent.get("price") or 0.0),
            status="DRY_RUN_ACCEPTED",
            order_id="mock-real-order-001",
            reason="mock",
            raw={"mock": True},
        )


dispatcher = ExecutionDispatcher(real_execution_engine=MockRealExecution())
dispatcher._persistent_kill_switch = MockKillSwitch()
dispatcher._futures_access_gate = MockFuturesGate()
dispatcher._futures_margin_guard = MockMarginGate()

intent = {
    "symbol": "SBER@MISX",
    "side": "BUY",
    "qty": 1,
    "price": 300,
    "signal_id": "sig-real-001",
    "strategy": "REAL_METADATA_TEST",
    "horizon": "INTRADAY",
    "timeframe": "M5",
}

market_state = {"regime": "trend_high_vol"}

result = dispatcher.execute(intent=intent, market_state=market_state)

assert result.status == "DRY_RUN_ACCEPTED", result
assert result.signal_id == "sig-real-001", result
assert result.payload["signal_id"] == "sig-real-001", result.payload
assert result.payload["strategy"] == "REAL_METADATA_TEST", result.payload
assert result.payload["horizon"] == "INTRADAY", result.payload
assert result.payload["timeframe"] == "M5", result.payload
assert result.payload["regime"] == "trend_high_vol", result.payload

print("OK: execution dispatcher real/dry-run metadata runtime")
PY
