from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FuturesAccessDecision:
    allowed: bool
    reason: str
    execution_mode: str
    symbol: str


class FuturesAccessGate:
    """Русский комментарий: защита real-торговли фьючерсами до разрешённой даты и режима."""

    FUTURES_MARKETS = {"RTSX", "FORTS"}

    def __init__(self, today: date | None = None) -> None:
        self.today = today or date.today()
        self.allowed_from = date.fromisoformat(
            os.getenv("FUTURES_REAL_ALLOWED_FROM", "2026-07-01")
        )

    def is_futures_symbol(self, symbol: str) -> bool:
        s = str(symbol or "").upper()
        return any(s.endswith(f"@{market}") for market in self.FUTURES_MARKETS)

    def check(self, *, symbol: str, execution_mode: str) -> FuturesAccessDecision:
        mode = str(execution_mode or "paper").strip().lower()

        if not self.is_futures_symbol(symbol):
            return FuturesAccessDecision(
                allowed=True,
                reason="not_futures_symbol",
                execution_mode=mode,
                symbol=symbol,
            )

        if mode != "real":
            return FuturesAccessDecision(
                allowed=True,
                reason="futures_allowed_in_non_real_mode",
                execution_mode=mode,
                symbol=symbol,
            )

        if self.today < self.allowed_from:
            return FuturesAccessDecision(
                allowed=False,
                reason=f"futures_real_trading_blocked_until_{self.allowed_from.isoformat()}",
                execution_mode=mode,
                symbol=symbol,
            )

        if os.getenv("ENABLE_REAL_FUTURES_TRADING", "0") != "1":
            return FuturesAccessDecision(
                allowed=False,
                reason="ENABLE_REAL_FUTURES_TRADING_not_enabled",
                execution_mode=mode,
                symbol=symbol,
            )

        return FuturesAccessDecision(
            allowed=True,
            reason="futures_real_trading_allowed",
            execution_mode=mode,
            symbol=symbol,
        )
