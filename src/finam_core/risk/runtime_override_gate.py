from __future__ import annotations

from dataclasses import dataclass

from finam_core.runtime.regime_runtime_override_repository import (
    RuntimeRegimeOverrideState,
)


@dataclass(frozen=True)
class RuntimeOverrideGateDecision:
    allowed: bool
    adjusted_quantity: float
    risk_multiplier: float
    stop_take_profile: str
    reason: str


def apply_runtime_override_gate(
    *,
    requested_quantity: float,
    execution_mode: str,
    override: RuntimeRegimeOverrideState | None,
) -> RuntimeOverrideGateDecision:
    """
    Русский комментарий:
    Применяет runtime_regime_overrides перед созданием заявки.
    Не отправляет заявку и не меняет RiskStack contract.
    """
    qty = max(0.0, float(requested_quantity))

    if override is None:
        return RuntimeOverrideGateDecision(
            allowed=True,
            adjusted_quantity=qty,
            risk_multiplier=1.0,
            stop_take_profile="default",
            reason="runtime_override_absent",
        )

    action = override.runtime_action.upper()
    allowed_mode = override.allowed_execution_mode.lower()
    current_mode = execution_mode.lower()

    if action == "BLOCK" or allowed_mode == "blocked":
        return RuntimeOverrideGateDecision(
            allowed=False,
            adjusted_quantity=0.0,
            risk_multiplier=0.0,
            stop_take_profile=override.stop_take_profile or "no_entry",
            reason=f"runtime_override_block:{override.reason}",
        )

    if allowed_mode and allowed_mode not in {"any", current_mode}:
        return RuntimeOverrideGateDecision(
            allowed=False,
            adjusted_quantity=0.0,
            risk_multiplier=0.0,
            stop_take_profile=override.stop_take_profile,
            reason=f"runtime_override_mode_block:{allowed_mode}!={current_mode}",
        )

    adjusted_qty = qty * max(0.0, min(1.0, override.max_position_size))
    risk_multiplier = max(0.0, min(1.0, override.risk_multiplier))

    if adjusted_qty <= 0 or risk_multiplier <= 0:
        return RuntimeOverrideGateDecision(
            allowed=False,
            adjusted_quantity=0.0,
            risk_multiplier=risk_multiplier,
            stop_take_profile=override.stop_take_profile,
            reason=f"runtime_override_zero_risk:{override.reason}",
        )

    return RuntimeOverrideGateDecision(
        allowed=True,
        adjusted_quantity=adjusted_qty,
        risk_multiplier=risk_multiplier,
        stop_take_profile=override.stop_take_profile or "default",
        reason=f"runtime_override_applied:{override.reason}",
    )
