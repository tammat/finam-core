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


class PortfolioGuard:
    """Русский комментарий: портфельный защитный слой перед live-paper."""

    def max_open_abs_position(self) -> float:
        raw = os.getenv("PORTFOLIO_MAX_OPEN_ABS_POSITION", "0").strip()
        return float(raw or 0.0)

    def max_paper_orders_per_run(self) -> int:
        raw = os.getenv("PORTFOLIO_MAX_PAPER_ORDERS_PER_RUN", "0").strip()
        return int(raw or 0)

    def kill_switch_enabled(self) -> bool:
        return os.getenv("PORTFOLIO_KILL_SWITCH", "0").strip() == "1"

    def is_allowed(
        self,
        *,
        total_open_abs_position: float,
        paper_orders_count: int,
    ) -> tuple[bool, str]:
        if self.kill_switch_enabled():
            return False, "PORTFOLIO_KILL_SWITCH_ENABLED"

        max_orders = self.max_paper_orders_per_run()
        if max_orders > 0 and paper_orders_count >= max_orders:
            return False, f"PORTFOLIO_MAX_PAPER_ORDERS_PER_RUN current={paper_orders_count} limit={max_orders}"

        max_open_abs = self.max_open_abs_position()
        if max_open_abs > 0 and total_open_abs_position >= max_open_abs:
            return False, f"PORTFOLIO_MAX_OPEN_ABS_POSITION current={total_open_abs_position} limit={max_open_abs}"

        return True, f"PORTFOLIO_OK open_abs={total_open_abs_position} orders={paper_orders_count}"
