from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DiscoveredObject:
    object_id: str
    object_name: str
    domain: str
    category: str
    object_type: str
    schema_name: str | None = None
    warehouse_layer: str | None = None
    source_system: str = "POSTGRES"
    source_type: str = "DERIVED"
    rows_count: int | None = None
    last_update: str | None = None
    discovery_source: str = "PostgresDiscovery"
    discovery_version: str = "POSTGRES_DISCOVERY_PLUGIN_V1"
    payload: dict[str, Any] = field(default_factory=dict)
