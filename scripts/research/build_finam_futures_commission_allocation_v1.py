#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import pathlib
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


SOURCE_VERSION = "FINAM_FUTURES_COMMISSION_ALLOCATION_V1"


@dataclass(frozen=True, slots=True)
class DailyEvidence:
    trade_date: str
    broker_account: str
    commission_total: Decimal
    currency_code: str
    source_document: str
    source_reference: str
    source_version: str
    evidence_status: str


@dataclass(frozen=True, slots=True)
class AttributionException:
    trade_date: str
    broker_account: str
    commission_total: Decimal
    currency_code: str
    attribution_status: str
    reason: str
    source_document: str
    source_reference: str


def attribution_identity(
    *,
    trade_date: str,
    broker_account: str,
    commission_total: Decimal,
    currency_code: str,
    source_document: str,
    source_reference: str,
) -> tuple[str, str, Decimal, str, str, str]:
    return (
        trade_date,
        broker_account,
        commission_total,
        currency_code,
        source_document,
        source_reference,
    )


def load_attribution_exceptions(
    path: pathlib.Path,
) -> list[AttributionException]:
    rows: list[AttributionException] = []
    seen: set[
        tuple[str, str, Decimal, str, str, str]
    ] = set()

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream, delimiter="\t")

        required = {
            "trade_date",
            "broker_account",
            "commission_total",
            "currency_code",
            "attribution_status",
            "reason",
            "source_document",
            "source_reference",
        }

        missing = required - set(reader.fieldnames or [])

        if missing:
            raise RuntimeError(
                "attribution_exception_columns_missing:"
                + ",".join(sorted(missing))
            )

        for line_number, row in enumerate(reader, start=2):
            try:
                commission_total = Decimal(
                    str(row["commission_total"]).replace(",", ".")
                )
            except InvalidOperation as error:
                raise RuntimeError(
                    "invalid_attribution_exception_commission:"
                    f"line:{line_number}"
                ) from error

            if commission_total <= 0:
                raise RuntimeError(
                    "attribution_exception_commission_not_positive:"
                    f"line:{line_number}"
                )

            attribution_status = str(
                row["attribution_status"]
            ).strip().upper()

            if attribution_status != "UNATTRIBUTABLE_NO_FILLS":
                raise RuntimeError(
                    "invalid_attribution_exception_status:"
                    f"line:{line_number}"
                )

            reason = str(row["reason"]).strip()

            if not reason:
                raise RuntimeError(
                    "attribution_exception_reason_missing:"
                    f"line:{line_number}"
                )

            item = AttributionException(
                trade_date=str(row["trade_date"]).strip(),
                broker_account=str(
                    row["broker_account"]
                ).strip(),
                commission_total=commission_total,
                currency_code=str(
                    row["currency_code"]
                ).strip(),
                attribution_status=attribution_status,
                reason=reason,
                source_document=str(
                    row["source_document"]
                ).strip(),
                source_reference=str(
                    row["source_reference"]
                ).strip(),
            )

            identity = attribution_identity(
                trade_date=item.trade_date,
                broker_account=item.broker_account,
                commission_total=item.commission_total,
                currency_code=item.currency_code,
                source_document=item.source_document,
                source_reference=item.source_reference,
            )

            if identity in seen:
                raise RuntimeError(
                    "duplicate_attribution_exception:"
                    f"line:{line_number}"
                )

            seen.add(identity)
            rows.append(item)

    return rows


