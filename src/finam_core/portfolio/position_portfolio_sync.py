from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuthoritativePosition:
    symbol: str
    qty: float
    avg_price: float = 0.0
    reason: str = "authoritative_sync"


class PositionPortfolioSyncLayer:
    """
    Русский комментарий:
    Слой authoritative-синхронизации позиций.

    Важно:
    - не проводит сделки;
    - не меняет cash;
    - не меняет realized_pnl;
    - только приводит локальную позицию к брокерскому факту.
    """

    def __init__(self, position_manager: Any, portfolio_manager: Any | None = None):
        self.position_manager = position_manager
        self.portfolio_manager = portfolio_manager

    def sync_position(self, position: AuthoritativePosition) -> dict[str, Any]:
        if not position.symbol:
            raise ValueError("symbol is required")

        event = self.position_manager.sync_authoritative_position(
            symbol=position.symbol,
            qty=float(position.qty),
            avg_price=float(position.avg_price),
            reason=position.reason,
        )

        if self.portfolio_manager is not None:
            refresh = getattr(self.portfolio_manager, "refresh_from_position_manager", None)
            if callable(refresh):
                refresh(self.position_manager)

        return {
            "event": "POSITION_PORTFOLIO_SYNC",
            "symbol": position.symbol,
            "qty": float(position.qty),
            "avg_price": float(position.avg_price),
            "reason": position.reason,
            "position_event": event,
        }

    def sync_many(self, positions: list[AuthoritativePosition]) -> list[dict[str, Any]]:
        return [self.sync_position(position) for position in positions]
