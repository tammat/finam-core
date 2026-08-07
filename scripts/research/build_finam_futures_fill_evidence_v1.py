#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import pathlib
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


DEFAULT_INPUT = pathlib.Path(
    "config/research/finam_futures_fill_evidence_v1.tsv"
)

REQUIRED_COLUMNS = (
    "execution_ts",
    "trade_date",
    "symbol",
    "side",
    "quantity_contracts",
    "price",
    "trade_id",
    "order_id",
    "broker_account",
    "source_document",
    "source_reference",
    "source_version",
    "evidence_status",
)


@dataclass(frozen=True, slots=True)
class FillEvidence:
    execution_ts: datetime
    trade_date: date
    symbol: str
    side: str
    quantity_contracts: Decimal
    price: Decimal
    trade_id: str
    order_id: str
    broker_account: str
    source_document: str
    source_reference: str
    source_version: str
    evidence_status: str


def parse_decimal(
    value: Any,
    *,
    field: str,
    line_number: int,
) -> Decimal:
    text = str(value or "").strip().replace(",", ".")

    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError(
            f"invalid_decimal:{line_number}:{field}:{text}"
        ) from error


def derived_trade_id(
    *,
    execution_ts: datetime,
    symbol: str,
    side: str,
    quantity: Decimal,
    price: Decimal,
    source_reference: str,
) -> str:
    payload = "|".join(
        (
            execution_ts.isoformat(),
            symbol,
            side,
            str(quantity),
            str(price),
            source_reference,
        )
    )

    return "DERIVED_" + hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()[:32]


