from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.events.event_store import StoredEvent
from finam_core.projections.projection_engine import ProjectionEngine
from finam_core.projections.projection_store import ProjectionStore


@dataclass(frozen=True)
class ProjectionSubscriberResult:
    events_processed: int
    orders_count: int
    positions_count: int


class RealtimeProjectionSubscriber:
    """
    Русский комментарий:
    Incremental projection updater.
    Обновляет materialized projections сразу после события.
    """

    def __init__(
        self,
        *,
        engine: ProjectionEngine | None = None,
        store: ProjectionStore | None = None,
    ) -> None:
        self.engine = engine or ProjectionEngine()
        self.store = store or ProjectionStore()

        # Русский комментарий:
        # in-memory state между событиями.
        self.state = self.engine.empty_state()

    def process_event(self, event: StoredEvent) -> ProjectionSubscriberResult:
        """
        Русский комментарий:
        Применяем одно событие к текущему projection state.
        """

        self.engine.apply_event(self.state, event)

        self.store.save(self.state)

        return ProjectionSubscriberResult(
            events_processed=self.state.events_processed,
            orders_count=len(self.state.orders.orders),
            positions_count=len(self.state.positions.positions),
        )

    def process_events(
        self,
        events: list[StoredEvent],
    ) -> ProjectionSubscriberResult:
        """
        Русский комментарий:
        Batch incremental processing.
        """

        for event in events:
            self.engine.apply_event(self.state, event)

        self.store.save(self.state)

        return ProjectionSubscriberResult(
            events_processed=self.state.events_processed,
            orders_count=len(self.state.orders.orders),
            positions_count=len(self.state.positions.positions),
        )
