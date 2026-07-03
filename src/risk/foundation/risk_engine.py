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
