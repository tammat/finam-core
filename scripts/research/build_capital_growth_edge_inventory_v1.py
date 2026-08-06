#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from dataclasses import dataclass
from typing import Any

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


OUT = pathlib.Path("/tmp/capital_growth_edge_inventory_v1")

RELATIONS_FILE = OUT / "candidate_relations.tsv"
COLUMNS_FILE = OUT / "candidate_columns.tsv"
ROWS_FILE = OUT / "candidate_rows.tsv"
COVERAGE_FILE = OUT / "source_coverage.tsv"
CONTRACT_FILE = OUT / "inventory_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

EXCLUDED_SCHEMAS = {
    "pg_catalog",
    "information_schema",
    "pg_toast",
}

IDENTITY_ALIASES = {
    "symbol": (
        "symbol",
        "ticker",
        "instrument",
        "security_code",
    ),
    "strategy": (
        "strategy",
        "strategy_code",
        "strategy_name",
        "algorithm",
        "algo_code",
    ),
    "timeframe": (
        "timeframe",
        "interval",
        "bar_interval",
    ),
    "regime": (
        "regime",
        "market_regime",
        "regime_code",
    ),
}

METRIC_ALIASES = {
    "trade_count": (
        "trade_count",
        "trades",
        "closed_trades",
        "sample_size",
    ),
    "net_pnl": (
        "net_pnl",
        "net_profit",
        "total_net_pnl",
        "pnl_net",
    ),
    "net_expectancy": (
        "net_expectancy",
        "expectancy",
        "expectancy_net",
    ),
    "profit_factor": (
        "profit_factor",
        "profitfactor",
        "pf",
    ),
    "max_drawdown": (
        "max_drawdown",
        "maximum_drawdown",
        "drawdown",
    ),
    "commission": (
        "commission",
        "commission_cost",
        "total_commission",
        "fees",
    ),
    "slippage": (
        "slippage",
        "slippage_cost",
        "total_slippage",
    ),
    "oos_status": (
        "oos_status",
        "out_of_sample_status",
        "validation_status",
    ),
    "walk_forward_status": (
        "walk_forward_status",
        "walkforward_status",
        "wf_status",
    ),
    "robustness": (
        "robustness",
        "robustness_score",
        "stability_score",
    ),
    "lifecycle_status": (
        "lifecycle_status",
        "candidate_status",
        "status",
    ),
    "last_signal_at": (
        "last_signal_at",
        "signal_at",
        "last_seen",
        "updated_at",
        "calculated_at",
    ),
}

ALL_ALIASES = {
    **IDENTITY_ALIASES,
    **METRIC_ALIASES,
}


