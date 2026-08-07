#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import pathlib
from decimal import Decimal, InvalidOperation
from typing import Any


SOURCE_VERSION = "FINAM_ACTUAL_COMMISSION_SIDE_EVIDENCE_V1"

DEFAULT_INPUT = pathlib.Path(
    "config/research/finam_actual_commission_side_evidence_v1.tsv"
)

DEFAULT_OUTPUT = pathlib.Path(
    "/tmp/finam_actual_commission_side_evidence_v1"
)

TARGET_SYMBOL = "SBERP@MISX"

# Предельная комиссия лучшего исследовательского запуска SBER.
TARGET_BREAK_EVEN_PER_SIDE = Decimal(
    "0.5058960347368421"
)

REQUIRED_COLUMNS = (
    "evidence_id",
    "trade_date",
    "symbol",
    "market",
    "side",
    "quantity_units",
    "lot_size",
    "turnover",
    "broker_order_fee",
    "settlement_fee",
    "exchange_fee",
    "other_fee",
    "source_document",
    "source_reference",
)


def to_decimal(
    value: Any,
    *,
    field: str,
    evidence_id: str,
) -> Decimal:
    text = str(value or "").strip().replace(",", ".")

    try:
        return Decimal(text)
    except InvalidOperation as error:
        raise ValueError(
            f"invalid_decimal:{evidence_id}:{field}:{text}"
        ) from error


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finam Actual Commission Side Evidence V1"
    )
    parser.add_argument(
        "--input",
        default=str(DEFAULT_INPUT),
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
    )
    args = parser.parse_args()

    input_path = pathlib.Path(args.input)
    output_dir = pathlib.Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, str]] = []
    normalized: list[dict[str, Any]] = []

    if not input_path.is_file():
        unresolved.append(
            {
                "scope": "EVIDENCE_FILE",
                "identity": str(input_path),
                "reason": "FILE_MISSING",
            }
        )
    else:
        with input_path.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as stream:
            reader = csv.DictReader(
                stream,
                delimiter="\t",
            )

            columns = set(reader.fieldnames or [])
            missing = sorted(
                set(REQUIRED_COLUMNS) - columns
            )

            if missing:
                unresolved.append(
                    {
                        "scope": "EVIDENCE_SCHEMA",
                        "identity": str(input_path),
                        "reason": (
                            "MISSING_COLUMNS:"
                            + ",".join(missing)
                        ),
                    }
                )
            else:
                seen_ids: set[str] = set()

                for line_no, row in enumerate(
                    reader,
                    start=2,
                ):
                    evidence_id = str(
                        row["evidence_id"] or ""
                    ).strip()

                    if not evidence_id:
                        unresolved.append(
                            {
                                "scope": "EVIDENCE_ROW",
                                "identity": f"line:{line_no}",
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

                    side = str(row["side"]).strip().upper()

                    if side not in {"BUY", "SELL"}:
                        unresolved.append(
                            {
                                "scope": "EVIDENCE_ROW",
                                "identity": evidence_id,
                                "reason": f"INVALID_SIDE:{side}",
                            }
                        )
                        continue

                    try:
                        quantity_units = to_decimal(
                            row["quantity_units"],
                            field="quantity_units",
                            evidence_id=evidence_id,
                        )
                        lot_size = to_decimal(
                            row["lot_size"],
                            field="lot_size",
                            evidence_id=evidence_id,
                        )
                        turnover = to_decimal(
                            row["turnover"],
                            field="turnover",
                            evidence_id=evidence_id,
                        )
                        broker_order_fee = to_decimal(
                            row["broker_order_fee"],
                            field="broker_order_fee",
                            evidence_id=evidence_id,
                        )
                        settlement_fee = to_decimal(
                            row["settlement_fee"],
                            field="settlement_fee",
                            evidence_id=evidence_id,
                        )
                        exchange_fee = to_decimal(
                            row["exchange_fee"],
                            field="exchange_fee",
                            evidence_id=evidence_id,
                        )
                        other_fee = to_decimal(
                            row["other_fee"],
                            field="other_fee",
                            evidence_id=evidence_id,
                        )
                    except ValueError as error:
                        unresolved.append(
                            {
                                "scope": "EVIDENCE_ROW",
                                "identity": evidence_id,
                                "reason": str(error),
                            }
                        )
                        continue

                    if (
                        quantity_units <= 0
                        or lot_size <= 0
                        or turnover <= 0
                    ):
                        unresolved.append(
                            {
                                "scope": "EVIDENCE_ROW",
                                "identity": evidence_id,
                                "reason": "NON_POSITIVE_TRADE_VALUE",
                            }
                        )
                        continue

                    if min(
                        broker_order_fee,
                        settlement_fee,
                        exchange_fee,
                        other_fee,
                    ) < 0:
                        unresolved.append(
                            {
                                "scope": "EVIDENCE_ROW",
                                "identity": evidence_id,
                                "reason": "NEGATIVE_FEE",
                            }
                        )
                        continue

                    total_fee = (
                        broker_order_fee
                        + settlement_fee
                        + exchange_fee
                        + other_fee
                    )

                    effective_rate = (
                        total_fee
                        / turnover
                        * Decimal("100")
                    )

                    settlement_rate = (
                        settlement_fee
                        / turnover
                        * Decimal("100")
                    )

                    break_even_status = (
                        "WITHIN_BREAK_EVEN"
                        if total_fee
                        <= TARGET_BREAK_EVEN_PER_SIDE
                        else "ABOVE_BREAK_EVEN"
                    )

                    normalized.append(
                        {
                            "evidence_id": evidence_id,
                            "trade_date": row["trade_date"],
                            "symbol": row["symbol"],
                            "market": row["market"],
                            "side": side,
                            "quantity_units": quantity_units,
                            "lot_size": lot_size,
                            "turnover": turnover,
                            "broker_order_fee": (
                                broker_order_fee
                            ),
                            "settlement_fee": settlement_fee,
                            "exchange_fee": exchange_fee,
                            "other_fee": other_fee,
                            "total_fee_per_side": total_fee,
                            "effective_fee_rate_percent": (
                                effective_rate
                            ),
                            "settlement_rate_percent": (
                                settlement_rate
                            ),
                            "break_even_per_side": (
                                TARGET_BREAK_EVEN_PER_SIDE
                            ),
                            "break_even_headroom": (
                                TARGET_BREAK_EVEN_PER_SIDE
                                - total_fee
                            ),
                            "break_even_status": (
                                break_even_status
                            ),
                            "source_document": (
                                row["source_document"]
                            ),
                            "source_reference": (
                                row["source_reference"]
                            ),
                        }
                    )

    fields = (
        "evidence_id",
        "trade_date",
        "symbol",
        "market",
        "side",
        "quantity_units",
        "lot_size",
        "turnover",
        "broker_order_fee",
        "settlement_fee",
        "exchange_fee",
        "other_fee",
        "total_fee_per_side",
        "effective_fee_rate_percent",
        "settlement_rate_percent",
        "break_even_per_side",
        "break_even_headroom",
        "break_even_status",
        "source_document",
        "source_reference",
    )

    write_tsv(
        output_dir / "normalized_side_evidence.tsv",
        fields,
        normalized,
    )

    write_tsv(
        output_dir / "unresolved.tsv",
        ("scope", "identity", "reason"),
        unresolved,
    )

    target_rows = [
        row
        for row in normalized
        if row["symbol"] == TARGET_SYMBOL
    ]

    target_within_break_even = sum(
        row["break_even_status"] == "WITHIN_BREAK_EVEN"
        for row in target_rows
    )

    target_average_fee = (
        sum(
            (
                Decimal(str(row["total_fee_per_side"]))
                for row in target_rows
            ),
            Decimal("0"),
        )
        / Decimal(len(target_rows))
        if target_rows
        else Decimal("0")
    )

    contract = (
        "FINAM ACTUAL COMMISSION SIDE EVIDENCE V1",
        "========================================",
        "",
        f"INPUT_FILE={input_path}",
        f"EVIDENCE_ROW_COUNT={len(normalized)}",
        f"TARGET_SYMBOL={TARGET_SYMBOL}",
        f"TARGET_EVIDENCE_ROW_COUNT={len(target_rows)}",
        (
            "TARGET_AVERAGE_FEE_PER_SIDE="
            f"{target_average_fee}"
        ),
        (
            "TARGET_BREAK_EVEN_PER_SIDE="
            f"{TARGET_BREAK_EVEN_PER_SIDE}"
        ),
        (
            "TARGET_WITHIN_BREAK_EVEN_COUNT="
            f"{target_within_break_even}"
        ),
        f"UNRESOLVED_COUNT={len(unresolved)}",
        (
            "ACTUAL_COMMISSION_EVIDENCE_VERIFIED="
            f"{int(bool(target_rows) and not unresolved)}"
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
        "\n".join(contract) + "\n",
        encoding="utf-8",
    )

    print("=== FINAM ACTUAL COMMISSION SIDE EVIDENCE V1 ===")
    print(f"evidence_row_count={len(normalized)}")
    print(f"target_evidence_row_count={len(target_rows)}")
    print(
        f"target_average_fee_per_side="
        f"{target_average_fee}"
    )
    print(
        f"target_break_even_per_side="
        f"{TARGET_BREAK_EVEN_PER_SIDE}"
    )
    print(
        f"target_within_break_even_count="
        f"{target_within_break_even}"
    )
    print(f"unresolved_count={len(unresolved)}")
    print(
        "actual_commission_evidence_verified="
        f"{int(bool(target_rows) and not unresolved)}"
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
        "FINAM_ACTUAL_COMMISSION_SIDE_EVIDENCE_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
