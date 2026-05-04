# -*- coding: utf-8 -*-
from __future__ import annotations

import os


def env_symbol_key(symbol: str) -> str:
    return (
        symbol.upper()
        .replace("@", "_")
        .replace("-", "_")
        .replace(".", "_")
        .replace("/", "_")
    )


class RegimePolicy:
    """Русский комментарий: разрешённые режимы по инструментам через env."""

    def allowed_regimes_for(self, symbol: str) -> set[str]:
        key = f"ALLOWED_REGIMES_{env_symbol_key(symbol)}"
        raw = os.getenv(key, "").strip()
        if not raw:
            return set()
        return {x.strip() for x in raw.split(",") if x.strip()}

    def is_allowed(self, symbol: str, regime: str) -> tuple[bool, str]:
        allowed = self.allowed_regimes_for(symbol)

        if "__DISABLED__" in allowed:
            return False, "REGIME_POLICY_DISABLED_SYMBOL"

        if not allowed:
            return True, "REGIME_POLICY_NOT_CONFIGURED"

        if regime in allowed:
            return True, f"REGIME_ALLOWED:{regime}"

        return False, f"REGIME_BLOCKED:{regime}"


class SymbolDrawdownGuard:
    """Русский комментарий: лимит просадки по инструменту через env перед live-paper."""

    def max_drawdown_for(self, symbol: str) -> float:
        key = f"MAX_SYMBOL_DRAWDOWN_{env_symbol_key(symbol)}"
        raw = os.getenv(key, os.getenv("MAX_SYMBOL_DRAWDOWN_DEFAULT", "0")).strip()
        return float(raw or 0.0)

    def is_allowed(self, symbol: str, current_drawdown: float) -> tuple[bool, str]:
        limit = self.max_drawdown_for(symbol)
        if limit <= 0:
            return True, "SYMBOL_DRAWDOWN_GUARD_NOT_CONFIGURED"

        if current_drawdown <= -abs(limit):
            return False, f"SYMBOL_DRAWDOWN_LIMIT current_drawdown={current_drawdown} limit={limit}"

        return True, f"SYMBOL_DRAWDOWN_OK current_drawdown={current_drawdown} limit={limit}"


class SymbolLossStreakGuard:
    """Русский комментарий: пауза по инструменту после серии убыточных закрытых сделок."""

    def loss_limit_for(self, symbol: str) -> int:
        key = f"LOSS_STREAK_LIMIT_{env_symbol_key(symbol)}"
        raw = os.getenv(key, os.getenv("LOSS_STREAK_LIMIT_DEFAULT", "0")).strip()
        return int(raw or 0)

    def pause_bars_for(self, symbol: str) -> int:
        key = f"LOSS_STREAK_PAUSE_BARS_{env_symbol_key(symbol)}"
        raw = os.getenv(key, os.getenv("LOSS_STREAK_PAUSE_BARS_DEFAULT", "0")).strip()
        return int(raw or 0)

    def is_allowed(self, symbol: str, loss_streak: int, pause_left: int) -> tuple[bool, str]:
        limit = self.loss_limit_for(symbol)
        pause_bars = self.pause_bars_for(symbol)

        if limit <= 0 or pause_bars <= 0:
            return True, "LOSS_STREAK_GUARD_NOT_CONFIGURED"

        if pause_left > 0:
            return False, f"LOSS_STREAK_PAUSE_ACTIVE loss_streak={loss_streak} pause_left={pause_left}"

        return True, f"LOSS_STREAK_OK loss_streak={loss_streak} limit={limit} pause_bars={pause_bars}"
