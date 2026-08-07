#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import pathlib
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


OUTPUT_ROOT = pathlib.Path(
    "/tmp/finam_commission_contract_verification_v1"
)

TARGET_STRATEGY = "MEAN_REVERSION_ZSCORE_V1"
TARGET_SYMBOL = "SBER@MISX"
TARGET_TIMEFRAME = "M5"


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


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


def parse_parameters(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if isinstance(value, str):
        return dict(json.loads(value))

    return {}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finam Commission Contract Verification V1"
    )
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    output_dir = OUTPUT_ROOT / args.batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                SELECT
                    r.run_uuid::text,
                    r.parameter_hash,
                    r.parameter_json,
                    count(*)::bigint AS trades,
                    avg(t.commission)::numeric
                        AS stored_round_trip_commission,
                    avg(t.slippage)::numeric
                        AS stored_slippage_per_trade,
                    avg(t.net_pnl + t.commission)::numeric
                        AS execution_expectancy,
                    avg(t.net_pnl)::numeric
                        AS net_expectancy
                FROM analytics.edge_lab_run_v1 r
                JOIN analytics.research_trade_v1 t
                  ON t.run_uuid = r.run_uuid
                WHERE r.research_batch_id = %s
                  AND r.strategy_code = %s
                  AND r.symbol = %s
                  AND r.timeframe = %s
                GROUP BY
                    r.run_uuid,
                    r.parameter_hash,
                    r.parameter_json
                ORDER BY
                    execution_expectancy DESC
                """,
                (
                    args.batch_id,
                    TARGET_STRATEGY,
                    TARGET_SYMBOL,
                    TARGET_TIMEFRAME,
                ),
            )

            source_rows = [
                dict(row)
                for row in cur.fetchall()
            ]

    rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

    for rank, row in enumerate(source_rows, start=1):
        parameters = parse_parameters(
            row["parameter_json"]
        )

        configured_per_side = to_decimal(
            parameters.get("commission_per_side")
        )
        expected_round_trip = (
            configured_per_side * Decimal("2")
        )
        stored_round_trip = to_decimal(
            row["stored_round_trip_commission"]
        )
        execution_expectancy = to_decimal(
            row["execution_expectancy"]
        )

        persistence_delta = abs(
            stored_round_trip - expected_round_trip
        )

        break_even_per_side = max(
            Decimal("0"),
            execution_expectancy / Decimal("2"),
        )

        if configured_per_side <= 0:
            status = "INVALID_CONFIGURATION"
            reason = "COMMISSION_PER_SIDE_NOT_POSITIVE"
        elif persistence_delta > Decimal("0.00000001"):
            status = "PERSISTENCE_MISMATCH"
            reason = "STORED_COMMISSION_DIFFERS_FROM_CONFIGURATION"
        elif configured_per_side > break_even_per_side:
            status = "COMMISSION_ABOVE_BREAK_EVEN"
            reason = "CURRENT_COMMISSION_DESTROYS_EXECUTION_EDGE"
        else:
            status = "COMMISSION_WITHIN_BREAK_EVEN"
            reason = "NET_EDGE_MAY_SURVIVE"

        rows.append(
            {
                "rank": rank,
                "run_uuid": row["run_uuid"],
                "parameter_hash": row["parameter_hash"],
                "trades": row["trades"],
                "configured_commission_per_side": (
                    configured_per_side
                ),
                "expected_round_trip_commission": (
                    expected_round_trip
                ),
                "stored_round_trip_commission": (
                    stored_round_trip
                ),
                "commission_persistence_delta": (
                    persistence_delta
                ),
                "execution_expectancy": (
                    execution_expectancy
                ),
                "net_expectancy": row["net_expectancy"],
                "break_even_round_trip_commission": (
                    max(Decimal("0"), execution_expectancy)
                ),
                "break_even_commission_per_side": (
                    break_even_per_side
                ),
                "commission_headroom_per_side": (
                    break_even_per_side
                    - configured_per_side
                ),
                "verification_status": status,
                "verification_reason": reason,
            }
        )

    if not rows:
        unresolved.append(
            {
                "scope": "COMMISSION_CONTRACT",
                "identity": (
                    f"{TARGET_STRATEGY}:"
                    f"{TARGET_SYMBOL}:"
                    f"{TARGET_TIMEFRAME}"
                ),
                "reason": "NO_RUNS_FOUND",
            }
        )

    fields = (
        "rank",
        "run_uuid",
        "parameter_hash",
        "trades",
        "configured_commission_per_side",
        "expected_round_trip_commission",
        "stored_round_trip_commission",
        "commission_persistence_delta",
        "execution_expectancy",
        "net_expectancy",
        "break_even_round_trip_commission",
        "break_even_commission_per_side",
        "commission_headroom_per_side",
        "verification_status",
        "verification_reason",
    )

    write_tsv(
        output_dir / "commission_contract.tsv",
        fields,
        rows,
    )

    write_tsv(
        output_dir / "unresolved.tsv",
        ("scope", "identity", "reason"),
        unresolved,
    )

    persistence_ok_count = sum(
        to_decimal(row["commission_persistence_delta"])
        <= Decimal("0.00000001")
        for row in rows
    )

    within_break_even_count = sum(
        row["verification_status"]
        == "COMMISSION_WITHIN_BREAK_EVEN"
        for row in rows
    )

    best_break_even_per_side = (
        max(
            to_decimal(
                row["break_even_commission_per_side"]
            )
            for row in rows
        )
        if rows
        else Decimal("0")
    )

    contract_lines = (
        "FINAM COMMISSION CONTRACT VERIFICATION V1",
        "=========================================",
        "",
        f"BATCH_ID={args.batch_id}",
        f"RUN_COUNT={len(rows)}",
        f"PERSISTENCE_OK_COUNT={persistence_ok_count}",
        (
            "COMMISSION_WITHIN_BREAK_EVEN_COUNT="
            f"{within_break_even_count}"
        ),
        (
            "BEST_BREAK_EVEN_COMMISSION_PER_SIDE="
            f"{best_break_even_per_side}"
        ),
        f"UNRESOLVED_COUNT={len(unresolved)}",
        "EXTERNAL_TARIFF_VERIFIED=0",
        "DATABASE=POSTGRESQL_ONLY",
        "DB_WRITES_PERFORMED=0",
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

    print("=== FINAM COMMISSION CONTRACT VERIFICATION V1 ===")
    print(f"batch_id={args.batch_id}")
    print(f"run_count={len(rows)}")
    print(f"persistence_ok_count={persistence_ok_count}")
    print(
        "commission_within_break_even_count="
        f"{within_break_even_count}"
    )
    print(
        "best_break_even_commission_per_side="
        f"{best_break_even_per_side}"
    )
    print("external_tariff_verified=0")
    print(f"unresolved_count={len(unresolved)}")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FINAM_COMMISSION_CONTRACT_VERIFICATION_V1_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
