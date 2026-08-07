#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import pathlib
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence


SOURCE_VERSION = "FINAM_ACTUAL_COMMISSION_EVIDENCE_V1"

DEFAULT_INPUT = pathlib.Path(
    "config/research/finam_actual_commission_evidence_v1.tsv"
)
DEFAULT_OUTPUT = pathlib.Path(
    "/tmp/finam_actual_commission_evidence_v1"
)

TARGET_SYMBOL = "SBER@MISX"
TARGET_BREAK_EVEN_PER_SIDE = Decimal(
    "0.5058960347368421"
)

REQUIRED_COLUMNS = (
    "evidence_id",
    "account_tariff",
    "trade_date",
    "symbol",
    "market",
    "quantity_lots",
    "lot_size",
    "entry_turnover",
    "exit_turnover",
    "broker_commission_entry",
    "broker_commission_exit",
    "exchange_fee_entry",
    "exchange_fee_exit",
    "other_fee_entry",
    "other_fee_exit",
    "source_document",
    "source_row_reference",
)

MONEY_COLUMNS = (
    "entry_turnover",
    "exit_turnover",
    "broker_commission_entry",
    "broker_commission_exit",
    "exchange_fee_entry",
    "exchange_fee_exit",
    "other_fee_entry",
    "other_fee_exit",
)


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: str
    account_tariff: str
    trade_date: str
    symbol: str
    market: str
    quantity_lots: Decimal
    lot_size: Decimal
    entry_turnover: Decimal
    exit_turnover: Decimal
    broker_commission_entry: Decimal
    broker_commission_exit: Decimal
    exchange_fee_entry: Decimal
    exchange_fee_exit: Decimal
    other_fee_entry: Decimal
    other_fee_exit: Decimal
    source_document: str
    source_row_reference: str

    @property
    def quantity_units(self) -> Decimal:
        return self.quantity_lots * self.lot_size

    @property
    def broker_commission_total(self) -> Decimal:
        return (
            self.broker_commission_entry
            + self.broker_commission_exit
        )

    @property
    def exchange_fee_total(self) -> Decimal:
        return (
            self.exchange_fee_entry
            + self.exchange_fee_exit
        )

    @property
    def other_fee_total(self) -> Decimal:
        return self.other_fee_entry + self.other_fee_exit

    @property
    def round_trip_total_cost(self) -> Decimal:
        return (
            self.broker_commission_total
            + self.exchange_fee_total
            + self.other_fee_total
        )

    @property
    def effective_cost_per_side(self) -> Decimal:
        return self.round_trip_total_cost / Decimal("2")

    @property
    def total_turnover(self) -> Decimal:
        return self.entry_turnover + self.exit_turnover

    @property
    def effective_cost_rate(self) -> Decimal:
        if self.total_turnover <= 0:
            return Decimal("0")

        return (
            self.round_trip_total_cost
            / self.total_turnover
            * Decimal("100")
        )


def to_decimal(
    value: Any,
    *,
    field: str,
    evidence_id: str,
) -> Decimal:
    text = str(value or "").strip().replace(",", ".")

    if not text:
        raise ValueError(
            f"empty_decimal:{evidence_id}:{field}"
        )

    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError(
            f"invalid_decimal:{evidence_id}:{field}:{text}"
        ) from error


