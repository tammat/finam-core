from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgEntryGuardDecision:
    allowed: bool
    reason: str


def evaluate_ng_directional_entry_guard(
    *, side: str, trend: str, normalized_slope: float,
    source_version: str, data_ready: bool, stale: bool,
    confirmed_bars: int, regime_bar_key: str | None,
    consumed_fingerprints: set[str], symbol: str,
    slope_epsilon: float = 0.02,
) -> NgEntryGuardDecision:
    """Fail closed when an NG entry is not confirmed by a fresh M5 regime."""
    side = str(side or "").upper()
    trend = str(trend or "").lower()
    if side not in {"BUY", "SELL"}:
        return NgEntryGuardDecision(False, "NG_DIRECTION_UNKNOWN")
    if (source_version != "CANDLE_REGIME_V3" or not data_ready or stale
            or int(confirmed_bars or 0) < 3 or not regime_bar_key):
        return NgEntryGuardDecision(False, "NG_DIRECTIONAL_REGIME_NOT_READY")
    epsilon = max(0.0, float(slope_epsilon))
    slope = float(normalized_slope or 0.0)
    if side == "BUY" and (trend in {"down", "trend_down"} or slope <= epsilon):
        return NgEntryGuardDecision(False, "NG_LONG_DIRECTION_NOT_CONFIRMED")
    if side == "SELL" and (trend in {"up", "trend_up"} or slope >= -epsilon):
        return NgEntryGuardDecision(False, "NG_SHORT_DIRECTION_NOT_CONFIRMED")
    fingerprint = f"{str(symbol).upper()}:{side}:{regime_bar_key}"
    if fingerprint in consumed_fingerprints:
        return NgEntryGuardDecision(False, "NG_DUPLICATE_REGIME_BAR_FINGERPRINT")
    return NgEntryGuardDecision(True, "NG_DIRECTION_CONFIRMED")


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
