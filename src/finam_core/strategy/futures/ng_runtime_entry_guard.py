from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgEntryGuardDecision:
    allowed: bool
    reason: str


def evaluate_ng_entry_guard(*, symbol: str, enabled_symbols: tuple[str, ...],
                            kill_switch_active: bool, seconds_since_last: float | None,
                            cooldown_seconds: float = 180.0) -> NgEntryGuardDecision:
    symbol = str(symbol or "").upper()
    enabled = tuple(str(item).upper() for item in enabled_symbols)
    if not symbol.startswith("NG"):
        return NgEntryGuardDecision(True, "NOT_NG")
    if kill_switch_active:
        return NgEntryGuardDecision(False, "KILL_SWITCH_ACTIVE_PRE_SIGNAL")
    if not enabled:
        return NgEntryGuardDecision(False, "NG_RUNTIME_UNIVERSE_DISABLED")
    if len(enabled) != 1:
        return NgEntryGuardDecision(False, "NG_CANONICAL_CONTRACT_AMBIGUOUS")
    if symbol != enabled[0]:
        return NgEntryGuardDecision(False, "NG_NOT_CANONICAL_CONTRACT")
    if seconds_since_last is not None and seconds_since_last < cooldown_seconds:
        return NgEntryGuardDecision(False, "NG_ENTRY_COOLDOWN")
    return NgEntryGuardDecision(True, "NG_ENTRY_ALLOWED")
