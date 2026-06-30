from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventLineageSpec:
    source_system_column: str = "source_system_id"
    source_key_column: str = "source_key"
    normalization_run_column: str = "normalization_run_id"
    algorithm_version_column: str = "algorithm_version"
    parent_event_uuid_column: str = "parent_event_uuid"


def event_lineage_columns_sql() -> str:
    return """
    source_system_id bigint NOT NULL,
    source_key text NOT NULL,
    normalization_run_id bigint,
    algorithm_version text NOT NULL DEFAULT 'v1',
    parent_event_uuid uuid
"""


def event_lineage_required_columns() -> tuple[str, ...]:
    return (
        "source_system_id",
        "source_key",
        "algorithm_version",
    )
