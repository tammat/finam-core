#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from collections import Counter, defaultdict
from decimal import Decimal
from typing import Any


SOURCE = pathlib.Path(
    "/tmp/edge_cost_recalculation_v1/recalculated_edges.tsv"
)

OUT = pathlib.Path(
    "/tmp/edge_cost_mismatch_diagnostics_v1"
)

DETAILS_FILE = OUT / "mismatch_details.tsv"
SUMMARY_FILE = OUT / "mismatch_summary.tsv"
STRATEGY_FILE = OUT / "strategy_summary.tsv"
HYPOTHESES_FILE = OUT / "formula_hypotheses.tsv"
CONTRACT_FILE = OUT / "contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


def decimal_value(value: str | None) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(value)


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
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
    OUT.mkdir(parents=True, exist_ok=True)

    if not SOURCE.is_file():
        raise RuntimeError(
            f"cost_recalculation_artifact_missing:{SOURCE}"
        )

    with SOURCE.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as stream:
        source_rows = list(
            csv.DictReader(stream, delimiter="\t")
        )

    mismatch_rows = [
        row
        for row in source_rows
        if row["classification"]
        == "COST_RECALCULATION_MISMATCH"
    ]

    detail_rows: list[dict[str, Any]] = []
    mismatch_counter: Counter[str] = Counter()
    strategy_counter: dict[
        tuple[str, str, str],
        Counter[str],
    ] = defaultdict(Counter)

    hypothesis_counter: Counter[str] = Counter()

    for row in mismatch_rows:
        failures: list[str] = []

        checks = (
            ("NET_IDENTITY", row["net_identity_ok"]),
            ("EXPECTANCY", row["expectancy_match"]),
            ("PROFIT_FACTOR", row["profit_factor_match"]),
            ("COMMISSION", row["commission_match"]),
            ("SLIPPAGE", row["slippage_match"]),
            ("DRAWDOWN", row["drawdown_match"]),
        )

        for name, result in checks:
            if result != "1":
                failures.append(name)
                mismatch_counter[name] += 1

        stored_expectancy = decimal_value(
            row["stored_expectancy"]
        )
        recalculated_expectancy = decimal_value(
            row["recalculated_expectancy"]
        )

        stored_profit_factor = decimal_value(
            row["stored_profit_factor"]
        )
        recalculated_profit_factor = decimal_value(
            row["recalculated_profit_factor"]
        )

        stored_commission = decimal_value(
            row["stored_commission"]
        )
        recalculated_commission = decimal_value(
            row["recalculated_commission"]
        )

        stored_slippage = decimal_value(
            row["stored_slippage"]
        )
        recalculated_slippage = decimal_value(
            row["recalculated_slippage"]
        )

        stored_drawdown = abs(
            decimal_value(row["stored_max_drawdown"])
        )
        recalculated_drawdown = decimal_value(
            row["recalculated_max_drawdown"]
        )

        hypotheses: list[str] = []

        if (
            row["expectancy_match"] != "1"
            and row["profit_factor_match"] == "1"
        ):
            hypotheses.append(
                "EXPECTANCY_FORMULA_OR_DENOMINATOR_DIFFERENCE"
            )

        if (
            row["profit_factor_match"] != "1"
            and row["net_identity_ok"] == "1"
        ):
            hypotheses.append(
                "PROFIT_FACTOR_GROSS_VS_NET_BASIS_DIFFERENCE"
            )

        if (
            row["commission_match"] != "1"
            and stored_commission == 0
            and recalculated_commission > 0
        ):
            hypotheses.append(
                "AGGREGATE_COMMISSION_NOT_POPULATED"
            )

        if (
            row["slippage_match"] != "1"
            and stored_slippage == 0
            and recalculated_slippage > 0
        ):
            hypotheses.append(
                "AGGREGATE_SLIPPAGE_NOT_POPULATED"
            )

        if (
            row["drawdown_match"] != "1"
            and row["expectancy_match"] == "1"
            and row["profit_factor_match"] == "1"
        ):
            hypotheses.append(
                "DRAWDOWN_ORDER_OR_BASELINE_DIFFERENCE"
            )

        if not hypotheses:
            hypotheses.append(
                "MULTI_METRIC_RECONCILIATION_REQUIRED"
            )

        for hypothesis in hypotheses:
            hypothesis_counter[hypothesis] += 1

        strategy_key = (
            row["strategy_code"],
            row["symbol"],
            row["timeframe"],
        )

        for failure in failures:
            strategy_counter[strategy_key][failure] += 1

        strategy_counter[strategy_key]["TOTAL"] += 1

        detail_rows.append(
            {
                "run_uuid": row["run_uuid"],
                "strategy_code": row["strategy_code"],
                "strategy_version": row["strategy_version"],
                "symbol": row["symbol"],
                "timeframe": row["timeframe"],
                "parameter_hash": row["parameter_hash"],
                "market_regime": row["market_regime"],
                "declared_trades": row["declared_trades"],
                "stored_expectancy": stored_expectancy,
                "recalculated_expectancy": (
                    recalculated_expectancy
                ),
                "expectancy_delta": (
                    recalculated_expectancy
                    - stored_expectancy
                ),
                "stored_profit_factor": (
                    stored_profit_factor
                ),
                "recalculated_profit_factor": (
                    recalculated_profit_factor
                ),
                "profit_factor_delta": (
                    recalculated_profit_factor
                    - stored_profit_factor
                ),
                "stored_commission": stored_commission,
                "recalculated_commission": (
                    recalculated_commission
                ),
                "commission_delta": (
                    recalculated_commission
                    - stored_commission
                ),
                "stored_slippage": stored_slippage,
                "recalculated_slippage": (
                    recalculated_slippage
                ),
                "slippage_delta": (
                    recalculated_slippage
                    - stored_slippage
                ),
                "stored_max_drawdown": stored_drawdown,
                "recalculated_max_drawdown": (
                    recalculated_drawdown
                ),
                "drawdown_delta": (
                    recalculated_drawdown
                    - stored_drawdown
                ),
                "failed_checks": ",".join(failures),
                "failure_count": len(failures),
                "hypotheses": ",".join(hypotheses),
                "runner_version": row.get(
                    "runner_version",
                    "",
                ),
                "source_version": row.get(
                    "source_version",
                    "",
                ),
            }
        )

    summary_rows = [
        {
            "mismatch_type": mismatch_type,
            "row_count": count,
        }
        for mismatch_type, count in sorted(
            mismatch_counter.items()
        )
    ]

    strategy_rows: list[dict[str, Any]] = []

    for (
        strategy_code,
        symbol,
        timeframe,
    ), counts in sorted(strategy_counter.items()):
        strategy_rows.append(
            {
                "strategy_code": strategy_code,
                "symbol": symbol,
                "timeframe": timeframe,
                "mismatch_count": counts["TOTAL"],
                "expectancy_mismatch_count": (
                    counts["EXPECTANCY"]
                ),
                "profit_factor_mismatch_count": (
                    counts["PROFIT_FACTOR"]
                ),
                "commission_mismatch_count": (
                    counts["COMMISSION"]
                ),
                "slippage_mismatch_count": (
                    counts["SLIPPAGE"]
                ),
                "drawdown_mismatch_count": (
                    counts["DRAWDOWN"]
                ),
                "net_identity_mismatch_count": (
                    counts["NET_IDENTITY"]
                ),
            }
        )

    hypothesis_rows = [
        {
            "hypothesis": hypothesis,
            "row_count": count,
            "status": "UNCONFIRMED",
        }
        for hypothesis, count in sorted(
            hypothesis_counter.items()
        )
    ]

    write_tsv(
        DETAILS_FILE,
        (
            "run_uuid",
            "strategy_code",
            "strategy_version",
            "symbol",
            "timeframe",
            "parameter_hash",
            "market_regime",
            "declared_trades",
            "stored_expectancy",
            "recalculated_expectancy",
            "expectancy_delta",
            "stored_profit_factor",
            "recalculated_profit_factor",
            "profit_factor_delta",
            "stored_commission",
            "recalculated_commission",
            "commission_delta",
            "stored_slippage",
            "recalculated_slippage",
            "slippage_delta",
            "stored_max_drawdown",
            "recalculated_max_drawdown",
            "drawdown_delta",
            "failed_checks",
            "failure_count",
            "hypotheses",
            "runner_version",
            "source_version",
        ),
        detail_rows,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "mismatch_type",
            "row_count",
        ),
        summary_rows,
    )

    write_tsv(
        STRATEGY_FILE,
        (
            "strategy_code",
            "symbol",
            "timeframe",
            "mismatch_count",
            "expectancy_mismatch_count",
            "profit_factor_mismatch_count",
            "commission_mismatch_count",
            "slippage_mismatch_count",
            "drawdown_mismatch_count",
            "net_identity_mismatch_count",
        ),
        strategy_rows,
    )

    write_tsv(
        HYPOTHESES_FILE,
        (
            "hypothesis",
            "row_count",
            "status",
        ),
        hypothesis_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        [],
    )

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "EDGE COST MISMATCH DIAGNOSTICS V1\n"
        )
        stream.write(
            "=================================\n\n"
        )
        stream.write("MODE=READ_ONLY_ARTIFACT_ANALYSIS\n")
        stream.write(
            f"MISMATCH_ROW_COUNT={len(detail_rows)}\n"
        )
        stream.write(
            f"MISMATCH_TYPE_COUNT={len(summary_rows)}\n"
        )
        stream.write(
            f"STRATEGY_GROUP_COUNT={len(strategy_rows)}\n"
        )
        stream.write(
            f"HYPOTHESIS_COUNT={len(hypothesis_rows)}\n"
        )
        stream.write("HYPOTHESES_CONFIRMED=0\n")
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== EDGE COST MISMATCH DIAGNOSTICS V1 ===")
    print(f"mismatch_row_count={len(detail_rows)}")
    print(f"mismatch_type_count={len(summary_rows)}")
    print(f"strategy_group_count={len(strategy_rows)}")
    print(f"hypothesis_count={len(hypothesis_rows)}")

    for row in summary_rows:
        print(
            "MISMATCH "
            f"type={row['mismatch_type']} "
            f"count={row['row_count']}"
        )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT=EDGE_COST_MISMATCH_DIAGNOSTICS_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
