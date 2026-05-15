#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src
export EXECUTION_MODE=real_dry_run
export REAL_EXECUTION_ENABLED=1
export REAL_ORDER_CONFIRM=1
export BROKER_CATEGORY=KSUR
export ENABLE_REAL_EXECUTION_SAFETY_GATE=0

python -m py_compile \
  src/finam_core/execution/execution_dispatcher.py \
  src/finam_core/execution/strategy_runtime_gate.py

python - <<'PY'
import uuid
from dataclasses import dataclass

from finam_core.execution.execution_dispatcher import ExecutionDispatcher
from finam_core.execution.real_execution import RealOrderResult


@dataclass
class GateDecision:
    allowed: bool
    watch_only: bool
    original_qty: float
    adjusted_qty: float
    risk_multiplier: float
    status: str
    reason: str


class MockGate:
    def __init__(self, decision):
        self.decision = decision
        self.seen_intent = None

    def evaluate(self, intent):
        self.seen_intent = dict(intent)
        return self.decision


class MockKillSwitch:
    def is_active(self, symbol=None):
        return False


class MockFuturesGate:
    def check(self, symbol=None, execution_mode=None):
        class Decision:
            allowed = True
            reason = "разрешено"
        return Decision()


class MockMarginGate:
    def check(self, **kwargs):
        class Decision:
            allowed = True
            reason = "разрешено"
            required_margin = 0.0
            margin_utilization_after = 0.0
        return Decision()


class MockRealExecution:
    def __init__(self):
        self.intent = None

    def execute(self, intent=None, market_state=None):
        self.intent = dict(intent)
        return RealOrderResult(
            symbol=intent["symbol"],
            side=intent["side"],
            qty=float(intent["qty"]),
            price=float(intent.get("price") or 0.0),
            status="DRY_RUN_ACCEPTED",
            order_id="mock-order",
            reason="тест",
            raw={},
        )


# Блокировка стратегии до execution.
blocked_gate = MockGate(GateDecision(
    allowed=False,
    watch_only=True,
    original_qty=2.0,
    adjusted_qty=0.0,
    risk_multiplier=0.0,
    status="BLOCKED",
    reason="Отрицательное матожидание",
))

dispatcher = ExecutionDispatcher(
    real_execution_engine=MockRealExecution(),
    strategy_runtime_gate=blocked_gate,
)

dispatcher._persistent_kill_switch = MockKillSwitch()
dispatcher._futures_access_gate = MockFuturesGate()
dispatcher._futures_margin_guard = MockMarginGate()

intent = {
    "client_order_id": f"test-runtime-gate-block-{uuid.uuid4().hex}",
    "symbol": "SBER@MISX",
    "side": "BUY",
    "qty": 2,
    "price": 300,
    "strategy": "BAD_STRATEGY",
}

result = dispatcher.execute(intent=intent, market_state={"regime": "trend_high_vol"})

assert isinstance(result, dict)
assert result["status"] == "REJECTED"
assert result["reason"] == "strategy_runtime_control_blocked"


# Изменение размера до execution.
real_engine = MockRealExecution()
allowed_gate = MockGate(GateDecision(
    allowed=True,
    watch_only=False,
    original_qty=2.0,
    adjusted_qty=1.0,
    risk_multiplier=0.5,
    status="WATCH",
    reason="Снижение риска",
))

dispatcher = ExecutionDispatcher(
    real_execution_engine=real_engine,
    strategy_runtime_gate=allowed_gate,
)

dispatcher._persistent_kill_switch = MockKillSwitch()
dispatcher._futures_access_gate = MockFuturesGate()
dispatcher._futures_margin_guard = MockMarginGate()

intent = {
    "client_order_id": f"test-runtime-gate-size-{uuid.uuid4().hex}",
    "symbol": "SBER@MISX",
    "side": "BUY",
    "qty": 2,
    "price": 300,
    "strategy": "TEST_STRATEGY",
    "signal_id": "sig-runtime-gate",
}

result = dispatcher.execute(intent=intent, market_state={"regime": "trend_high_vol"})

assert result.status == "DRY_RUN_ACCEPTED"
assert real_engine.intent["qty"] == 1.0
assert real_engine.intent["runtime_control"]["risk_multiplier"] == 0.5

print("OK: ExecutionDispatcher применяет StrategyRuntimeGate до отправки заявки")
PY
