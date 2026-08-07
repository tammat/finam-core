#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


DEFAULT_INPUT = Path(
    "config/research/finam_futures_daily_commission_v1.tsv"
)

REQUIRED_COLUMNS = {
    "trade_date",
    "broker_account",
    "commission_total",
    "currency_code",
    "source_document",
    "source_reference",
    "source_version",
    "evidence_status",
}


def parse_decimal(value: Any, line_number: int) -> Decimal:
    text = (
        str(value or "")
        .strip()
        .replace(" ", "")
        .replace(",", ".")
    )

    try:
        result = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(
            f"invalid_commission:line:{line_number}:{text}"
        ) from error

    if result <= 0:
        raise ValueError(
            f"commission_not_positive:line:{line_number}"
        )

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Load Finam Futures Daily Commission V1"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
    )
    parser.add_argument(
        "--save",
        action="store_true",
    )
    args = parser.parse_args()

    input_path = Path(args.input)

    if not input_path.is_file():
        raise SystemExit(
            f"ERROR=input_file_missing:{input_path}"
        )

    rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    identities: set[tuple[date, str, str]] = set()

    with input_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as stream:
        reader = csv.DictReader(
            stream,
            delimiter="\t",
        )

        missing = sorted(
            REQUIRED_COLUMNS - set(reader.fieldnames or [])
        )

        if missing:
            raise SystemExit(
                "ERROR=required_columns_missing:"
                + ",".join(missing)
            )

        for line_number, row in enumerate(reader, start=2):
            if not any(
                str(value or "").strip()
                for value in row.values()
            ):
                continue

            try:
                trade_date = date.fromisoformat(
                    str(row["trade_date"]).strip()
                )

                broker_account = str(
                    row["broker_account"] or ""
                ).strip()

                commission_total = parse_decimal(
                    row["commission_total"],
                    line_number,
                )

                currency_code = str(
                    row["currency_code"] or ""
                ).strip().upper()

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

                if not broker_account:
                    raise ValueError(
                        "broker_account_missing"
                    )

                if not currency_code:
                    raise ValueError(
                        "currency_code_missing"
                    )

                if not source_document:
                    raise ValueError(
                        "source_document_missing"
                    )

                if not source_reference:
                    raise ValueError(
                        "source_reference_missing"
                    )

                if not source_version:
                    raise ValueError(
                        "source_version_missing"
                    )

                if evidence_status not in {
                    "VERIFIED",
                    "REVIEW_REQUIRED",
                }:
                    raise ValueError(
                        "invalid_evidence_status:"
                        f"{evidence_status}"
                    )

                identity = (
                    trade_date,
                    broker_account,
                    source_version,
                )

                if identity in identities:
                    raise ValueError(
                        "duplicate_input_identity:"
                        f"{trade_date}:"
                        f"{broker_account}:"
                        f"{source_version}"
                    )

                identities.add(identity)

                rows.append(
                    {
                        "trade_date": trade_date,
                        "broker_account": broker_account,
                        "commission_total": commission_total,
                        "currency_code": currency_code,
                        "source_document": source_document,
                        "source_reference": source_reference,
                        "source_version": source_version,
                        "evidence_status": evidence_status,
                    }
                )

            except Exception as error:
                unresolved.append(
                    f"line:{line_number}:{error}"
                )

    inserted_count = 0
    updated_count = 0

    if args.save and rows and not unresolved:
        with psycopg2.connect(build_psycopg_url()) as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor,
            ) as cursor:
                for row in rows:
                    cursor.execute(
                        """
                        INSERT INTO
                            analytics.futures_commission_daily_v1 (
                                trade_date,
                                broker_account,
                                commission_total,
                                currency_code,
                                source_document,
                                source_reference,
                                source_version,
                                evidence_status
                            )
                        VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s, %s
                        )
                        ON CONFLICT (
                            trade_date,
                            broker_account,
                            source_version
                        )
                        DO UPDATE SET
                            commission_total =
                                EXCLUDED.commission_total,
                            currency_code =
                                EXCLUDED.currency_code,
                            source_document =
                                EXCLUDED.source_document,
                            source_reference =
                                EXCLUDED.source_reference,
                            evidence_status =
                                EXCLUDED.evidence_status
                        RETURNING (xmax = 0) AS inserted
                        """,
                        (
                            row["trade_date"],
                            row["broker_account"],
                            row["commission_total"],
                            row["currency_code"],
                            row["source_document"],
                            row["source_reference"],
                            row["source_version"],
                            row["evidence_status"],
                        ),
                    )

                    result = cursor.fetchone()

                    if bool(result["inserted"]):
                        inserted_count += 1
                    else:
                        updated_count += 1

    verified_count = sum(
        row["evidence_status"] == "VERIFIED"
        for row in rows
    )

    print("=== FINAM FUTURES DAILY COMMISSION LOAD V1 ===")
    print(f"input_file={input_path}")
    print(f"valid_row_count={len(rows)}")
    print(f"verified_row_count={verified_count}")
    print(f"unresolved_count={len(unresolved)}")
    print(f"inserted_count={inserted_count}")
    print(f"updated_count={updated_count}")

    for item in unresolved:
        print(f"UNRESOLVED={item}")

    print(
        "db_writes_performed="
        f"{1 if args.save and rows and not unresolved else 0}"
    )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if unresolved or not rows:
        print(
            "VERDICT="
            "FINAM_FUTURES_DAILY_COMMISSION_LOAD_V1_BLOCKED"
        )
        return 2

    if args.save:
        print(
            "VERDICT="
            "FINAM_FUTURES_DAILY_COMMISSION_LOAD_V1_READY"
        )
    else:
        print(
            "VERDICT="
            "FINAM_FUTURES_DAILY_COMMISSION_LOAD_V1_DRY_RUN_OK"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
