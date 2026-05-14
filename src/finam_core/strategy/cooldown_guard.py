from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class CooldownDecision:
    allowed: bool
    reason: str
    cooldown_sec: float
    elapsed_sec: float


class CooldownGuard:
    """Русский комментарий: единый guard для блокировки повторных сигналов по cooldown."""

    def __init__(self) -> None:
        self._last_signal_ts: dict[str, float] = {}

    def calculate_dynamic_cooldown(
        self,
        *,
        base_cooldown: float,
        atr_pct: float | None,
    ) -> float:
        """Русский комментарий: рассчитывает динамический cooldown по волатильности."""
        try:
            value = float(atr_pct or 0.0)

            # Русский комментарий: высокая волатильность → ускоряемся.
            if value > 0.015:
                return float(base_cooldown) * 0.5

            # Русский комментарий: низкая волатильность → замедляемся.
            if value < 0.005:
                return float(base_cooldown) * 1.5

            return float(base_cooldown)

        except Exception:
            return float(base_cooldown)

    def check_elapsed(
        self,
        *,
        last_ts: float,
        now_ts: float | None = None,
        cooldown_sec: float,
    ) -> CooldownDecision:
        """Русский комментарий: проверяет cooldown по внешнему last_ts pipeline."""
        now = float(now_ts if now_ts is not None else time.time())
        last = float(last_ts or 0.0)
        elapsed = now - last

        if cooldown_sec > 0 and elapsed < cooldown_sec:
            return CooldownDecision(False, "cooldown_active", float(cooldown_sec), float(elapsed))

        return CooldownDecision(True, "cooldown_ok", float(cooldown_sec), float(elapsed))

    def check(
        self,
        *,
        key: str,
        cooldown_sec: float,
    ) -> CooldownDecision:
        """Русский комментарий: standalone cooldown с внутренним состоянием."""
        now = time.time()
        last = float(self._last_signal_ts.get(key, 0.0) or 0.0)
        decision = self.check_elapsed(
            last_ts=last,
            now_ts=now,
            cooldown_sec=cooldown_sec,
        )

        if decision.allowed:
            self._last_signal_ts[key] = now

        return decision
