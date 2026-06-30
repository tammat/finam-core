from __future__ import annotations


def event_summary_sql(table: str, event_type_column: str = "event_type") -> str:
    return f"""
SELECT
    count(*)::bigint AS total_events,
    string_agg(event_count, ', ' ORDER BY event_count) AS event_count
FROM (
    SELECT {event_type_column}::text || ':' || count(*)::text AS event_count
    FROM {table}
    GROUP BY {event_type_column}
) s
"""


def event_health_sql(table: str) -> str:
    return f"""
SELECT
    count(*)::bigint AS total_events,
    count(*) FILTER (WHERE quality_status='VALID')::bigint AS valid_events,
    count(*) FILTER (WHERE quality_status='WARNING')::bigint AS warning_events,
    count(*) FILTER (WHERE quality_status='REJECTED')::bigint AS rejected_events,
    count(*) FILTER (WHERE quality_status='REVIEW_REQUIRED')::bigint AS review_required_events
FROM {table}
"""


def event_list_sql(
    table: str,
    columns: tuple[str, ...],
    order_column: str = "event_time",
    limit: int = 100,
) -> str:
    selected = ", ".join(columns)
    return f"""
SELECT {selected}
FROM {table}
ORDER BY {order_column} DESC
LIMIT {int(limit)}
"""


def event_search_sql(
    table: str,
    columns: tuple[str, ...],
    search_columns: tuple[str, ...],
    order_column: str = "event_time",
    limit: int = 100,
) -> str:
    selected = ", ".join(columns)
    condition = " OR ".join([f"{column}::text ILIKE %s" for column in search_columns])
    return f"""
SELECT {selected}
FROM {table}
WHERE {condition}
ORDER BY {order_column} DESC
LIMIT {int(limit)}
"""
