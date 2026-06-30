from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EventValidationSpec:
    table: str
    event_type: str
    required_columns: tuple[str, ...]
    quality_column: str = "quality_status"
    event_time_column: str = "event_time"
    source_time_column: str = "source_time"
    received_at_column: str = "received_at"
    normalized_at_column: str = "normalized_at"


def required_fields_sql(spec: EventValidationSpec) -> str:
    conditions = [f"{column} IS NOT NULL" for column in spec.required_columns]
    return f"""
SELECT count(*)::bigint AS required_fields_valid
FROM {spec.table}
WHERE {' AND '.join(conditions)}
"""


def invalid_values_sql(table: str, column: str, allowed_values: Iterable[str]) -> str:
    values = ",".join("'" + v.replace("'", "''") + "'" for v in allowed_values)
    return f"""
SELECT count(*)::bigint AS invalid_values
FROM {table}
WHERE {column} IS NULL OR {column}::text NOT IN ({values})
"""


def time_order_violations_sql(spec: EventValidationSpec) -> str:
    return f"""
SELECT count(*)::bigint AS time_order_violations
FROM {spec.table}
WHERE NOT (
    {spec.event_time_column} <= {spec.source_time_column}
    AND {spec.source_time_column} <= {spec.received_at_column}
    AND {spec.received_at_column} <= {spec.normalized_at_column}
)
"""


def duplicate_event_uuid_sql(table: str) -> str:
    return f"""
SELECT count(*)::bigint AS duplicate_event_uuid
FROM (
    SELECT event_uuid
    FROM {table}
    GROUP BY event_uuid
    HAVING count(*) > 1
) d
"""