def write_tsv(
    path: pathlib.Path,
    fields: Sequence[str],
    rows: Iterable[Mapping[str, Any]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(fields),
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def load_evidence(
    path: pathlib.Path,
) -> tuple[list[Evidence], list[dict[str, str]]]:
    unresolved: list[dict[str, str]] = []
    evidence_rows: list[Evidence] = []

    if not path.is_file():
        unresolved.append(
            {
                "scope": "EVIDENCE_FILE",
                "identity": str(path),
                "reason": "FILE_MISSING",
            }
        )
        return evidence_rows, unresolved

    with path.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        reader = csv.DictReader(
            stream,
            delimiter="\t",
        )

        fieldnames = set(reader.fieldnames or [])
        missing_columns = sorted(
            set(REQUIRED_COLUMNS) - fieldnames
        )

        if missing_columns:
            unresolved.append(
                {
                    "scope": "EVIDENCE_SCHEMA",
                    "identity": str(path),
                    "reason": (
                        "REQUIRED_COLUMNS_MISSING:"
                        + ",".join(missing_columns)
                    ),
                }
            )
            return evidence_rows, unresolved

        seen_ids: set[str] = set()

        for row_number, row in enumerate(
            reader,
            start=2,
        ):
            if not any(
                str(value or "").strip()
                for value in row.values()
            ):
                continue

            evidence_id = str(
                row["evidence_id"] or ""
            ).strip()

            if not evidence_id:
                unresolved.append(
                    {
                        "scope": "EVIDENCE_ROW",
                        "identity": f"line:{row_number}",
                        "reason": "EVIDENCE_ID_MISSING",
                    }
                )
                continue

            if evidence_id in seen_ids:
                unresolved.append(
                    {
                        "scope": "EVIDENCE_ROW",
                        "identity": evidence_id,
                        "reason": "DUPLICATE_EVIDENCE_ID",
                    }
                )
                continue

            seen_ids.add(evidence_id)

            missing_text = [
                field
                for field in (
                    "account_tariff",
                    "trade_date",
                    "symbol",
                    "market",
                    "source_document",
                    "source_row_reference",
                )
                if not str(row[field] or "").strip()
            ]

            if missing_text:
                unresolved.append(
                    {
                        "scope": "EVIDENCE_ROW",
                        "identity": evidence_id,
                        "reason": (
                            "TEXT_FIELDS_MISSING:"
                            + ",".join(missing_text)
                        ),
                    }
                )
                continue

            try:
                values = {
                    field: to_decimal(
                        row[field],
                        field=field,
                        evidence_id=evidence_id,
                    )
                    for field in (
                        "quantity_lots",
                        "lot_size",
                        *MONEY_COLUMNS,
                    )
                }
            except ValueError as error:
                unresolved.append(
                    {
                        "scope": "EVIDENCE_ROW",
                        "identity": evidence_id,
                        "reason": str(error),
                    }
                )
                continue

            if values["quantity_lots"] <= 0:
                unresolved.append(
                    {
                        "scope": "EVIDENCE_ROW",
                        "identity": evidence_id,
                        "reason": (
                            "QUANTITY_LOTS_NOT_POSITIVE"
                        ),
                    }
                )
                continue

            if values["lot_size"] <= 0:
                unresolved.append(
                    {
                        "scope": "EVIDENCE_ROW",
                        "identity": evidence_id,
                        "reason": "LOT_SIZE_NOT_POSITIVE",
                    }
                )
                continue

            if (
                values["entry_turnover"] <= 0
                or values["exit_turnover"] <= 0
            ):
                unresolved.append(
                    {
                        "scope": "EVIDENCE_ROW",
                        "identity": evidence_id,
                        "reason": (
                            "TURNOVER_NOT_POSITIVE"
                        ),
                    }
                )
                continue

            negative_costs = [
                field
                for field in MONEY_COLUMNS
                if "turnover" not in field
                and values[field] < 0
            ]

            if negative_costs:
                unresolved.append(
                    {
                        "scope": "EVIDENCE_ROW",
                        "identity": evidence_id,
                        "reason": (
                            "NEGATIVE_COSTS:"
                            + ",".join(negative_costs)
                        ),
                    }
                )
                continue

            evidence_rows.append(
                Evidence(
                    evidence_id=evidence_id,
                    account_tariff=str(
                        row["account_tariff"]
                    ).strip(),
                    trade_date=str(
                        row["trade_date"]
                    ).strip(),
                    symbol=str(row["symbol"]).strip(),
                    market=str(row["market"]).strip(),
                    quantity_lots=values[
                        "quantity_lots"
                    ],
                    lot_size=values["lot_size"],
                    entry_turnover=values[
                        "entry_turnover"
                    ],
                    exit_turnover=values[
                        "exit_turnover"
                    ],
                    broker_commission_entry=values[
                        "broker_commission_entry"
                    ],
                    broker_commission_exit=values[
                        "broker_commission_exit"
                    ],
                    exchange_fee_entry=values[
                        "exchange_fee_entry"
                    ],
                    exchange_fee_exit=values[
                        "exchange_fee_exit"
                    ],
                    other_fee_entry=values[
                        "other_fee_entry"
                    ],
                    other_fee_exit=values[
                        "other_fee_exit"
                    ],
                    source_document=str(
                        row["source_document"]
                    ).strip(),
                    source_row_reference=str(
                        row["source_row_reference"]
                    ).strip(),
                )
            )

    return evidence_rows, unresolved


def normalized_rows(
    evidence: Sequence[Evidence],
) -> list[dict[str, Any]]:
    return [
        {
            "evidence_id": row.evidence_id,
            "account_tariff": row.account_tariff,
            "trade_date": row.trade_date,
            "symbol": row.symbol,
            "market": row.market,
            "quantity_lots": row.quantity_lots,
            "lot_size": row.lot_size,
            "quantity_units": row.quantity_units,
            "entry_turnover": row.entry_turnover,
            "exit_turnover": row.exit_turnover,
            "total_turnover": row.total_turnover,
            "broker_commission_total": (
                row.broker_commission_total
            ),
            "exchange_fee_total": (
                row.exchange_fee_total
            ),
            "other_fee_total": row.other_fee_total,
            "round_trip_total_cost": (
                row.round_trip_total_cost
            ),
            "effective_cost_per_side": (
                row.effective_cost_per_side
            ),
            "effective_cost_rate_percent": (
                row.effective_cost_rate
            ),
            "source_document": row.source_document,
            "source_row_reference": (
                row.source_row_reference
            ),
        }
        for row in evidence
    ]


def instrument_summary(
    evidence: Sequence[Evidence],
) -> list[dict[str, Any]]:
    groups: dict[
        tuple[str, str, str],
        list[Evidence],
    ] = defaultdict(list)

    for row in evidence:
        groups[
            (
                row.account_tariff,
                row.symbol,
                row.market,
            )
        ].append(row)

    summaries: list[dict[str, Any]] = []

    for key, rows in sorted(groups.items()):
        total_turnover = sum(
            (
                row.total_turnover
                for row in rows
            ),
            Decimal("0"),
        )
        total_cost = sum(
            (
                row.round_trip_total_cost
                for row in rows
            ),
            Decimal("0"),
        )
        trade_count = len(rows)

        summaries.append(
            {
                "account_tariff": key[0],
                "symbol": key[1],
                "market": key[2],
                "evidence_count": trade_count,
                "total_turnover": total_turnover,
                "total_cost": total_cost,
                "average_round_trip_cost": (
                    total_cost / Decimal(trade_count)
                ),
                "average_cost_per_side": (
                    total_cost
                    / Decimal(trade_count)
                    / Decimal("2")
                ),
                "weighted_cost_rate_percent": (
                    total_cost
                    / total_turnover
                    * Decimal("100")
                    if total_turnover > 0
                    else Decimal("0")
                ),
                "minimum_round_trip_cost": min(
                    row.round_trip_total_cost
                    for row in rows
                ),
                "maximum_round_trip_cost": max(
                    row.round_trip_total_cost
                    for row in rows
                ),
            }
        )

    return summaries


def break_even_rows(
    summaries: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []

    for row in summaries:
        average_per_side = Decimal(
            str(row["average_cost_per_side"])
        )

        if row["symbol"] != TARGET_SYMBOL:
            status = "OUTSIDE_TARGET_SYMBOL"
        elif (
            average_per_side
            <= TARGET_BREAK_EVEN_PER_SIDE
        ):
            status = "WITHIN_BREAK_EVEN"
        else:
            status = "ABOVE_BREAK_EVEN"

        output.append(
            {
                **row,
                "target_break_even_per_side": (
                    TARGET_BREAK_EVEN_PER_SIDE
                ),
                "cost_headroom_per_side": (
                    TARGET_BREAK_EVEN_PER_SIDE
                    - average_per_side
                ),
                "break_even_status": status,
            }
        )

    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Finam Actual Commission Evidence V1"
        )
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_path = pathlib.Path(args.input)
    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    evidence, unresolved = load_evidence(input_path)

    normalized = normalized_rows(evidence)
    summaries = instrument_summary(evidence)
    comparisons = break_even_rows(summaries)

    write_tsv(
        output_dir / "normalized_evidence.tsv",
        (
            "evidence_id",
            "account_tariff",
            "trade_date",
            "symbol",
            "market",
            "quantity_lots",
            "lot_size",
            "quantity_units",
            "entry_turnover",
            "exit_turnover",
            "total_turnover",
            "broker_commission_total",
            "exchange_fee_total",
            "other_fee_total",
            "round_trip_total_cost",
            "effective_cost_per_side",
            "effective_cost_rate_percent",
            "source_document",
            "source_row_reference",
        ),
        normalized,
    )

    write_tsv(
        output_dir / "instrument_summary.tsv",
        (
            "account_tariff",
            "symbol",
            "market",
            "evidence_count",
            "total_turnover",
            "total_cost",
            "average_round_trip_cost",
            "average_cost_per_side",
            "weighted_cost_rate_percent",
            "minimum_round_trip_cost",
            "maximum_round_trip_cost",
        ),
        summaries,
    )

    write_tsv(
        output_dir / "break_even_comparison.tsv",
        (
            "account_tariff",
            "symbol",
            "market",
            "evidence_count",
            "average_round_trip_cost",
            "average_cost_per_side",
            "target_break_even_per_side",
            "cost_headroom_per_side",
            "break_even_status",
        ),
        comparisons,
    )

    if not evidence:
        unresolved.append(
            {
                "scope": "ACTUAL_COMMISSION_EVIDENCE",
                "identity": str(input_path),
                "reason": "NO_VALID_EVIDENCE_ROWS",
            }
        )

    target_rows = [
        row
        for row in comparisons
        if row["symbol"] == TARGET_SYMBOL
    ]

    if not target_rows:
        unresolved.append(
            {
                "scope": "TARGET_SYMBOL",
                "identity": TARGET_SYMBOL,
                "reason": (
                    "TARGET_SYMBOL_EVIDENCE_MISSING"
                ),
            }
        )

    target_within_break_even = sum(
        row["break_even_status"]
        == "WITHIN_BREAK_EVEN"
        for row in target_rows
    )

    tariff_names = sorted(
        {
            row.account_tariff
            for row in evidence
        }
    )

    source_documents = sorted(
        {
            row.source_document
            for row in evidence
        }
    )

    write_tsv(
        output_dir / "unresolved.tsv",
        ("scope", "identity", "reason"),
        unresolved,
    )

    contract_lines = (
        "FINAM ACTUAL COMMISSION EVIDENCE V1",
        "===================================",
        "",
        f"INPUT_FILE={input_path}",
        f"EVIDENCE_ROW_COUNT={len(evidence)}",
        f"TARIFF_COUNT={len(tariff_names)}",
        f"SOURCE_DOCUMENT_COUNT={len(source_documents)}",
        f"TARGET_SYMBOL={TARGET_SYMBOL}",
        f"TARGET_EVIDENCE_GROUP_COUNT={len(target_rows)}",
        (
            "TARGET_WITHIN_BREAK_EVEN_COUNT="
            f"{target_within_break_even}"
        ),
        (
            "TARGET_BREAK_EVEN_PER_SIDE="
            f"{TARGET_BREAK_EVEN_PER_SIDE}"
        ),
        f"UNRESOLVED_COUNT={len(unresolved)}",
        (
            "EXTERNAL_TARIFF_VERIFIED="
            f"{int(bool(evidence) and not unresolved)}"
        ),
        "DATABASE=POSTGRESQL_ONLY",
        "DB_WRITES_PERFORMED=0",
        "STRATEGY_CHANGED=0",
        "RISK_ENGINE_CHANGED=0",
        "RUNTIME_CHANGED=0",
        "EXECUTION_CHANGED=0",
        "ORDERS_CHANGED=0",
        "FILLS_CHANGED=0",
        "OOS_ALLOWED=0",
        "SHADOW_ALLOWED=0",
        "PAPER_ALLOWED=0",
        "MICRO_LIVE_ALLOWED=0",
    )

    (output_dir / "contract.txt").write_text(
        "\n".join(contract_lines) + "\n",
        encoding="utf-8",
    )

    print("=== FINAM ACTUAL COMMISSION EVIDENCE V1 ===")
    print(f"input_file={input_path}")
    print(f"evidence_row_count={len(evidence)}")
    print(f"tariff_count={len(tariff_names)}")
    print(
        f"source_document_count="
        f"{len(source_documents)}"
    )
    print(
        f"target_evidence_group_count="
        f"{len(target_rows)}"
    )
    print(
        "target_within_break_even_count="
        f"{target_within_break_even}"
    )
    print(f"unresolved_count={len(unresolved)}")
    print(
        "external_tariff_verified="
        f"{int(bool(evidence) and not unresolved)}"
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
    print(
        "VERDICT="
        "FINAM_ACTUAL_COMMISSION_EVIDENCE_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
