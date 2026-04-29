# src/finam_core/risk/kill_switch.py

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class KillSwitchDecision:
    allowed: bool
    reason: str
    daily_realized_pnl: float
    equity: float
    start_equity: float
    drawdown: float
    kill_switch_active: bool


class KillSwitchEngine:
    """
    Русский коммент: Risk v3.1 — дневной лимит убытка и kill switch.
    Не отправляет заявки напрямую, только разрешает/блокирует вход.
    """

    def __init__(self):
        self.daily_loss_limit = abs(float(os.getenv("DAILY_LOSS_LIMIT", "1000")))
        self.max_drawdown_abs = abs(float(os.getenv("MAX_DRAWDOWN_ABS", "2000")))
        self.kill_switch_active = False

    def reset(self) -> None:
        self.kill_switch_active = False

    def evaluate(self, daily_realized_pnl: float, equity: float, start_equity: float) -> KillSwitchDecision:
        daily_pnl = float(daily_realized_pnl or 0.0)
        eq = float(equity or 0.0)
        start_eq = float(start_equity or 0.0)
        drawdown = max(0.0, start_eq - eq) if start_eq > 0 else 0.0

        if self.kill_switch_active:
            return KillSwitchDecision(False, "kill_switch_active", daily_pnl, eq, start_eq, drawdown, True)

        if daily_pnl <= -self.daily_loss_limit:
            self.kill_switch_active = True
            return KillSwitchDecision(False, "daily_loss_limit_exceeded", daily_pnl, eq, start_eq, drawdown, True)

        if drawdown >= self.max_drawdown_abs:
            self.kill_switch_active = True
            return KillSwitchDecision(False, "max_drawdown_exceeded", daily_pnl, eq, start_eq, drawdown, True)

        return KillSwitchDecision(True, "ok", daily_pnl, eq, start_eq, drawdown, False)
