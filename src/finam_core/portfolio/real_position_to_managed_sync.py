from __future__ import annotations

from finam_core.execution.position_registry import ManagedPosition
from finam_core.execution.managed_position_service import ManagedPositionService
from finam_core.portfolio.latest_real_positions_provider import LatestRealPositionsProvider


class RealPositionToManagedSync:
    """
    Syncs latest broker positions into ManagedPositionService.

    Safe:
    - does not create orders
    - does not modify broker
    - preserves existing stop/tp ids if position already exists
    """

    def __init__(
        self,
        provider: LatestRealPositionsProvider | None = None,
        managed: ManagedPositionService | None = None,
    ):
        self.provider = provider or LatestRealPositionsProvider()
        self.managed = managed or ManagedPositionService()

    def sync(self) -> int:
        count = 0

        for p in self.provider.get_positions():
            existing = self.managed.get(p.symbol)

            side = "LONG" if p.qty > 0 else "SHORT"

            if existing is None:
                self.managed.register(
                    ManagedPosition(
                        symbol=p.symbol,
                        side=side,
                        qty=abs(float(p.qty)),
                        entry_price=float(p.avg_price or 0.0),
                    )
                )
            else:
                self.managed.register(
                    ManagedPosition(
                        symbol=p.symbol,
                        side=side,
                        qty=abs(float(p.qty)),
                        entry_price=float(p.avg_price or existing.entry_price),
                        stop_order_id=existing.stop_order_id,
                        tp1_order_id=existing.tp1_order_id,
                        tp2_order_id=existing.tp2_order_id,
                        breakeven_done=existing.breakeven_done,
                        tp1_done=existing.tp1_done,
                        tp2_done=existing.tp2_done,
                    )
                )

            count += 1

        return count
