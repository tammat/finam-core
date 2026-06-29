from __future__ import annotations


def registry_summary_sql(table: str, status_column: str = "status") -> str:
    return f"""
SELECT
    count(*)::bigint AS total_rows,
    string_agg(status_count, ', ' ORDER BY status_count) AS status_count
FROM (
    SELECT {status_column}::text || ':' || count(*)::text AS status_count
    FROM {table}
    GROUP BY {status_column}
) s
"""


def registry_list_sql(
    table: str,
    columns: tuple[str, ...],
    order_column: str,
    limit: int = 100,
) -> str:
    selected = ", ".join(columns)
    return f"""
SELECT {selected}
FROM {table}
ORDER BY {order_column}
LIMIT {int(limit)}
"""


def registry_search_sql(
    table: str,
    columns: tuple[str, ...],
    search_columns: tuple[str, ...],
    order_column: str,
    limit: int = 100,
) -> str:
    selected = ", ".join(columns)
    condition = " OR ".join([f"{column}::text ILIKE %s" for column in search_columns])
    return f"""
SELECT {selected}
FROM {table}
WHERE {condition}
ORDER BY {order_column}
LIMIT {int(limit)}
"""
