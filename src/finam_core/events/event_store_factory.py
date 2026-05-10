from __future__ import annotations

from typing import Any

from finam_core.events.event_store import EventStore


class EventStoreFactory:
    """Русский комментарий: единая фабрика EventStore с shared EventBus."""

    _event_bus: Any | None = None

    @classmethod
    def configure(cls, *, event_bus: Any | None = None) -> None:
        cls._event_bus = event_bus

    @classmethod
    def get_event_bus(cls) -> Any | None:
        return cls._event_bus

    @classmethod
    def create(cls, *, database_url: str | None = None) -> EventStore:
        return EventStore(
            database_url=database_url,
            event_bus=cls._event_bus,
        )
