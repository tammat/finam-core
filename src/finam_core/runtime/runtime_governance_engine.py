from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeGovernanceInput:
    symbol: str
    strategy: str
    timeframe: str

    runtime_mode: str
    runtime_enabled: bool
    runtime_reason: str

    event_status: str = "NORMAL"
    event_allow_runtime: bool = True
    event_risk_multiplier: float = 1.0
    event_reason: str = "нет_значимых_событий"

    session_bucket: str = "UNKNOWN"
    session_allow_runtime: bool = True
    session_reason: str = "session_разрешена"

    ng_m1_policy_required: bool = False
    ng_m1_policy_allow_runtime: bool = True
    ng_m1_policy_reason: str = "ng_m1_policy_not_required"


@dataclass(frozen=True)
class RuntimeGovernanceDecision:
    symbol: str
    strategy: str
    timeframe: str

    decision: str
    allow_runtime: bool
    risk_multiplier: float
    reason: str


class RuntimeGovernanceEngine:
    """
    Русский комментарий:
    Единый runtime governance engine.
    Он не создаёт торговые сигналы и не отправляет заявки.
    Он только разрешает, блокирует или снижает риск runtime-исполнения.
    """

    def decide(self, item: RuntimeGovernanceInput) -> RuntimeGovernanceDecision:
        if not item.runtime_enabled:
            return RuntimeGovernanceDecision(
                symbol=item.symbol,
                strategy=item.strategy,
                timeframe=item.timeframe,
                decision="BLOCK_RUNTIME_SELECTION",
                allow_runtime=False,
                risk_multiplier=0.0,
                reason=item.runtime_reason,
            )

        if not item.event_allow_runtime:
            return RuntimeGovernanceDecision(
                symbol=item.symbol,
                strategy=item.strategy,
                timeframe=item.timeframe,
                decision="BLOCK_EVENT_RISK",
                allow_runtime=False,
                risk_multiplier=0.0,
                reason=item.event_reason,
            )

        if not item.session_allow_runtime:
            return RuntimeGovernanceDecision(
                symbol=item.symbol,
                strategy=item.strategy,
                timeframe=item.timeframe,
                decision="BLOCK_SESSION_RISK",
                allow_runtime=False,
                risk_multiplier=0.0,
                reason=item.session_reason,
            )

        if item.ng_m1_policy_required and not item.ng_m1_policy_allow_runtime:
            return RuntimeGovernanceDecision(
                symbol=item.symbol,
                strategy=item.strategy,
                timeframe=item.timeframe,
                decision="BLOCK_NG_M1_REGIME_POLICY",
                allow_runtime=False,
                risk_multiplier=0.0,
                reason=item.ng_m1_policy_reason,
            )

        risk_multiplier = min(
            1.0,
            max(0.0, float(item.event_risk_multiplier or 1.0)),
        )

        if risk_multiplier < 1.0:
            return RuntimeGovernanceDecision(
                symbol=item.symbol,
                strategy=item.strategy,
                timeframe=item.timeframe,
                decision="ALLOW_REDUCED_RISK",
                allow_runtime=True,
                risk_multiplier=risk_multiplier,
                reason=f"runtime_разрешен_со_сниженным_риском multiplier={risk_multiplier}",
            )

        return RuntimeGovernanceDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            decision="ALLOW_RUNTIME",
            allow_runtime=True,
            risk_multiplier=1.0,
            reason="runtime_разрешен",
        )
