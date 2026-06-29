from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RegistryValidationSpec:
    table: str
    code_column: str
    required_columns: tuple[str, ...]
    status_column: str = "status"
    maturity_column: str = "maturity_level"


def required_fields_sql(spec: RegistryValidationSpec) -> str:
    conditions = [
        f"coalesce({column}::text, '') <> ''"
        for column in spec.required_columns
    ]
    return f"""
SELECT count(*)::bigint AS valid_rows
FROM {spec.table}
WHERE {' AND '.join(conditions)}
"""


def duplicate_codes_sql(spec: RegistryValidationSpec) -> str:
    return f"""
SELECT count(*)::bigint AS duplicate_codes
FROM (
    SELECT {spec.code_column}
    FROM {spec.table}
    GROUP BY {spec.code_column}
    HAVING count(*) > 1
) d
"""


def invalid_values_sql(table: str, column: str, allowed_values: Iterable[str]) -> str:
    values = ",".join("'" + v.replace("'", "''") + "'" for v in allowed_values)
    return f"""
SELECT count(*)::bigint AS invalid_values
FROM {table}
WHERE {column} IS NULL OR {column}::text NOT IN ({values})
"""


def unsafe_approvals_sql(table: str) -> str:
    return f"""
SELECT count(*)::bigint AS unsafe_approvals
FROM {table}
WHERE coalesce(approved_for_live, false)=true
"""
