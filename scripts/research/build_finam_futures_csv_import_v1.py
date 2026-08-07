#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


BUY_OPERATION = "Покупка производного финансового инструмента"
SELL_OPERATION = "Продажа производного финансового инструмента"

REQUIRED_COLUMNS = {
    "Дата",
    "Время",
    "Операция",
    "Тикер",
    "Идентификатор счета",
    "Количество",
    "Цена за штуку",
}


def parse_decimal(
    value: Any,
    *,
    field: str,
    line_number: int,
) -> Decimal:
    text = str(value or "").strip().replace(" ", "").replace(",", ".")

    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError(
            f"invalid_decimal:line:{line_number}:{field}:{text}"
        ) from error


def get_side(operation: str) -> str | None:
    if operation == BUY_OPERATION:
        return "BUY"

    if operation == SELL_OPERATION:
        return "SELL"

    return None


def make_trade_id(
    *,
    execution_ts: datetime,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    broker_account: str,
    occurrence: int,
) -> str:
    payload = "|".join(
        (
            execution_ts.isoformat(),
            symbol,
            side,
            str(quantity),
            str(price),
            broker_account,
        )
    )

    digest = hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()[:24]

    return f"FINAM_{digest}_{occurrence:03d}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finam Futures CSV Import V1"
    )
    parser.add_argument("--input", required=True)
    parser.add_argument(
        "--source-document",
        default="FINAM_OPERATIONS_EXPORT_2026_05",
    )
    parser.add_argument(
        "--source-version",
        default="FINAM_FUTURES_CSV_IMPORT_V1",
    )
    parser.add_argument(
        "--allow-duplicate-fingerprints",
        action="store_true",
    )
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.is_file():
        raise SystemExit(
            f"ERROR=input_file_missing:{input_path}"
        )

    parsed: list[dict[str, Any]] = []
    unresolved: list[str] = []
    skipped = 0

    with input_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream, delimiter=";")

        missing = sorted(
            REQUIRED_COLUMNS - set(reader.fieldnames or [])
        )

        if missing:
            raise SystemExit(
                "ERROR=required_columns_missing:"
                + ",".join(missing)
            )

        for line_number, row in enumerate(reader, start=2):
            operation = str(
                row.get("Операция") or ""
            ).strip()

            side = get_side(operation)

            if side is None:
                skipped += 1
                continue

            try:
                execution_ts = datetime.fromisoformat(
                    f"{row['Дата'].strip()}T"
                    f"{row['Время'].strip()}+03:00"
                )

                ticker = str(
                    row.get("Тикер") or ""
                ).strip().upper()

                if not ticker:
                    raise ValueError("ticker_missing")

                symbol = (
                    ticker
                    if "@" in ticker
                    else f"{ticker}@RTSX"
                )

                quantity = parse_decimal(
                    row.get("Количество"),
                    field="Количество",
                    line_number=line_number,
                )

                price = parse_decimal(
                    row.get("Цена за штуку"),
                    field="Цена за штуку",
                    line_number=line_number,
                )

                if quantity <= 0:
                    raise ValueError(
                        "quantity_contracts_not_positive"
                    )

                if price <= 0:
                    raise ValueError("price_not_positive")

                broker_account = str(
                    row.get("Идентификатор счета") or ""
                ).strip()

                if not broker_account:
                    raise ValueError(
                        "broker_account_missing"
                    )

                fingerprint = "|".join(
                    (
                        execution_ts.isoformat(),
                        symbol,
                        side,
                        str(quantity),
                        str(price),
                        broker_account,
                    )
                )

                parsed.append(
                    {
                        "line_number": line_number,
                        "execution_ts": execution_ts,
                        "trade_date": execution_ts.date(),
                        "symbol": symbol,
                        "side": side,
                        "quantity": quantity,
                        "price": price,
                        "broker_account": broker_account,
                        "fingerprint": fingerprint,
                    }
                )

            except Exception as error:
                unresolved.append(
                    f"line:{line_number}:{error}"
                )

    fingerprint_counts = Counter(
        row["fingerprint"]
        for row in parsed
    )

    duplicate_groups = {
        key: count
        for key, count in fingerprint_counts.items()
        if count > 1
    }

    occurrence_counter: Counter[str] = Counter()

    for row in parsed:
        fingerprint = row["fingerprint"]
        occurrence_counter[fingerprint] += 1

        row["trade_id"] = make_trade_id(
            execution_ts=row["execution_ts"],
            symbol=row["symbol"],
            side=row["side"],
            quantity=row["quantity"],
            price=row["price"],
            broker_account=row["broker_account"],
            occurrence=occurrence_counter[fingerprint],
        )

        row["evidence_status"] = (
            "REVIEW_REQUIRED"
            if fingerprint_counts[fingerprint] > 1
            else "VERIFIED"
        )

    blocking_duplicate_count = (
        0
        if args.allow_duplicate_fingerprints
        else len(duplicate_groups)
    )

    inserted = 0
    updated = 0

    save_allowed = (
        bool(parsed)
        and not unresolved
        and blocking_duplicate_count == 0
    )

    if args.save and save_allowed:
        with psycopg2.connect(build_psycopg_url()) as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor,
            ) as cursor:
                for row in parsed:
                    cursor.execute(
                        """
                        INSERT INTO
                            analytics.futures_fill_evidence_v1 (
                                execution_ts,
                                trade_date,
                                symbol,
                                side,
                                quantity_contracts,
                                price,
                                trade_id,
                                order_id,
                                broker_account,
                                source_document,
                                source_reference,
                                source_version,
                                evidence_status
                            )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            '', %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (
                            broker_account,
                            trade_id,
                            source_version
                        )
                        DO UPDATE SET
                            execution_ts = EXCLUDED.execution_ts,
                            trade_date = EXCLUDED.trade_date,
                            symbol = EXCLUDED.symbol,
                            side = EXCLUDED.side,
                            quantity_contracts =
                                EXCLUDED.quantity_contracts,
                            price = EXCLUDED.price,
                            source_document =
                                EXCLUDED.source_document,
                            source_reference =
                                EXCLUDED.source_reference,
                            evidence_status =
                                EXCLUDED.evidence_status
                        RETURNING (xmax = 0) AS inserted
                        """,
                        (
                            row["execution_ts"],
                            row["trade_date"],
                            row["symbol"],
                            row["side"],
                            row["quantity"],
                            row["price"],
                            row["trade_id"],
                            row["broker_account"],
                            args.source_document,
                            f"CSV_LINE_{row['line_number']}",
                            args.source_version,
                            row["evidence_status"],
                        ),
                    )

                    result = cursor.fetchone()

                    if bool(result["inserted"]):
                        inserted += 1
                    else:
                        updated += 1

    verified = sum(
        row["evidence_status"] == "VERIFIED"
        for row in parsed
    )

    review_required = sum(
        row["evidence_status"] == "REVIEW_REQUIRED"
        for row in parsed
    )

    print("=== FINAM FUTURES CSV IMPORT V1 ===")
    print(f"input_file={input_path}")
    print(f"futures_fill_count={len(parsed)}")
    print(f"verified_fill_count={verified}")
    print(f"review_required_count={review_required}")
    print(f"skipped_non_futures_row_count={skipped}")
    print(
        "duplicate_fingerprint_group_count="
        f"{len(duplicate_groups)}"
    )
    print(
        "duplicate_fingerprint_row_count="
        f"{sum(duplicate_groups.values())}"
    )
    print(
        f"blocking_duplicate_count="
        f"{blocking_duplicate_count}"
    )
    print(f"unresolved_count={len(unresolved)}")
    print(f"inserted_count={inserted}")
    print(f"updated_count={updated}")

    for fingerprint, count in duplicate_groups.items():
        matches = [
            row
            for row in parsed
            if row["fingerprint"] == fingerprint
        ]

        first = matches[0]

        print(
            "DUPLICATE_FINGERPRINT "
            f"count={count} "
            f"symbol={first['symbol']} "
            f"ts={first['execution_ts']} "
            f"side={first['side']} "
            f"quantity={first['quantity']} "
            f"price={first['price']} "
            f"lines="
            + ",".join(
                str(row["line_number"])
                for row in matches
            )
        )

    for item in unresolved:
        print(f"UNRESOLVED={item}")

    print(
        f"db_writes_performed="
        f"{1 if args.save and save_allowed else 0}"
    )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")

    if not parsed:
        print("VERDICT=FINAM_FUTURES_CSV_IMPORT_V1_NO_FILLS")
        return 2

    if unresolved or blocking_duplicate_count > 0:
        print(
            "VERDICT="
            "FINAM_FUTURES_CSV_IMPORT_V1_REVIEW_REQUIRED"
        )
        return 2

    if args.save:
        print("VERDICT=FINAM_FUTURES_CSV_IMPORT_V1_READY")
    else:
        print(
            "VERDICT="
            "FINAM_FUTURES_CSV_IMPORT_V1_DRY_RUN_OK"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
