#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


DATE_FROM = "2026-05-04"
DATE_TO_EXCLUSIVE = "2026-05-30"

TIMESTAMP_COLUMNS = (
    "ts",
    "trade_ts",
    "fill_ts",
    "execution_ts",
    "executed_at",
    "created_at",
)

SYMBOL_COLUMNS = (
    "symbol",
    "ticker",
    "security_code",
    "instrument_code",
)

QUANTITY_COLUMNS = (
    "qty",
    "quantity",
    "filled_qty",
    "filled_quantity",
    "executed_qty",
)

PRICE_COLUMNS = (
    "price",
    "fill_price",
    "execution_price",
    "trade_price",
)


@dataclass(frozen=True, slots=True)
class Candidate:
    schema_name: str
    table_name: str
    object_type: str
    timestamp_column: str
    symbol_column: str
    quantity_column: str
    price_column: str


def first_available(
    columns: set[str],
    candidates: tuple[str, ...],
) -> str | None:
    for column in candidates:
        if column in columns:
            return column

    return None


def discover_candidates(
    cursor: RealDictCursor,
) -> list[Candidate]:
    cursor.execute(
        """
        SELECT
            c.table_schema,
            c.table_name,
            t.table_type,
            array_agg(
                c.column_name
                ORDER BY c.ordinal_position
            ) AS columns
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema
         AND t.table_name = c.table_name
        WHERE c.table_schema NOT IN (
            'pg_catalog',
            'information_schema'
        )
        GROUP BY
            c.table_schema,
            c.table_name,
            t.table_type
        ORDER BY
            c.table_schema,
            c.table_name
        """
    )

    result: list[Candidate] = []

    for row in cursor.fetchall():
        columns = {
            str(column)
            for column in row["columns"]
        }

        timestamp_column = first_available(
            columns,
            TIMESTAMP_COLUMNS,
        )
        symbol_column = first_available(
            columns,
            SYMBOL_COLUMNS,
        )
        quantity_column = first_available(
            columns,
            QUANTITY_COLUMNS,
        )
        price_column = first_available(
            columns,
            PRICE_COLUMNS,
        )

        if not all(
            (
                timestamp_column,
                symbol_column,
                quantity_column,
                price_column,
            )
        ):
            continue

        result.append(
            Candidate(
                schema_name=str(row["table_schema"]),
                table_name=str(row["table_name"]),
                object_type=str(row["table_type"]),
                timestamp_column=str(timestamp_column),
                symbol_column=str(symbol_column),
                quantity_column=str(quantity_column),
                price_column=str(price_column),
            )
        )

    return result


def inspect_candidate(
    cursor: RealDictCursor,
    candidate: Candidate,
) -> dict[str, Any]:
    query = sql.SQL(
        """
        SELECT
            count(*)::bigint AS total_rows,
            min({timestamp_column}) AS first_ts,
            max({timestamp_column}) AS last_ts,
            count(*) FILTER (
                WHERE {timestamp_column} >= %s::date
                  AND {timestamp_column} < %s::date
            )::bigint AS period_rows,
            count(DISTINCT {symbol_column}) FILTER (
                WHERE {timestamp_column} >= %s::date
                  AND {timestamp_column} < %s::date
            )::bigint AS period_symbol_count,
            coalesce(
                sum(abs({quantity_column})) FILTER (
                    WHERE {timestamp_column} >= %s::date
                      AND {timestamp_column} < %s::date
                ),
                0
            )::numeric AS period_quantity
        FROM {schema_name}.{table_name}
        """
    ).format(
        timestamp_column=sql.Identifier(
            candidate.timestamp_column
        ),
        symbol_column=sql.Identifier(
            candidate.symbol_column
        ),
        quantity_column=sql.Identifier(
            candidate.quantity_column
        ),
        schema_name=sql.Identifier(
            candidate.schema_name
        ),
        table_name=sql.Identifier(
            candidate.table_name
        ),
    )

    cursor.execute(
        query,
        (
            DATE_FROM,
            DATE_TO_EXCLUSIVE,
            DATE_FROM,
            DATE_TO_EXCLUSIVE,
            DATE_FROM,
            DATE_TO_EXCLUSIVE,
        ),
    )

    row = cursor.fetchone()

    return {
        "schema_name": candidate.schema_name,
        "table_name": candidate.table_name,
        "object_type": candidate.object_type,
        "timestamp_column": candidate.timestamp_column,
        "symbol_column": candidate.symbol_column,
        "quantity_column": candidate.quantity_column,
        "price_column": candidate.price_column,
        "total_rows": int(row["total_rows"] or 0),
        "first_ts": row["first_ts"],
        "last_ts": row["last_ts"],
        "period_rows": int(row["period_rows"] or 0),
        "period_symbol_count": int(
            row["period_symbol_count"] or 0
        ),
        "period_quantity": row["period_quantity"],
        "inspection_error": "",
    }


