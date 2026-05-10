from __future__ import annotations

from dataclasses import dataclass

from finam_core.events.event_store_reader import EventStoreReader
from finam_core.projections.projection_engine import ProjectionEngine
from finam_core.projections.projection_store import ProjectionStore


@dataclass(frozen=True)
class ProjectionUpdateResult:
    events_loaded: int
    events_processed: int
    orders_count: int
    positions_count: int


class ProjectionUpdater:
    """Русский комментарий: обновляет materialized projections из EventStore."""

    def __init__(
        self,
        *,
        reader: EventStoreReader | None = None,
        engine: ProjectionEngine | None = None,
        store: ProjectionStore | None = None,
    ) -> None:
        self.reader = reader or EventStoreReader()
        self.engine = engine or ProjectionEngine()
        self.store = store or ProjectionStore()

    def update_all(self, *, batch_size: int = 10000) -> ProjectionUpdateResult:
        """Русский комментарий: полный rebuild projections из EventStore."""
        events = list(self.reader.iter_all(batch_size=batch_size))
        state = self.engine.build(events)
        self.store.save(state)

        return ProjectionUpdateResult(
            events_loaded=len(events),
            events_processed=state.events_processed,
            orders_count=len(state.orders.orders),
            positions_count=len(state.positions.positions),
        )
