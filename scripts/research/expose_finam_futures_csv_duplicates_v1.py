#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path


BUY_OPERATION = "Покупка производного финансового инструмента"
SELL_OPERATION = "Продажа производного финансового инструмента"


def parse_decimal(value: str) -> Decimal:
    return Decimal(
        str(value or "")
        .strip()
        .replace(" ", "")
        .replace(",", ".")
    )


def side_from_operation(operation: str) -> str | None:
    if operation.strip() == BUY_OPERATION:
        return "BUY"

    if operation.strip() == SELL_OPERATION:
        return "SELL"

    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()

    path = Path(args.input)

    groups: dict[
        tuple[str, str, str, str, str, str],
        list[dict[str, str]],
    ] = defaultdict(list)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream, delimiter=";")

        for line_number, row in enumerate(reader, start=2):
            side = side_from_operation(
                str(row.get("Операция") or "")
            )

            if side is None:
                continue

            execution_ts = datetime.fromisoformat(
                f"{str(row['Дата']).strip()}T"
                f"{str(row['Время']).strip()}+03:00"
            )

            ticker = str(
                row.get("Тикер") or ""
            ).strip().upper()

            symbol = (
                ticker
                if "@" in ticker
                else f"{ticker}@RTSX"
            )

            quantity = parse_decimal(
                str(row.get("Количество") or "")
            )
            price = parse_decimal(
                str(row.get("Цена за штуку") or "")
            )
            account = str(
                row.get("Идентификатор счета") or ""
            ).strip()

            key = (
                execution_ts.isoformat(),
                symbol,
                side,
                str(quantity),
                str(price),
                account,
            )

            groups[key].append(
                {
                    "line_number": str(line_number),
                    "date": str(row.get("Дата") or ""),
                    "time": str(row.get("Время") or ""),
                    "operation": str(
                        row.get("Операция") or ""
                    ),
                    "security_name": str(
                        row.get(
                            "Краткое наименование ценной бумаги"
                        )
                        or ""
                    ),
                    "ticker": ticker,
                    "account": account,
                    "quantity": str(
                        row.get("Количество") or ""
                    ),
                    "price": str(
                        row.get("Цена за штуку") or ""
                    ),
                    "comment": str(
                        row.get("Комментарий") or ""
                    ),
                    "full_operation": str(
                        row.get(
                            "Полное наименование операции"
                        )
                        or ""
                    ),
                    "transaction_volume": str(
                        row.get("Объем транзакции") or ""
                    ),
                    "currency": str(
                        row.get("Валюта") or ""
                    ),
                }
            )

    duplicate_groups = [
        (key, rows)
        for key, rows in groups.items()
        if len(rows) > 1
    ]

    duplicate_groups.sort(
        key=lambda item: (
            item[0][0],
            item[0][1],
            item[0][2],
        )
    )

    print("=== FINAM FUTURES CSV DUPLICATES V1 ===")
    print(
        f"duplicate_group_count={len(duplicate_groups)}"
    )
    print(
        "duplicate_row_count="
        f"{sum(len(rows) for _, rows in duplicate_groups)}"
    )

    for group_no, (key, rows) in enumerate(
        duplicate_groups,
        start=1,
    ):
        (
            execution_ts,
            symbol,
            side,
            quantity,
            price,
            account,
        ) = key

        print(
            "DUPLICATE_GROUP "
            f"group={group_no} "
            f"count={len(rows)} "
            f"execution_ts={execution_ts} "
            f"symbol={symbol} "
            f"side={side} "
            f"quantity={quantity} "
            f"price={price} "
            f"account={account}"
        )

        for row in rows:
            print(
                "DUPLICATE_ROW "
                f"group={group_no} "
                f"line={row['line_number']} "
                f"operation={row['operation']!r} "
                f"security_name={row['security_name']!r} "
                f"ticker={row['ticker']!r} "
                f"quantity={row['quantity']!r} "
                f"price={row['price']!r} "
                f"volume={row['transaction_volume']!r} "
                f"currency={row['currency']!r} "
                f"comment={row['comment']!r} "
                f"full_operation={row['full_operation']!r}"
            )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FINAM_FUTURES_CSV_DUPLICATES_V1_EXPOSED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