def load_rows(
    path: pathlib.Path,
    *,
    allow_derived_trade_id: bool,
) -> tuple[list[FillEvidence], list[dict[str, str]]]:
    rows: list[FillEvidence] = []
    unresolved: list[dict[str, str]] = []

    if not path.is_file():
        return rows, [
            {
                "scope": "INPUT_FILE",
                "identity": str(path),
                "reason": "FILE_MISSING",
            }
        ]

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        available = set(reader.fieldnames or [])
        missing = sorted(set(REQUIRED_COLUMNS) - available)

        if missing:
            return rows, [
                {
                    "scope": "INPUT_SCHEMA",
                    "identity": str(path),
                    "reason": (
                        "REQUIRED_COLUMNS_MISSING:"
                        + ",".join(missing)
                    ),
                }
            ]

        seen: set[tuple[str, str, str]] = set()

        for line_number, row in enumerate(reader, start=2):
            if not any(
                str(value or "").strip()
                for value in row.values()
            ):
                continue

            try:
                execution_ts = datetime.fromisoformat(
                    str(row["execution_ts"]).strip()
                )

                if execution_ts.tzinfo is None:
                    raise ValueError(
                        "execution_timezone_required"
                    )

                trade_date = date.fromisoformat(
                    str(row["trade_date"]).strip()
                )

                if execution_ts.date() != trade_date:
                    raise ValueError(
                        "trade_date_execution_ts_mismatch"
                    )

                symbol = str(
                    row["symbol"] or ""
                ).strip().upper()

                if "@" not in symbol:
                    raise ValueError(
                        f"canonical_symbol_required:{symbol}"
                    )

                side = str(
                    row["side"] or ""
                ).strip().upper()

                if side not in {"BUY", "SELL"}:
                    raise ValueError(f"invalid_side:{side}")

                quantity = parse_decimal(
                    row["quantity_contracts"],
                    field="quantity_contracts",
                    line_number=line_number,
                )
                price = parse_decimal(
                    row["price"],
                    field="price",
                    line_number=line_number,
                )

                if quantity <= 0:
                    raise ValueError(
                        "quantity_contracts_not_positive"
                    )

                if price <= 0:
                    raise ValueError("price_not_positive")

                broker_account = str(
                    row["broker_account"] or ""
                ).strip()
                source_document = str(
                    row["source_document"] or ""
                ).strip()
                source_reference = str(
                    row["source_reference"] or ""
                ).strip()
                source_version = str(
                    row["source_version"] or ""
                ).strip()
                evidence_status = str(
                    row["evidence_status"] or ""
                ).strip().upper()
                order_id = str(
                    row["order_id"] or ""
                ).strip()
                trade_id = str(
                    row["trade_id"] or ""
                ).strip()

                required_text = {
                    "broker_account": broker_account,
                    "source_document": source_document,
                    "source_reference": source_reference,
                    "source_version": source_version,
                }

                missing_text = [
                    field
                    for field, value in required_text.items()
                    if not value
                ]

                if missing_text:
                    raise ValueError(
                        "required_text_missing:"
                        + ",".join(missing_text)
                    )

                if evidence_status not in {
                    "VERIFIED",
                    "REVIEW_REQUIRED",
                }:
                    raise ValueError(
                        f"invalid_evidence_status:{evidence_status}"
                    )

                if not trade_id:
                    if not allow_derived_trade_id:
                        raise ValueError("trade_id_missing")

                    trade_id = derived_trade_id(
                        execution_ts=execution_ts,
                        symbol=symbol,
                        side=side,
                        quantity=quantity,
                        price=price,
                        source_reference=source_reference,
                    )
                    evidence_status = "REVIEW_REQUIRED"

                identity = (
                    broker_account,
                    trade_id,
                    source_version,
                )

                if identity in seen:
                    raise ValueError(
                        "duplicate_input_identity:"
                        + ":".join(identity)
                    )

                seen.add(identity)

                rows.append(
                    FillEvidence(
                        execution_ts=execution_ts,
                        trade_date=trade_date,
                        symbol=symbol,
                        side=side,
                        quantity_contracts=quantity,
                        price=price,
                        trade_id=trade_id,
                        order_id=order_id,
                        broker_account=broker_account,
                        source_document=source_document,
                        source_reference=source_reference,
                        source_version=source_version,
                        evidence_status=evidence_status,
                    )
                )
            except Exception as error:
                unresolved.append(
                    {
                        "scope": "INPUT_ROW",
                        "identity": f"line:{line_number}",
                        "reason": str(error),
                    }
                )

    return rows, unresolved


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finam Futures Fill Evidence Import V1"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
    )
    parser.add_argument(
        "--allow-derived-trade-id",
        action="store_true",
    )
    parser.add_argument(
        "--save",
        action="store_true",
    )
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)

    rows, unresolved = load_rows(
        input_path,
        allow_derived_trade_id=args.allow_derived_trade_id,
    )

    if not rows:
        unresolved.append(
            {
                "scope": "INPUT_EVIDENCE",
                "identity": str(input_path),
                "reason": "NO_VALID_FILL_ROWS",
            }
        )

    inserted = 0
    updated = 0

    if args.save and not unresolved:
        with psycopg2.connect(build_psycopg_url()) as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor,
            ) as cursor:
                for row in rows:
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
                            %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (
                            broker_account,
                            trade_id,
                            source_version
                        )
                        DO UPDATE SET
                            execution_ts =
                                EXCLUDED.execution_ts,
                            trade_date =
                                EXCLUDED.trade_date,
                            symbol =
                                EXCLUDED.symbol,
                            side =
                                EXCLUDED.side,
                            quantity_contracts =
                                EXCLUDED.quantity_contracts,
                            price =
                                EXCLUDED.price,
                            order_id =
                                EXCLUDED.order_id,
                            source_document =
                                EXCLUDED.source_document,
                            source_reference =
                                EXCLUDED.source_reference,
                            evidence_status =
                                EXCLUDED.evidence_status
                        RETURNING (xmax = 0) AS inserted
                        """,
                        (
                            row.execution_ts,
                            row.trade_date,
                            row.symbol,
                            row.side,
                            row.quantity_contracts,
                            row.price,
                            row.trade_id,
                            row.order_id,
                            row.broker_account,
                            row.source_document,
                            row.source_reference,
                            row.source_version,
                            row.evidence_status,
                        ),
                    )

                    result = cursor.fetchone()

                    if bool(result["inserted"]):
                        inserted += 1
                    else:
                        updated += 1

    verified_count = sum(
        row.evidence_status == "VERIFIED"
        for row in rows
    )
    review_count = sum(
        row.evidence_status == "REVIEW_REQUIRED"
        for row in rows
    )
    day_count = len({row.trade_date for row in rows})
    symbol_count = len({row.symbol for row in rows})
    quantity_total = sum(
        (row.quantity_contracts for row in rows),
        Decimal("0"),
    )

    print("=== FINAM FUTURES FILL EVIDENCE IMPORT V1 ===")
    print(f"input_file={input_path}")
    print(f"valid_fill_count={len(rows)}")
    print(f"verified_fill_count={verified_count}")
    print(f"review_required_count={review_count}")
    print(f"trade_day_count={day_count}")
    print(f"symbol_count={symbol_count}")
    print(f"quantity_contracts_total={quantity_total}")
    print(f"inserted_count={inserted}")
    print(f"updated_count={updated}")
    print(f"unresolved_count={len(unresolved)}")

    for item in unresolved:
        print(
            "UNRESOLVED "
            f"scope={item['scope']} "
            f"identity={item['identity']} "
            f"reason={item['reason']}"
        )

    print(
        f"db_writes_performed="
        f"{1 if args.save and not unresolved else 0}"
    )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")

    if unresolved:
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_IMPORT_V1_BLOCKED"
        )
        return 2

    if args.save:
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_IMPORT_V1_READY"
        )
    else:
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_IMPORT_V1_DRY_RUN_OK"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
