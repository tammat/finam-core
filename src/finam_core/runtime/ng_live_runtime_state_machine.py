from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgLiveRuntimeInput:
    symbol: str
    strategy: str
    timeframe: str

    previous_state: str
    active_edge: bool
    governance_allow: bool
    market_data_fresh: bool
    open_position_qty: float
    halted: bool = False


@dataclass(frozen=True)
class NgLiveRuntimeDecision:
    symbol: str
    strategy: str
    timeframe: str

    runtime_state: str
    allow_new_entries: bool
    allow_position_management: bool
    reason: str


class NgLiveRuntimeStateMachine:
    """
    Русский комментарий:
    State machine для NG M1 runtime.
    Не отправляет заявки. Только определяет runtime-состояние.
    """

    def decide(self, item: NgLiveRuntimeInput) -> NgLiveRuntimeDecision:
        prev = (item.previous_state or "DISABLED").upper()

        if item.halted:
            return self._decision(item, "HALTED", False, False, "runtime_halted")

        if not item.governance_allow:
            return self._decision(item, "DISABLED", False, False, "governance_block")

        if not item.market_data_fresh:
            if abs(item.open_position_qty) > 0:
                return self._decision(item, "EXIT_ONLY", False, True, "market_data_stale_position_management_only")
            return self._decision(item, "DISABLED", False, False, "market_data_stale")

        if not item.active_edge:
            if abs(item.open_position_qty) > 0:
                return self._decision(item, "EXIT_ONLY", False, True, "edge_lost_exit_only")
            if prev in {"ACTIVE", "WARMUP"}:
                return self._decision(item, "COOLDOWN", False, False, "edge_lost_cooldown")
            return self._decision(item, "DISABLED", False, False, "no_active_edge")

        if prev == "DISABLED":
            return self._decision(item, "WARMUP", False, False, "active_edge_detected_warmup")

        if prev == "WARMUP":
            return self._decision(item, "ACTIVE", True, True, "warmup_completed_active")

        if prev in {"ACTIVE", "COOLDOWN", "EXIT_ONLY"}:
            return self._decision(item, "ACTIVE", True, True, "active_edge_confirmed")

        return self._decision(item, "WARMUP", False, False, f"unknown_previous_state:{prev}")

    def _decision(
        self,
        item: NgLiveRuntimeInput,
        state: str,
        allow_new_entries: bool,
        allow_position_management: bool,
        reason: str,
    ) -> NgLiveRuntimeDecision:
        return NgLiveRuntimeDecision(
            symbol=item.symbol,
            strategy=item.strategy,
            timeframe=item.timeframe,
            runtime_state=state,
            allow_new_entries=allow_new_entries,
            allow_position_management=allow_position_management,
            reason=reason,
        )