def main() -> int:
    inspected: list[dict[str, Any]] = []

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            candidates = discover_candidates(cursor)

            for candidate in candidates:
                try:
                    inspected.append(
                        inspect_candidate(
                            cursor,
                            candidate,
                        )
                    )
                except Exception as error:
                    conn.rollback()

                    inspected.append(
                        {
                            "schema_name": (
                                candidate.schema_name
                            ),
                            "table_name": (
                                candidate.table_name
                            ),
                            "object_type": (
                                candidate.object_type
                            ),
                            "timestamp_column": (
                                candidate.timestamp_column
                            ),
                            "symbol_column": (
                                candidate.symbol_column
                            ),
                            "quantity_column": (
                                candidate.quantity_column
                            ),
                            "price_column": (
                                candidate.price_column
                            ),
                            "total_rows": 0,
                            "first_ts": None,
                            "last_ts": None,
                            "period_rows": 0,
                            "period_symbol_count": 0,
                            "period_quantity": 0,
                            "inspection_error": (
                                f"{type(error).__name__}:"
                                f"{error}"
                            ),
                        }
                    )

    inspected.sort(
        key=lambda row: (
            -int(row["period_rows"]),
            row["schema_name"],
            row["table_name"],
        )
    )

    usable = [
        row
        for row in inspected
        if int(row["period_rows"]) > 0
    ]

    print("=== HISTORICAL FUTURES FILL SOURCE V1 ===")
    print(f"date_from={DATE_FROM}")
    print(f"date_to_exclusive={DATE_TO_EXCLUSIVE}")
    print(f"candidate_count={len(inspected)}")
    print(f"usable_candidate_count={len(usable)}")

    for row in inspected:
        print(
            "SOURCE_CANDIDATE "
            f"schema={row['schema_name']} "
            f"table={row['table_name']} "
            f"type={row['object_type']} "
            f"timestamp={row['timestamp_column']} "
            f"symbol={row['symbol_column']} "
            f"quantity={row['quantity_column']} "
            f"price={row['price_column']} "
            f"total_rows={row['total_rows']} "
            f"first_ts={row['first_ts']} "
            f"last_ts={row['last_ts']} "
            f"period_rows={row['period_rows']} "
            f"period_symbols="
            f"{row['period_symbol_count']} "
            f"period_quantity="
            f"{row['period_quantity']} "
            f"error={row['inspection_error']}"
        )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if not usable:
        print(
            "VERDICT="
            "HISTORICAL_FUTURES_FILL_SOURCE_V1_NOT_FOUND"
        )
        return 2

    best = usable[0]

    print(
        "RECOMMENDED_SOURCE "
        f"schema={best['schema_name']} "
        f"table={best['table_name']} "
        f"timestamp_column="
        f"{best['timestamp_column']} "
        f"symbol_column={best['symbol_column']} "
        f"quantity_column="
        f"{best['quantity_column']} "
        f"price_column={best['price_column']}"
    )

    print(
        "VERDICT="
        "HISTORICAL_FUTURES_FILL_SOURCE_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
