#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from datetime import datetime
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


CONTRACT_PATTERN = re.compile(
    r"^(?P<root>[A-Z]+)"
    r"(?P<month>[FGHJKMNQUVXZ])"
    r"(?P<year>[0-9])"
    r"@RTSX$"
)

MONTH_NUMBER = {
    "F": 1,
    "G": 2,
    "H": 3,
    "J": 4,
    "K": 5,
    "M": 6,
    "N": 7,
    "Q": 8,
    "U": 9,
    "V": 10,
    "X": 11,
    "Z": 12,
}


def as_int(value: Any) -> int:
    return int(value or 0)


def contract_sort_key(symbol: str) -> tuple[int, int, str]:
    match = CONTRACT_PATTERN.match(symbol)

    if match is None:
        return (9999, 99, symbol)

    year_digit = int(match.group("year"))

    # Проект работает с контрактами 2026 года.
    year = 2020 + year_digit
    month = MONTH_NUMBER[match.group("month")]

    return (year, month, symbol)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Futures Continuous Symbol Resolution V1"
    )
    parser.add_argument(
        "--continuous-symbol",
        default="NG@RTSX",
    )
    parser.add_argument(
        "--bar-schema",
        default="public",
    )
    parser.add_argument(
        "--bar-table",
        default="market_bars",
    )
    parser.add_argument(
        "--minimum-bars",
        type=int,
        default=100,
    )
    args = parser.parse_args()

    root = args.continuous_symbol.split("@", 1)[0]

    if not root:
        raise SystemExit(
            "ERROR=continuous_symbol_root_missing"
        )

    pattern = f"{root}%@RTSX"

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                SELECT
                    column_name
                FROM information_schema.columns
                WHERE table_schema = %s
                  AND table_name = %s
                ORDER BY ordinal_position
                """,
                (
                    args.bar_schema,
                    args.bar_table,
                ),
            )

            columns = {
                str(row["column_name"])
                for row in cur.fetchall()
            }

            required = {
                "symbol",
                "timeframe",
                "ts",
            }

            missing = sorted(required - columns)

            if missing:
                raise SystemExit(
                    "ERROR=bar_columns_missing:"
                    + ",".join(missing)
                )

            query = f"""
                SELECT
                    symbol,
                    timeframe,
                    count(*)::bigint AS bar_count,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM {args.bar_schema}.{args.bar_table}
                WHERE symbol LIKE %s
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """

            cur.execute(query, (pattern,))

            rows = [
                dict(row)
                for row in cur.fetchall()
            ]

    valid_rows: list[dict[str, Any]] = []
    invalid_symbols: list[str] = []

    for row in rows:
        symbol = str(row["symbol"])

        match = CONTRACT_PATTERN.match(symbol)

        if match is None:
            invalid_symbols.append(symbol)
            continue

        if match.group("root") != root:
            continue

        if as_int(row["bar_count"]) < args.minimum_bars:
            continue

        row["contract_year"] = (
            2020 + int(match.group("year"))
        )
        row["contract_month"] = MONTH_NUMBER[
            match.group("month")
        ]

        valid_rows.append(row)

    valid_rows.sort(
        key=lambda row: (
            contract_sort_key(str(row["symbol"])),
            str(row["timeframe"]),
        )
    )

    symbol_rows: dict[str, list[dict[str, Any]]] = {}

    for row in valid_rows:
        symbol_rows.setdefault(
            str(row["symbol"]),
            [],
        ).append(row)

    recommended_symbol = None

    if symbol_rows:
        latest_symbols = sorted(
            symbol_rows,
            key=contract_sort_key,
        )

        recommended_symbol = latest_symbols[-1]

    print("=== FUTURES CONTINUOUS SYMBOL RESOLUTION V1 ===")
    print(
        f"continuous_symbol="
        f"{args.continuous_symbol}"
    )
    print(f"contract_root={root}")
    print(
        f"bar_source="
        f"{args.bar_schema}.{args.bar_table}"
    )
    print(f"minimum_bars={args.minimum_bars}")
    print(f"raw_contract_row_count={len(rows)}")
    print(
        f"eligible_contract_row_count="
        f"{len(valid_rows)}"
    )
    print(
        f"eligible_contract_count="
        f"{len(symbol_rows)}"
    )
    print(
        f"invalid_symbol_count="
        f"{len(set(invalid_symbols))}"
    )

    for row in valid_rows:
        print(
            "CONTRACT_COVERAGE "
            f"continuous_symbol="
            f"{args.continuous_symbol} "
            f"contract_symbol={row['symbol']} "
            f"timeframe={row['timeframe']} "
            f"bars={row['bar_count']} "
            f"first_ts={row['first_ts']} "
            f"last_ts={row['last_ts']} "
            f"contract_year={row['contract_year']} "
            f"contract_month="
            f"{row['contract_month']}"
        )

    for symbol in sorted(set(invalid_symbols)):
        print(
            "UNRESOLVED "
            f"scope=CONTRACT_SYMBOL "
            f"identity={symbol} "
            f"reason=CONTRACT_PATTERN_NOT_RECOGNIZED"
        )

    print(
        "recommended_contract_symbol="
        f"{recommended_symbol or 'NONE'}"
    )

    print("db_writes_performed=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")

    if not valid_rows:
        print(
            "VERDICT="
            "FUTURES_CONTINUOUS_SYMBOL_RESOLUTION_V1_BLOCKED"
        )
        return 2

    print(
        "VERDICT="
        "FUTURES_CONTINUOUS_SYMBOL_RESOLUTION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
