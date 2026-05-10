from __future__ import annotations

from dataclasses import dataclass

from finam_core.events.event_store_reader import EventStoreReader
from finam_core.events.dead_letter_service import DeadLetterService
from finam_core.projections.projection_checkpoint_service import ProjectionCheckpointService
from finam_core.projections.projection_engine import ProjectionEngine
from finam_core.projections.projection_store import ProjectionStore


@dataclass(frozen=True)
class CheckpointAwareProjectionUpdateResult:
    checkpoint_name: str
    previous_event_id: int
    new_event_id: int
    events_loaded: int
    events_processed: int
    orders_count: int
    positions_count: int


class CheckpointAwareProjectionUpdater:
    """Русский комментарий: обновляет projections только по новым events после checkpoint."""

    def __init__(
        self,
        *,
        reader: EventStoreReader | None = None,
        engine: ProjectionEngine | None = None,
        store: ProjectionStore | None = None,
        checkpoints: ProjectionCheckpointService | None = None,
        dead_letters: DeadLetterService | None = None,
    ) -> None:
        self.reader = reader or EventStoreReader()
        self.engine = engine or ProjectionEngine()
        self.store = store or ProjectionStore()
        self.checkpoints = checkpoints or ProjectionCheckpointService()
        self.dead_letters = dead_letters or DeadLetterService()

        # Русский комментарий: checkpoint updater не должен падать на одном broken event.
        if isinstance(self.engine, ProjectionEngine):
            self.engine.dead_letters = self.dead_letters
            self.engine.worker_name = "checkpoint_aware_projection_updater"
            self.engine.strict = False

    def update_since_checkpoint(
        self,
        *,
        checkpoint_name: str = "projection_updater",
        limit: int = 10000,
    ) -> CheckpointAwareProjectionUpdateResult:
        checkpoint = self.checkpoints.get(name=checkpoint_name)

        events = self.reader.list_since_id(
            since_id=checkpoint.last_event_id,
            limit=limit,
        )

        state = self.engine.build(events)

        max_event_id = checkpoint.last_event_id

        if events:
            self.store.save(state)
            max_event_id = max(int(event.db_id or 0) for event in events)
            self.checkpoints.update(
                name=checkpoint_name,
                last_event_id=max_event_id,
            )

        return CheckpointAwareProjectionUpdateResult(
            checkpoint_name=checkpoint_name,
            previous_event_id=checkpoint.last_event_id,
            new_event_id=max_event_id,
            events_loaded=len(events),
            events_processed=state.events_processed,
            orders_count=len(state.orders.orders),
            positions_count=len(state.positions.positions),
        )
