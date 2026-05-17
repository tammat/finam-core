from datetime import datetime
from typing import Iterable, Protocol

from finam_core.runtime.runtime_state import RuntimeWorkerState


class RuntimeTelemetryDb(Protocol):
    def execute(self, sql: str, params: tuple) -> None:
        ...


class RuntimeTelemetry:
    def __init__(self, db: RuntimeTelemetryDb):
        self.db = db

    def write_worker_states(self, states: Iterable[RuntimeWorkerState]) -> None:
        now = datetime.utcnow()

        for state in states:
            self.db.execute(
                "INSERT INTO runtime_worker_state "
                "(symbol, enabled, status, started_at, stopped_at, "
                "last_heartbeat_at, last_error, updated_at) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) "
                "ON CONFLICT (symbol) DO UPDATE SET "
                "enabled = EXCLUDED.enabled, "
                "status = EXCLUDED.status, "
                "started_at = EXCLUDED.started_at, "
                "stopped_at = EXCLUDED.stopped_at, "
                "last_heartbeat_at = EXCLUDED.last_heartbeat_at, "
                "last_error = EXCLUDED.last_error, "
                "updated_at = EXCLUDED.updated_at",
                (
                    state.symbol,
                    state.enabled,
                    state.status,
                    state.started_at,
                    state.stopped_at,
                    state.last_heartbeat_at,
                    state.last_error,
                    now,
                ),
            )
