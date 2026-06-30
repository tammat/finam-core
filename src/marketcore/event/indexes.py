from __future__ import annotations


def standard_event_indexes_sql(
    table: str,
    table_short_name: str,
    include_instrument: bool = True,
    include_contract: bool = True,
    include_timeframe: bool = True,
) -> str:
    statements = [
        f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_event_sequence ON {table}(event_sequence);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_event_time ON {table}(event_time);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_source_system ON {table}(source_system_id);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_quality_status ON {table}(quality_status);",
        f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_normalization_run ON {table}(normalization_run_id);",
    ]
    if include_instrument:
        statements.append(
            f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_instrument ON {table}(instrument_id);"
        )
    if include_contract:
        statements.append(
            f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_contract ON {table}(contract_id);"
        )
    if include_timeframe:
        statements.append(
            f"CREATE INDEX IF NOT EXISTS idx_{table_short_name}_timeframe ON {table}(timeframe_id);"
        )
    return "\n".join(statements)
