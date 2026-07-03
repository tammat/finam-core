#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_RISK_ENGINE_FOUNDATION_V1 ==="

mkdir -p src/risk/foundation scripts

cat > src/risk/foundation/risk_module.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskModuleResult:
    module: str
    status: str
    score: int
    reason: str
    details: dict[str, str]


class RiskModule:
    name = "BASE"

    def evaluate(self, ctx) -> RiskModuleResult:
        raise NotImplementedError
PY

cat > src/risk/foundation/risk_engine.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass

from risk.foundation.risk_context import RiskContext
from risk.foundation.risk_module import RiskModule, RiskModuleResult
from risk.foundation.risk_verdict import RiskVerdict


@dataclass(frozen=True)
class RiskEngineResult:
    verdict: RiskVerdict
    module_results: tuple[RiskModuleResult, ...]


class KillSwitchModule(RiskModule):
    name = "KILL_SWITCH"

    def evaluate(self, ctx: RiskContext) -> RiskModuleResult:
        if ctx.kill_switch_enabled:
            return RiskModuleResult(self.name, "BLOCK", 1000, "kill_switch_enabled", {})
        return RiskModuleResult(self.name, "PASS", 0, "kill_switch_off", {})


class DailyLossModule(RiskModule):
    name = "DAILY_LOSS"

    def evaluate(self, ctx: RiskContext) -> RiskModuleResult:
        if ctx.portfolio.daily_drawdown <= -ctx.daily_loss_limit:
            return RiskModuleResult(self.name, "BLOCK", 900, "daily_loss_limit_reached", {})
        return RiskModuleResult(self.name, "PASS", 0, "daily_loss_ok", {})


class ExposureModule(RiskModule):
    name = "EXPOSURE"

    def evaluate(self, ctx: RiskContext) -> RiskModuleResult:
        projected = ctx.portfolio.gross_exposure + ctx.requested_quantity
        if projected > ctx.exposure_limit:
            return RiskModuleResult(self.name, "BLOCK", 800, "exposure_limit_exceeded", {
                "projected": str(projected),
                "limit": str(ctx.exposure_limit),
            })
        return RiskModuleResult(self.name, "PASS", 0, "exposure_ok", {
            "projected": str(projected),
            "limit": str(ctx.exposure_limit),
        })


class QuantityModule(RiskModule):
    name = "QUANTITY"

    def evaluate(self, ctx: RiskContext) -> RiskModuleResult:
        if ctx.requested_quantity <= 0:
            return RiskModuleResult(self.name, "BLOCK", 700, "bad_quantity", {})
        return RiskModuleResult(self.name, "PASS", 0, "quantity_ok", {})


class SignalStrengthModule(RiskModule):
    name = "SIGNAL_STRENGTH"

    def evaluate(self, ctx: RiskContext) -> RiskModuleResult:
        if ctx.signal.signal_strength < 0.5:
            return RiskModuleResult(self.name, "WARN", 300, "weak_signal", {
                "signal_strength": str(ctx.signal.signal_strength),
            })
        return RiskModuleResult(self.name, "PASS", 0, "signal_strength_ok", {
            "signal_strength": str(ctx.signal.signal_strength),
        })


class RiskEngine:
    def __init__(self, modules: tuple[RiskModule, ...] | None = None) -> None:
        self.modules = modules or (
            KillSwitchModule(),
            DailyLossModule(),
            ExposureModule(),
            QuantityModule(),
            SignalStrengthModule(),
        )

    def evaluate(self, ctx: RiskContext) -> RiskEngineResult:
        results = tuple(module.evaluate(ctx) for module in self.modules)

        if any(r.status == "BLOCK" for r in results):
            status = "BLOCK"
        elif any(r.status == "WARN" for r in results):
            status = "WARN"
        else:
            status = "PASS"

        score = sum(r.score for r in results)
        reasons = tuple(r.reason for r in results if r.status != "PASS")

        if not reasons:
            reasons = ("risk_pass",)

        return RiskEngineResult(
            verdict=RiskVerdict(status=status, risk_score=score, reasons=reasons),
            module_results=results,
        )
PY

cat > scripts/test_risk_engine_foundation_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_RISK_ENGINE_FOUNDATION_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/risk/foundation/risk_module.py \
  src/risk/foundation/risk_engine.py \
  src/risk/foundation/risk_context.py \
  src/risk/foundation/risk_verdict.py \
  src/portfolio/portfolio_state.py \
  src/strategy/signal.py

PYTHONPATH=src python - <<'PY'
from decimal import Decimal

from portfolio.portfolio_state import PortfolioState
from risk.foundation.risk_context import RiskContext
from risk.foundation.risk_engine import RiskEngine
from strategy.signal import StrategySignal

signal = StrategySignal(
    signal_id="s1",
    symbol="LKOH@MISX",
    timeframe="M5",
    strategy="TEST_EDGE",
    side="BUY",
    signal_strength=Decimal("0.8"),
)

portfolio = PortfolioState(
    equity=Decimal("100000"),
    free_cash=Decimal("90000"),
    gross_exposure=Decimal("10000"),
    symbol_exposure=Decimal("0"),
    open_positions=1,
    daily_pnl=Decimal("0"),
    daily_drawdown=Decimal("0"),
)

ctx = RiskContext(
    signal=signal,
    portfolio=portfolio,
    asset_class="EQUITY",
    requested_quantity=Decimal("1"),
    max_risk_per_trade=Decimal("1000"),
    daily_loss_limit=Decimal("3000"),
    exposure_limit=Decimal("50000"),
    kill_switch_enabled=False,
)

engine = RiskEngine()
result = engine.evaluate(ctx)

assert result.verdict.status == "PASS"
assert result.verdict.risk_score == 0
assert len(result.module_results) == 5

blocked = RiskContext(
    signal=signal,
    portfolio=portfolio,
    asset_class="EQUITY",
    requested_quantity=Decimal("1"),
    max_risk_per_trade=Decimal("1000"),
    daily_loss_limit=Decimal("3000"),
    exposure_limit=Decimal("50000"),
    kill_switch_enabled=True,
)

blocked_result = engine.evaluate(blocked)
assert blocked_result.verdict.status == "BLOCK"
assert "kill_switch_enabled" in blocked_result.verdict.reasons

print("risk_engine_foundation_contract=OK")
print("modules=5")
print("pass_case=OK")
print("block_case=OK")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=RISK_ENGINE_FOUNDATION_V1_READY"
echo "VERDICT=TEST_RISK_ENGINE_FOUNDATION_V1_OK"
SH_TEST

chmod +x scripts/test_risk_engine_foundation_v1.sh
scripts/test_risk_engine_foundation_v1.sh

echo "VERDICT=BUILD_RISK_ENGINE_FOUNDATION_V1_OK"
