from __future__ import annotations

import os
import time
from dataclasses import dataclass

from finam_core.projections.checkpoint_aware_projection_updater import (
    CheckpointAwareProjectionUpdater,
)


@dataclass(frozen=True)
class ProjectionWorkerTickResult:
    ok: bool
    checkpoint_name: str
    events_loaded: int
    previous_event_id: int
    new_event_id: int
    error: str | None = None


class ProjectionWorker:
    """Русский комментарий: restart-safe worker для checkpoint-aware projections."""

    def __init__(
        self,
        *,
        updater: CheckpointAwareProjectionUpdater | None = None,
        checkpoint_name: str = "projection_worker",
        interval_sec: float | None = None,
        limit: int | None = None,
    ) -> None:
        self.updater = updater or CheckpointAwareProjectionUpdater()
        self.checkpoint_name = checkpoint_name
        self.interval_sec = float(
            interval_sec if interval_sec is not None else os.getenv("PROJECTION_WORKER_INTERVAL_SEC", "5")
        )
        self.limit = int(
            limit if limit is not None else os.getenv("PROJECTION_WORKER_LIMIT", "10000")
        )

    def tick(self) -> ProjectionWorkerTickResult:
        """Русский комментарий: один безопасный цикл обновления projections."""
        try:
            result = self.updater.update_since_checkpoint(
                checkpoint_name=self.checkpoint_name,
                limit=self.limit,
            )

            print(
                "PROJECTION_WORKER_TICK_OK "
                f"checkpoint={result.checkpoint_name} "
                f"events_loaded={result.events_loaded} "
                f"previous_event_id={result.previous_event_id} "
                f"new_event_id={result.new_event_id} "
                f"orders={result.orders_count} "
                f"positions={result.positions_count}",
                flush=True,
            )

            return ProjectionWorkerTickResult(
                ok=True,
                checkpoint_name=result.checkpoint_name,
                events_loaded=result.events_loaded,
                previous_event_id=result.previous_event_id,
                new_event_id=result.new_event_id,
            )

        except Exception as exc:
            print(
                f"PROJECTION_WORKER_TICK_FAILED checkpoint={self.checkpoint_name} error={exc}",
                flush=True,
            )

            return ProjectionWorkerTickResult(
                ok=False,
                checkpoint_name=self.checkpoint_name,
                events_loaded=0,
                previous_event_id=0,
                new_event_id=0,
                error=str(exc),
            )

    def run_forever(self) -> None:
        """Русский комментарий: бесконечный worker-loop для systemd."""
        print(
            f"PROJECTION_WORKER_STARTED checkpoint={self.checkpoint_name} "
            f"interval_sec={self.interval_sec} limit={self.limit}",
            flush=True,
        )

        while True:
            self.tick()
            time.sleep(self.interval_sec)
