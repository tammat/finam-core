from __future__ import annotations

from typing import Any

from finam_core.events.event_store_factory import EventStoreFactory


def append_event_safe(
    *,
    event_type: str,
    aggregate_type: str = "system",
    aggregate_id: str | None = None,
    source: str = "system",
    payload: dict[str, Any] | None = None,
) -> None:
    """Русский комментарий: безопасная запись audit event; не ломает основной поток."""
    try:
        EventStoreFactory.create().append(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            source=source,
            payload=payload or {},
        )
    except Exception as exc:
        print(f"EVENT_STORE_APPEND_FAILED event_type={event_type} error={exc}", flush=True)