@dataclass(frozen=True, slots=True)
class RelationCandidate:
    schema_name: str
    relation_name: str
    relation_type: str
    estimated_rows: int
    matched_identity_count: int
    matched_metric_count: int
    score: int


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def choose_column(
    column_names: set[str],
    aliases: tuple[str, ...],
) -> str | None:
    for alias in aliases:
        if alias in column_names:
            return alias
    return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, str]] = []
    relation_rows: list[dict[str, Any]] = []
    column_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    coverage_rows: list[dict[str, Any]] = []

    connection_url = build_psycopg_url()

    with psycopg2.connect(connection_url) as connection:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    n.nspname AS schema_name,
                    c.relname AS relation_name,
                    CASE c.relkind
                        WHEN 'r' THEN 'TABLE'
                        WHEN 'p' THEN 'PARTITIONED_TABLE'
                        WHEN 'v' THEN 'VIEW'
                        WHEN 'm' THEN 'MATERIALIZED_VIEW'
                        ELSE c.relkind::text
                    END AS relation_type,
                    GREATEST(c.reltuples::bigint, 0) AS estimated_rows
                FROM pg_class c
                JOIN pg_namespace n
                  ON n.oid = c.relnamespace
                WHERE c.relkind IN ('r', 'p', 'v', 'm')
                  AND n.nspname NOT IN (
                      'pg_catalog',
                      'information_schema',
                      'pg_toast'
                  )
                ORDER BY n.nspname, c.relname
                """
            )
            relations = list(cursor.fetchall())

            for relation in relations:
                schema_name = str(relation["schema_name"])
                relation_name = str(relation["relation_name"])

                if schema_name in EXCLUDED_SCHEMAS:
                    continue

                cursor.execute(
                    """
                    SELECT
                        column_name,
                        data_type,
                        ordinal_position
                    FROM information_schema.columns
                    WHERE table_schema = %s
                      AND table_name = %s
                    ORDER BY ordinal_position
                    """,
                    (schema_name, relation_name),
                )
                columns = list(cursor.fetchall())

                column_names = {
                    str(row["column_name"]).lower()
                    for row in columns
                }

                resolved: dict[str, str | None] = {
                    logical_name: choose_column(
                        column_names,
                        aliases,
                    )
                    for logical_name, aliases in ALL_ALIASES.items()
                }

                identity_count = sum(
                    resolved[name] is not None
                    for name in IDENTITY_ALIASES
                )
                metric_count = sum(
                    resolved[name] is not None
                    for name in METRIC_ALIASES
                )

                # Не считаем relation источником edge без symbol
                # и хотя бы одной статистической метрики.
                if (
                    resolved["symbol"] is None
                    or metric_count == 0
                ):
                    continue

                score = identity_count * 10 + metric_count

                relation_rows.append(
                    {
                        "schema_name": schema_name,
                        "relation_name": relation_name,
                        "relation_type": relation["relation_type"],
                        "estimated_rows": relation["estimated_rows"],
                        "matched_identity_count": identity_count,
                        "matched_metric_count": metric_count,
                        "discovery_score": score,
                    }
                )

                for row in columns:
                    column_name = str(row["column_name"]).lower()

                    logical_matches = [
                        logical_name
                        for logical_name, aliases in ALL_ALIASES.items()
                        if column_name in aliases
                    ]

                    if not logical_matches:
                        continue

                    column_rows.append(
                        {
                            "schema_name": schema_name,
                            "relation_name": relation_name,
                            "column_name": column_name,
                            "data_type": row["data_type"],
                            "ordinal_position": row["ordinal_position"],
                            "logical_metrics": ",".join(logical_matches),
                        }
                    )

                coverage = {
                    "schema_name": schema_name,
                    "relation_name": relation_name,
                    **{
                        f"has_{logical_name}": int(
                            resolved[logical_name] is not None
                        )
                        for logical_name in ALL_ALIASES
                    },
                }
                coverage_rows.append(coverage)

                selected_columns = {
                    logical_name: physical_name
                    for logical_name, physical_name in resolved.items()
                    if physical_name is not None
                }

                projection_parts = [
                    sql.SQL("%s::text AS source_schema"),
                    sql.SQL("%s::text AS source_relation"),
                ]
                projection_values: list[Any] = [
                    schema_name,
                    relation_name,
                ]

                for logical_name in ALL_ALIASES:
                    physical_name = selected_columns.get(logical_name)

                    if physical_name is None:
                        projection_parts.append(
                            sql.SQL("NULL::text AS {}").format(
                                sql.Identifier(logical_name)
                            )
                        )
                    else:
                        projection_parts.append(
                            sql.SQL("{}::text AS {}").format(
                                sql.Identifier(physical_name),
                                sql.Identifier(logical_name),
                            )
                        )

                query = sql.SQL(
                    """
                    SELECT {}
                    FROM {}.{}
                    LIMIT 200
                    """
                ).format(
                    sql.SQL(", ").join(projection_parts),
                    sql.Identifier(schema_name),
                    sql.Identifier(relation_name),
                )

                try:
                    cursor.execute(query, projection_values)
                    extracted = list(cursor.fetchall())
                except Exception as error:
                    connection.rollback()
                    connection.set_session(readonly=True)

                    unresolved.append(
                        {
                            "scope": "RELATION_READ",
                            "identity": (
                                f"{schema_name}.{relation_name}"
                            ),
                            "reason": (
                                f"{type(error).__name__}:"
                                f"{str(error)[:240]}"
                            ),
                        }
                    )
                    continue

                for row in extracted:
                    candidate_rows.append(dict(row))

    relation_rows.sort(
        key=lambda row: (
            -int(row["discovery_score"]),
            row["schema_name"],
            row["relation_name"],
        )
    )

    write_tsv(
        RELATIONS_FILE,
        (
            "schema_name",
            "relation_name",
            "relation_type",
            "estimated_rows",
            "matched_identity_count",
            "matched_metric_count",
            "discovery_score",
        ),
        relation_rows,
    )

    write_tsv(
        COLUMNS_FILE,
        (
            "schema_name",
            "relation_name",
            "column_name",
            "data_type",
            "ordinal_position",
            "logical_metrics",
        ),
        column_rows,
    )

    row_fields = (
        "source_schema",
        "source_relation",
        *ALL_ALIASES.keys(),
    )
    write_tsv(
        ROWS_FILE,
        row_fields,
        candidate_rows,
    )

    coverage_fields = (
        "schema_name",
        "relation_name",
        *(
            f"has_{logical_name}"
            for logical_name in ALL_ALIASES
        ),
    )
    write_tsv(
        COVERAGE_FILE,
        coverage_fields,
        coverage_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    relation_count = len(relation_rows)
    candidate_row_count = len(candidate_rows)
    complete_cost_source_count = sum(
        row["has_commission"] == 1
        and row["has_slippage"] == 1
        and row["has_net_expectancy"] == 1
        for row in coverage_rows
    )
    oos_source_count = sum(
        row["has_oos_status"] == 1
        for row in coverage_rows
    )
    walk_forward_source_count = sum(
        row["has_walk_forward_status"] == 1
        for row in coverage_rows
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("CAPITAL GROWTH EDGE INVENTORY V1\n")
        stream.write("================================\n\n")
        stream.write("MODE=READ_ONLY_DISCOVERY\n")
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write(f"CANDIDATE_RELATION_COUNT={relation_count}\n")
        stream.write(f"CANDIDATE_ROW_COUNT={candidate_row_count}\n")
        stream.write(
            "COMPLETE_COST_SOURCE_COUNT="
            f"{complete_cost_source_count}\n"
        )
        stream.write(f"OOS_SOURCE_COUNT={oos_source_count}\n")
        stream.write(
            "WALK_FORWARD_SOURCE_COUNT="
            f"{walk_forward_source_count}\n"
        )
        stream.write(f"UNRESOLVED_COUNT={len(unresolved)}\n")
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("STRATEGY_CHANGED=0\n")
        stream.write("RISK_ENGINE_CHANGED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== CAPITAL GROWTH EDGE INVENTORY V1 ===")
    print(f"candidate_relation_count={relation_count}")
    print(f"candidate_row_count={candidate_row_count}")
    print(
        "complete_cost_source_count="
        f"{complete_cost_source_count}"
    )
    print(f"oos_source_count={oos_source_count}")
    print(
        "walk_forward_source_count="
        f"{walk_forward_source_count}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for row in relation_rows[:30]:
        print(
            "EDGE_SOURCE "
            f"relation={row['schema_name']}."
            f"{row['relation_name']} "
            f"rows={row['estimated_rows']} "
            f"identity={row['matched_identity_count']} "
            f"metrics={row['matched_metric_count']} "
            f"score={row['discovery_score']}"
        )

    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=CAPITAL_GROWTH_EDGE_INVENTORY_V1_READY")

    # Ошибки отдельных нерелевантных VIEW не должны отменять
    # весь инвентарь, но должны быть видны в unresolved.tsv.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
