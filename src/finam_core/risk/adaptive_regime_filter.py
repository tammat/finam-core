from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdaptiveRegimeDecision:
    allowed: bool
    action: str
    multiplier: float
    reason: str


class AdaptiveRegimeFilter:
    """Русский комментарий: фильтрует входы по исторической эффективности режима рынка."""

    def __init__(
        self,
        min_closed_trades: int = 5,
        block_net_pnl_below: float = -1.0,
        reduce_net_pnl_below: float = 0.0,
    ) -> None:
        self.min_closed_trades = int(min_closed_trades)
        self.block_net_pnl_below = float(block_net_pnl_below)
        self.reduce_net_pnl_below = float(reduce_net_pnl_below)

    def evaluate(
        self,
        regime: str,
        closed_trades: int,
        net_pnl: float,
        winrate: float,
    ) -> AdaptiveRegimeDecision:
        regime = str(regime or "❔ Нет данных")
        closed_trades = int(closed_trades or 0)
        net_pnl = float(net_pnl or 0.0)
        winrate = float(winrate or 0.0)

        if closed_trades < self.min_closed_trades:
            return AdaptiveRegimeDecision(
                allowed=True,
                action="ALLOW_LEARNING",
                multiplier=1.0,
                reason=(
                    f"режим={regime};сделок={closed_trades};"
                    f"недостаточно_статистики={self.min_closed_trades}"
                ),
            )

        if net_pnl <= self.block_net_pnl_below:
            return AdaptiveRegimeDecision(
                allowed=False,
                action="BLOCK",
                multiplier=0.0,
                reason=(
                    f"режим={regime};сделок={closed_trades};"
                    f"net_pnl={net_pnl};winrate={winrate};"
                    f"режим_убыточен"
                ),
            )

        if net_pnl < self.reduce_net_pnl_below:
            return AdaptiveRegimeDecision(
                allowed=True,
                action="REDUCE",
                multiplier=0.5,
                reason=(
                    f"режим={regime};сделок={closed_trades};"
                    f"net_pnl={net_pnl};winrate={winrate};"
                    f"режим_под_ограничением"
                ),
            )

        return AdaptiveRegimeDecision(
            allowed=True,
            action="ALLOW",
            multiplier=1.0,
            reason=(
                f"режим={regime};сделок={closed_trades};"
                f"net_pnl={net_pnl};winrate={winrate};"
                f"режим_допущен"
            ),
        )
