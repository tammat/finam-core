from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class BrSignalStabilityDecision:
    allowed: bool
    reason: str
    h1_bias: str
    last_side: str | None
    cooldown_active: bool


class BrSignalStabilityGuard:
    """Русский комментарий: защитный слой против flip-flop сигналов Brent."""

    def __init__(self, cooldown_minutes: int = 20):
        self.cooldown = timedelta(minutes=int(cooldown_minutes))
        self._last_signal_ts: dict[str, datetime] = {}
        self._last_side: dict[str, str] = {}

    def decide(
        self,
        *,
        symbol: str,
        side: str,
        signal_ts: datetime | None,
        h1_bias: str,
    ) -> BrSignalStabilityDecision:
        now = signal_ts or datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        symbol_key = str(symbol or "")
        side_norm = str(side or "").upper()
        h1 = str(h1_bias or "flat").lower()

        if h1 == "up" and side_norm == "SELL":
            return BrSignalStabilityDecision(False, "h1_bias_blocks_sell", h1, self._last_side.get(symbol_key), False)

        if h1 == "down" and side_norm == "BUY":
            return BrSignalStabilityDecision(False, "h1_bias_blocks_buy", h1, self._last_side.get(symbol_key), False)

        if h1 in {"flat", "unknown", "dead"}:
            return BrSignalStabilityDecision(False, "h1_bias_not_directional", h1, self._last_side.get(symbol_key), False)

        last_ts = self._last_signal_ts.get(symbol_key)
        last_side = self._last_side.get(symbol_key)

        if last_ts is not None and now - last_ts < self.cooldown:
            if last_side and last_side != side_norm:
                return BrSignalStabilityDecision(False, "cooldown_blocks_flip_flop", h1, last_side, True)

        self._last_signal_ts[symbol_key] = now
        self._last_side[symbol_key] = side_norm

        return BrSignalStabilityDecision(True, "br_signal_stability_ok", h1, last_side, False)