def dec(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def load_evidence(path: pathlib.Path) -> list[DailyEvidence]:
    rows: list[DailyEvidence] = []
    seen: set[tuple[str, str, str]] = set()

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        reader = csv.DictReader(stream, delimiter="\t")

        required = {
            "trade_date",
            "broker_account",
            "commission_total",
            "currency_code",
            "source_document",
            "source_reference",
            "source_version",
            "evidence_status",
        }

        missing = required - set(reader.fieldnames or [])

        if missing:
            raise RuntimeError(
                "evidence_columns_missing:"
                + ",".join(sorted(missing))
            )

        for line_number, row in enumerate(reader, start=2):
            try:
                commission = Decimal(
                    str(row["commission_total"]).replace(",", ".")
                )
            except InvalidOperation as error:
                raise RuntimeError(
                    f"invalid_commission:line:{line_number}"
                ) from error

            if commission <= 0:
                raise RuntimeError(
                    f"commission_not_positive:line:{line_number}"
                )

            evidence_status = str(
                row["evidence_status"]
            ).strip().upper()

            if evidence_status not in {
                "VERIFIED",
                "REVIEW_REQUIRED",
            }:
                raise RuntimeError(
                    f"invalid_evidence_status:line:{line_number}"
                )

            identity = (
                str(row["trade_date"]),
                str(row["broker_account"]),
                str(row["source_version"]),
            )

            if identity in seen:
                raise RuntimeError(
                    f"duplicate_evidence_identity:{identity}"
                )

            seen.add(identity)

            rows.append(
                DailyEvidence(
                    trade_date=str(row["trade_date"]),
                    broker_account=str(
                        row["broker_account"]
                    ),
                    commission_total=commission,
                    currency_code=str(
                        row["currency_code"]
                    ),
                    source_document=str(
                        row["source_document"]
                    ),
                    source_reference=str(
                        row["source_reference"]
                    ),
                    source_version=str(
                        row["source_version"]
                    ),
                    evidence_status=evidence_status,
                )
            )

    if not rows:
        raise RuntimeError("daily_commission_evidence_empty")

    return rows


def validate_identifier(
    cursor: RealDictCursor,
    *,
    schema_name: str,
    table_name: str,
    required_columns: tuple[str, ...],
) -> None:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        """,
        (schema_name, table_name),
    )

    available = {
        str(row["column_name"])
        for row in cursor.fetchall()
    }

    missing = sorted(set(required_columns) - available)

    if missing:
        raise RuntimeError(
            "fills_columns_missing:"
            + ",".join(missing)
        )


def load_daily_fills(
    cursor: RealDictCursor,
    *,
    evidence: DailyEvidence,
    schema_name: str,
    table_name: str,
    timestamp_column: str,
    symbol_column: str,
    quantity_column: str,
    price_column: str,
    futures_symbol_pattern: str,
) -> list[dict[str, Any]]:
    query = sql.SQL(
        """
        SELECT
            {symbol_column}::text AS symbol,
            sum(abs({quantity_column}))::numeric
                AS executed_contracts,
            sum(
                abs({quantity_column}) * abs({price_column})
            )::numeric AS turnover
        FROM {schema_name}.{table_name}
        WHERE {timestamp_column} >= %s::date
          AND {timestamp_column} < %s::date + interval '1 day'
          AND {symbol_column}::text LIKE %s
        GROUP BY {symbol_column}
        ORDER BY {symbol_column}
        """
    ).format(
        symbol_column=sql.Identifier(symbol_column),
        quantity_column=sql.Identifier(quantity_column),
        price_column=sql.Identifier(price_column),
        timestamp_column=sql.Identifier(timestamp_column),
        schema_name=sql.Identifier(schema_name),
        table_name=sql.Identifier(table_name),
    )

    cursor.execute(
        query,
        (
            evidence.trade_date,
            evidence.trade_date,
            futures_symbol_pattern,
        ),
    )

    return [
        dict(row)
        for row in cursor.fetchall()
        if dec(row["executed_contracts"]) > 0
    ]


def calculate_allocations(
    *,
    evidence: DailyEvidence,
    fills: list[dict[str, Any]],
    allocation_model: str,
) -> list[dict[str, Any]]:
    if not fills:
        raise RuntimeError(
            f"daily_fills_missing:{evidence.trade_date}"
        )

    if allocation_model == "CONTRACT_COUNT":
        basis_name = "executed_contracts"
    elif allocation_model == "TURNOVER":
        basis_name = "turnover"
    else:
        raise RuntimeError(
            f"unsupported_allocation_model:{allocation_model}"
        )

    basis_total = sum(
        (
            dec(row[basis_name])
            for row in fills
        ),
        Decimal("0"),
    )

    if basis_total <= 0:
        raise RuntimeError(
            f"allocation_basis_not_positive:"
            f"{evidence.trade_date}:{allocation_model}"
        )

    allocations: list[dict[str, Any]] = []

    for row in fills:
        contracts = dec(row["executed_contracts"])
        turnover = dec(row["turnover"])
        basis = dec(row[basis_name])
        weight = basis / basis_total

        allocated = (
            evidence.commission_total * weight
        )

        commission_per_contract = (
            allocated / contracts
        )

        allocations.append(
            {
                "trade_date": evidence.trade_date,
                "broker_account": evidence.broker_account,
                "allocation_model": allocation_model,
                "symbol": str(row["symbol"]),
                "executed_contracts": contracts,
                "turnover": turnover,
                "allocation_basis_value": basis,
                "allocation_weight": weight,
                "daily_commission_total": (
                    evidence.commission_total
                ),
                "allocated_commission": allocated,
                "commission_per_contract": (
                    commission_per_contract
                ),
                "source_document": (
                    evidence.source_document
                ),
                "source_reference": (
                    evidence.source_reference
                ),
                "source_version": (
                    evidence.source_version
                ),
                "evidence_status": (
                    evidence.evidence_status
                ),
            }
        )

    allocated_total = sum(
        (
            row["allocated_commission"]
            for row in allocations
        ),
        Decimal("0"),
    )

    delta = abs(
        allocated_total - evidence.commission_total
    )

    if delta > Decimal("0.000001"):
        raise RuntimeError(
            f"allocation_reconciliation_failed:"
            f"{evidence.trade_date}:{allocation_model}:{delta}"
        )

    return allocations


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Finam Futures Commission Allocation V1"
        )
    )
    parser.add_argument(
        "--evidence-file",
        default=(
            "config/research/"
            "finam_futures_daily_commission_v1.tsv"
        ),
    )
    parser.add_argument(
        "--attribution-exceptions-file",
        default=(
            "config/research/"
            "finam_futures_commission_attribution_exceptions_v1.tsv"
        ),
    )
    parser.add_argument("--fills-schema", required=True)
    parser.add_argument("--fills-table", required=True)
    parser.add_argument("--timestamp-column", required=True)
    parser.add_argument("--symbol-column", required=True)
    parser.add_argument("--quantity-column", required=True)
    parser.add_argument("--price-column", required=True)
    parser.add_argument(
        "--futures-symbol-pattern",
        default="%@RTSX",
    )
    parser.add_argument(
        "--allocation-model",
        choices=("CONTRACT_COUNT", "TURNOVER", "ALL"),
        default="ALL",
    )
    parser.add_argument("--batch-id", required=True)
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    evidence_rows = load_evidence(
        pathlib.Path(args.evidence_file)
    )
    attribution_exceptions = load_attribution_exceptions(
        pathlib.Path(args.attribution_exceptions_file)
    )

    evidence_identities = {
        attribution_identity(
            trade_date=row.trade_date,
            broker_account=row.broker_account,
            commission_total=row.commission_total,
            currency_code=row.currency_code,
            source_document=row.source_document,
            source_reference=row.source_reference,
        )
        for row in evidence_rows
    }

    exception_by_identity = {
        attribution_identity(
            trade_date=row.trade_date,
            broker_account=row.broker_account,
            commission_total=row.commission_total,
            currency_code=row.currency_code,
            source_document=row.source_document,
            source_reference=row.source_reference,
        ): row
        for row in attribution_exceptions
    }

    orphan_exception_identities = (
        set(exception_by_identity) - evidence_identities
    )

    if orphan_exception_identities:
        raise RuntimeError(
            "attribution_exception_without_evidence:"
            f"count={len(orphan_exception_identities)}"
        )

    models = (
        ("CONTRACT_COUNT", "TURNOVER")
        if args.allocation_model == "ALL"
        else (args.allocation_model,)
    )

    all_allocations: list[dict[str, Any]] = []
    unresolved: list[str] = []
    excluded_from_allocation: list[str] = []

    source_fills_table = (
        f"{args.fills_schema}.{args.fills_table}"
    )

    with psycopg2.connect(build_psycopg_url()) as conn:
        if not args.save:
            conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            validate_identifier(
                cursor,
                schema_name=args.fills_schema,
                table_name=args.fills_table,
                required_columns=(
                    args.timestamp_column,
                    args.symbol_column,
                    args.quantity_column,
                    args.price_column,
                ),
            )

            for evidence in evidence_rows:
                fills = load_daily_fills(
                    cursor,
                    evidence=evidence,
                    schema_name=args.fills_schema,
                    table_name=args.fills_table,
                    timestamp_column=args.timestamp_column,
                    symbol_column=args.symbol_column,
                    quantity_column=args.quantity_column,
                    price_column=args.price_column,
                    futures_symbol_pattern=(
                        args.futures_symbol_pattern
                    ),
                )

                if not fills:
                    identity = attribution_identity(
                        trade_date=evidence.trade_date,
                        broker_account=evidence.broker_account,
                        commission_total=evidence.commission_total,
                        currency_code=evidence.currency_code,
                        source_document=evidence.source_document,
                        source_reference=evidence.source_reference,
                    )
                    exception = exception_by_identity.get(identity)

                    if exception is not None:
                        excluded_from_allocation.append(
                            "UNATTRIBUTABLE_NO_FILLS:"
                            f"{evidence.trade_date}:"
                            f"{evidence.broker_account}:"
                            f"{evidence.commission_total}:"
                            f"{exception.reason}"
                        )
                        continue

                    unresolved.append(
                        "DAILY_FILLS_MISSING:"
                        f"{evidence.trade_date}"
                    )
                    continue

                if args.save:
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
                            %s::date,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
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
                        """,
                        (
                            evidence.trade_date,
                            evidence.broker_account,
                            evidence.commission_total,
                            evidence.currency_code,
                            evidence.source_document,
                            evidence.source_reference,
                            evidence.source_version,
                            evidence.evidence_status,
                        ),
                    )

                for model in models:
                    allocations = calculate_allocations(
                        evidence=evidence,
                        fills=fills,
                        allocation_model=model,
                    )

                    all_allocations.extend(allocations)

                    if args.save:
                        for row in allocations:
                            cursor.execute(
                                """
                                INSERT INTO
                                  analytics.futures_commission_allocation_v1 (
                                    allocation_batch_id,
                                    trade_date,
                                    broker_account,
                                    allocation_model,
                                    symbol,
                                    executed_contracts,
                                    turnover,
                                    allocation_basis_value,
                                    allocation_weight,
                                    daily_commission_total,
                                    allocated_commission,
                                    commission_per_contract,
                                    source_fills_table,
                                    source_document,
                                    source_reference,
                                    source_version,
                                    evidence_status
                                  )
                                VALUES (
                                    %s,
                                    %s::date,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s,
                                    %s
                                )
                                ON CONFLICT (
                                    allocation_batch_id,
                                    trade_date,
                                    allocation_model,
                                    symbol
                                )
                                DO UPDATE SET
                                    executed_contracts =
                                        EXCLUDED.executed_contracts,
                                    turnover =
                                        EXCLUDED.turnover,
                                    allocation_basis_value =
                                        EXCLUDED.allocation_basis_value,
                                    allocation_weight =
                                        EXCLUDED.allocation_weight,
                                    daily_commission_total =
                                        EXCLUDED.daily_commission_total,
                                    allocated_commission =
                                        EXCLUDED.allocated_commission,
                                    commission_per_contract =
                                        EXCLUDED.commission_per_contract,
                                    source_fills_table =
                                        EXCLUDED.source_fills_table,
                                    source_document =
                                        EXCLUDED.source_document,
                                    source_reference =
                                        EXCLUDED.source_reference,
                                    source_version =
                                        EXCLUDED.source_version,
                                    evidence_status =
                                        EXCLUDED.evidence_status
                                """,
                                (
                                    args.batch_id,
                                    row["trade_date"],
                                    row["broker_account"],
                                    row["allocation_model"],
                                    row["symbol"],
                                    row["executed_contracts"],
                                    row["turnover"],
                                    row[
                                        "allocation_basis_value"
                                    ],
                                    row["allocation_weight"],
                                    row[
                                        "daily_commission_total"
                                    ],
                                    row[
                                        "allocated_commission"
                                    ],
                                    row[
                                        "commission_per_contract"
                                    ],
                                    source_fills_table,
                                    row["source_document"],
                                    row["source_reference"],
                                    row["source_version"],
                                    row["evidence_status"],
                                ),
                            )

    day_count = len(
        {
            row["trade_date"]
            for row in all_allocations
        }
    )
    symbol_count = len(
        {
            row["symbol"]
            for row in all_allocations
        }
    )

    print("=== FINAM FUTURES COMMISSION ALLOCATION V1 ===")
    print(f"allocation_batch_id={args.batch_id}")
    print(f"source_fills_table={source_fills_table}")
    print(f"evidence_day_count={len(evidence_rows)}")
    print(f"allocated_day_count={day_count}")
    print(
        "excluded_day_count="
        f"{len(excluded_from_allocation)}"
    )
    print(f"allocation_row_count={len(all_allocations)}")
    print(f"symbol_count={symbol_count}")
    print(f"allocation_models={','.join(models)}")
    print(f"unresolved_count={len(unresolved)}")

    for item in excluded_from_allocation:
        print(f"EXCLUDED_FROM_ALLOCATION={item}")

    for item in unresolved:
        print(f"UNRESOLVED={item}")

    for row in all_allocations[:40]:
        print(
            "ALLOCATION "
            f"date={row['trade_date']} "
            f"model={row['allocation_model']} "
            f"symbol={row['symbol']} "
            f"contracts={row['executed_contracts']} "
            f"weight={row['allocation_weight']} "
            f"allocated={row['allocated_commission']} "
            f"per_contract="
            f"{row['commission_per_contract']}"
        )

    print(
        f"db_writes_performed="
        f"{1 if args.save else 0}"
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
            "FINAM_FUTURES_COMMISSION_ALLOCATION_V1_BLOCKED"
        )
        return 2

    print(
        "VERDICT="
        "FINAM_FUTURES_COMMISSION_ALLOCATION_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
