from __future__ import annotations

from finam_core.execution.position_registry import (
    ManagedPosition,
    PositionRegistry,
)
from finam_core.storage.managed_position_repository import (
    ManagedPositionRepository,
)


class ManagedPositionService:
    """
    Coordinates:
    - runtime registry
    - persistent repository
    """

    def __init__(
        self,
        registry: PositionRegistry | None = None,
        repository: ManagedPositionRepository | None = None,
    ):
        self.registry = registry or PositionRegistry()
        self.repository = repository or ManagedPositionRepository()

        self.repository.ensure_schema()

    def register(self, pos: ManagedPosition) -> ManagedPosition:
        saved = self.registry.register_position(pos)
        self.repository.save(saved)
        return saved

    def get(self, symbol: str) -> ManagedPosition | None:
        pos = self.registry.get(symbol)

        if pos is not None:
            return pos

        db_pos = self.repository.get(symbol)

        if db_pos is not None:
            self.registry.register_position(db_pos)

        return db_pos

    def mark_tp1_filled(self, symbol: str) -> ManagedPosition | None:
        pos = self.registry.mark_tp1_filled(symbol)

        if pos is not None:
            self.repository.save(pos)

        return pos

    def mark_tp2_filled(self, symbol: str) -> ManagedPosition | None:
        pos = self.registry.mark_tp2_filled(symbol)

        if pos is not None:
            self.repository.save(pos)

        return pos

    def mark_breakeven_done(
        self,
        symbol: str,
        stop_order_id: str | None = None,
    ) -> ManagedPosition | None:
        pos = self.registry.mark_breakeven_done(
            symbol,
            stop_order_id=stop_order_id,
        )

        if pos is not None:
            self.repository.save(pos)

        return pos

    def update_stop(
        self,
        symbol: str,
        stop_order_id: str | None,
    ) -> ManagedPosition | None:
        pos = self.registry.update_stop(
            symbol,
            stop_order_id,
        )

        if pos is not None:
            self.repository.save(pos)

        return pos

    def remove(self, symbol: str) -> None:
        self.registry.remove(symbol)
        self.repository.delete(symbol)

    def restore_from_repository(self) -> int:
        positions = self.repository.list_all()

        for pos in positions:
            self.registry.register_position(pos)

        return len(positions)
