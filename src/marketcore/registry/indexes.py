from __future__ import annotations


def standard_registry_indexes_sql(
    table: str,
    table_short_name: str,
    code_column: str,
    type_column: str | None = None,
    status_column: str = "status",
    maturity_column: str = "maturity_level",
    updated_column: str = "updated_at",
) -> str:
    statements = [
        f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{table_short_name}_code ON {table}({code_column});",
        f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_status ON {table}({status_column});",
        f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_maturity ON {table}({maturity_column});",
        f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_updated_at ON {table}({updated_column});",
    ]
    if type_column:
        statements.append(
            f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_type ON {table}({type_column});"
        )
    return "\n".join(statements)
