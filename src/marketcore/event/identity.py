from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventIdentitySpec:
    event_id_column: str = "event_id"
    event_uuid_column: str = "event_uuid"
    event_sequence_column: str = "event_sequence"
    event_version_column: str = "event_version"


def event_identity_columns_sql() -> str:
    return """
    event_id bigserial PRIMARY KEY,
    event_uuid uuid NOT NULL DEFAULT gen_random_uuid(),
    event_sequence bigint NOT NULL,
    event_version text NOT NULL DEFAULT 'v1',
    UNIQUE(event_uuid)
"""


def event_identity_required_columns() -> tuple[str, ...]:
    return (
        "event_id",
        "event_uuid",
        "event_sequence",
        "event_version",
    )
