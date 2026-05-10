from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FuturesMarginDecision:
    allowed: bool
    reason: str
    symbol: str
    qty: float
    required_margin: float
    used_margin_before: float
    used_margin_after: float
    equity: float
    margin_utilization_after: float


class FuturesMarginGuard:
    """Русский комментарий: проверяет загрузку ГО/маржи перед real futures execution."""

    DEFAULT_MARGIN_BY_PREFIX = {
        "BR": 25000.0,
        "NG": 5000.0,
        "Si": 15000.0,
        "SI": 15000.0,
        "RTS": 30000.0,
    }

    def __init__(self) -> None:
        self.max_utilization = float(os.getenv("FUTURES_MAX_MARGIN_UTILIZATION", "0.50"))

    def is_futures_symbol(self, symbol: str) -> bool:
        s = str(symbol or "").upper()
        return s.endswith("@RTSX") or s.endswith("@FORTS")

    def margin_per_contract(self, symbol: str) -> float:
        s = str(symbol or "").split("@")[0]

        env_key = f"FUTURES_MARGIN_{s.upper()}"
        if os.getenv(env_key):
            return float(os.getenv(env_key, "0"))

        for prefix, value in self.DEFAULT_MARGIN_BY_PREFIX.items():
            if s.upper().startswith(prefix.upper()):
                return float(value)

        return float(os.getenv("FUTURES_DEFAULT_MARGIN_PER_CONTRACT", "10000"))

    def check(
        self,
        *,
        symbol: str,
        qty: float,
        equity: float,
        used_margin_before: float,
    ) -> FuturesMarginDecision:
        q = abs(float(qty or 0.0))
        eq = float(equity or 0.0)
        used_before = float(used_margin_before or 0.0)

        if not self.is_futures_symbol(symbol):
            return FuturesMarginDecision(
                allowed=True,
                reason="not_futures_symbol",
                symbol=symbol,
                qty=q,
                required_margin=0.0,
                used_margin_before=used_before,
                used_margin_after=used_before,
                equity=eq,
                margin_utilization_after=0.0 if eq <= 0 else used_before / eq,
            )

        if eq <= 0:
            return FuturesMarginDecision(
                allowed=False,
                reason="equity_not_positive",
                symbol=symbol,
                qty=q,
                required_margin=0.0,
                used_margin_before=used_before,
                used_margin_after=used_before,
                equity=eq,
                margin_utilization_after=1.0,
            )

        required = self.margin_per_contract(symbol) * q
        used_after = used_before + required
        utilization_after = used_after / eq

        if utilization_after > self.max_utilization:
            return FuturesMarginDecision(
                allowed=False,
                reason="futures_margin_utilization_limit",
                symbol=symbol,
                qty=q,
                required_margin=required,
                used_margin_before=used_before,
                used_margin_after=used_after,
                equity=eq,
                margin_utilization_after=utilization_after,
            )

        return FuturesMarginDecision(
            allowed=True,
            reason="futures_margin_ok",
            symbol=symbol,
            qty=q,
            required_margin=required,
            used_margin_before=used_before,
            used_margin_after=used_after,
            equity=eq,
            margin_utilization_after=utilization_after,
        )
