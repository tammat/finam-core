#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import pathlib
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    execute_one,
)

from finam_core.research.futures_monetary_validity_v1 import (
    load_monetary_validity_by_run,
)


OUTPUT_ROOT = pathlib.Path(
    "/tmp/postgresql_edge_parameter_search_v1"
)

MINIMUM_TRADES = 30


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


def queued_runs(
    batch_id: str,
    limit: int,
) -> list[str]:
    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT run_uuid::text
                FROM analytics.edge_lab_run_v1
                WHERE research_batch_id = %s
                  AND status_code = 'QUEUED'
                ORDER BY created_at, id
                LIMIT %s
                """,
                (batch_id, limit),
            )
            return [
                str(row[0])
                for row in cursor.fetchall()
            ]


def classify(row: dict[str, Any]) -> tuple[str, str]:
    trades = int(row["trades"] or 0)
    expectancy = Decimal(str(row["expectancy"] or 0))
    profit_factor = Decimal(
        str(row["profit_factor"] or 0)
    )
    commission = Decimal(
        str(row["commission"] or 0)
    )
    slippage = Decimal(str(row["slippage"] or 0))

    if trades < MINIMUM_TRADES:
        return (
            "INSUFFICIENT_SAMPLE",
            f"TRADES_BELOW_{MINIMUM_TRADES}",
        )

    if commission <= 0:
        return (
            "INVALID_COST_MODEL",
            "COMMISSION_NOT_POSITIVE",
        )

    # Отрицательная экономика при нулевом slippage уже достаточна
    # для отклонения: положительное реальное проскальзывание
    # способно только ухудшить такой результат.
    if expectancy <= 0:
        return (
            "REJECTED_AFTER_COSTS",
            "EXPECTANCY_NOT_POSITIVE",
        )

    if profit_factor <= 1:
        return (
            "REJECTED_AFTER_COSTS",
            "PROFIT_FACTOR_NOT_ABOVE_ONE",
        )

    # Положительный результат нельзя повышать до EDGE_CANDIDATE,
    # пока нет подтверждённой положительной модели slippage.
    if slippage <= 0:
        return (
            "COST_MODEL_INCOMPLETE",
            "SLIPPAGE_MODEL_MISSING",
        )

    return (
        "EDGE_CANDIDATE",
        "POSITIVE_AFTER_COSTS",
    )


def apply_monetary_ranking_guard(
    *,
    symbol: str,
    run_uuid: str,
    classification: str,
    reason: str,
    monetary_by_run: dict[str, dict],
) -> tuple[str, str]:
    """
    Fail-closed monetary guard для futures EDGE_CANDIDATE.

    Первичная причина отклонения сохраняется для всех результатов,
    которые не дошли до EDGE_CANDIDATE.
    Equity ranking не изменяется.
    """
    if classification != "EDGE_CANDIDATE":
        return classification, reason

    if not symbol.endswith("@RTSX"):
        return classification, reason

    monetary = monetary_by_run.get(run_uuid)

    if monetary is None:
        return (
            "MONETARY_VALIDITY_REJECTED",
            "MONETARY_LINEAGE_MISSING",
        )

    if not monetary["ranking_allowed"]:
        return (
            "MONETARY_VALIDITY_REJECTED",
            str(monetary["monetary_status"]),
        )

    return classification, reason


def load_results(
    batch_id: str,
) -> list[dict[str, Any]]:
    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    r.id AS task_id,
                    r.run_uuid::text,
                    r.research_batch_id,
                    r.research_code,
                    r.strategy_code,
                    r.strategy_version,
                    r.symbol,
                    r.timeframe,
                    r.parameter_hash,
                    r.parameter_json,
                    r.status_code,
                    r.started_at,
                    r.finished_at,
                    o.trades,
                    o.wins,
                    o.losses,
                    o.win_rate,
                    o.expectancy,
                    o.profit_factor,
                    o.max_drawdown,
                    o.recovery_factor,
                    o.sharpe,
                    o.sortino,
                    o.commission,
                    o.slippage,
                    o.stability_score,
                    o.confidence_score,
                    o.verdict_code
                FROM analytics.edge_lab_run_v1 r
                LEFT JOIN analytics.edge_observation_v1 o
                  ON o.run_uuid = r.run_uuid
                WHERE r.research_batch_id = %s
                ORDER BY r.id
                """,
                (batch_id,),
            )

            return [
                dict(row)
                for row in cursor.fetchall()
            ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run PostgreSQL Edge Parameter Search V1"
        )
    )
    parser.add_argument(
        "--batch-id",
        required=True,
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=500,
    )
    parser.add_argument(
        "--report-only",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    output_dir = OUTPUT_ROOT / args.batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    attempted = 0
    succeeded = 0
    failed = 0
    execution_rows: list[dict[str, Any]] = []

    if not args.report_only:
        run_uuids = queued_runs(
            args.batch_id,
            args.max_runs,
        )

        for run_uuid in run_uuids:
            attempted += 1
            rc = execute_one(run_uuid=run_uuid)

            if rc == 0:
                succeeded += 1
                status = "EXECUTED"
            else:
                failed += 1
                status = "FAILED"

            execution_rows.append(
                {
                    "run_uuid": run_uuid,
                    "exit_code": rc,
                    "execution_status": status,
                }
            )

    write_tsv(
        output_dir / "execution_results.tsv",
        (
            "run_uuid",
            "exit_code",
            "execution_status",
        ),
        execution_rows,
    )

    raw_results = load_results(args.batch_id)
    classified: list[dict[str, Any]] = []

    monetary_by_run = load_monetary_validity_by_run()

    for row in raw_results:
        if row["trades"] is None:
            classification = (
                "NOT_EXECUTED"
                if row["status_code"] == "QUEUED"
                else "RESULT_MISSING"
            )
            reason = (
                "TASK_STILL_QUEUED"
                if row["status_code"] == "QUEUED"
                else "EDGE_OBSERVATION_MISSING"
            )
        else:
            classification, reason = classify(row)

        classification, reason = (
            apply_monetary_ranking_guard(
                symbol=str(row["symbol"]),
                run_uuid=str(row["run_uuid"]),
                classification=classification,
                reason=reason,
                monetary_by_run=monetary_by_run,
            )
        )

        classified.append(
            {
                **row,
                "classification": classification,
                "classification_reason": reason,
            }
        )

    candidates = [
        row
        for row in classified
        if row["classification"] == "EDGE_CANDIDATE"
    ]

    candidates.sort(
        key=lambda row: (
            -Decimal(str(row["expectancy"] or 0)),
            -Decimal(str(row["profit_factor"] or 0)),
            Decimal(str(row["max_drawdown"] or 0)),
        )
    )

    rejected = [
        row
        for row in classified
        if row["classification"] != "EDGE_CANDIDATE"
    ]

    fields = (
        "task_id",
        "run_uuid",
        "research_batch_id",
        "research_code",
        "strategy_code",
        "strategy_version",
        "symbol",
        "timeframe",
        "parameter_hash",
        "parameter_json",
        "status_code",
        "trades",
        "wins",
        "losses",
        "win_rate",
        "expectancy",
        "profit_factor",
        "max_drawdown",
        "recovery_factor",
        "sharpe",
        "sortino",
        "commission",
        "slippage",
        "stability_score",
        "confidence_score",
        "verdict_code",
        "classification",
        "classification_reason",
    )

    write_tsv(
        output_dir / "candidate_ranking.tsv",
        fields,
        candidates,
    )

    write_tsv(
        output_dir / "rejected_candidates.tsv",
        fields,
        rejected,
    )

    status_counts: dict[str, int] = {}

    for row in classified:
        key = str(row["classification"])
        status_counts[key] = status_counts.get(key, 0) + 1

    unresolved: list[dict[str, str]] = []

    for row in classified:
        if row["classification"] == "RESULT_MISSING":
            unresolved.append(
                {
                    "scope": "SEARCH_RESULT",
                    "identity": str(row["run_uuid"]),
                    "reason": "EDGE_OBSERVATION_MISSING",
                }
            )

    write_tsv(
        output_dir / "unresolved.tsv",
        ("scope", "identity", "reason"),
        unresolved,
    )

    completed_count = sum(
        row["status_code"] == "DONE"
        for row in classified
    )
    queued_count = sum(
        row["status_code"] == "QUEUED"
        for row in classified
    )
    failed_count = sum(
        row["status_code"] == "FAILED"
        for row in classified
    )

    contract = [
        "POSTGRESQL EDGE PARAMETER SEARCH V1 RESULTS",
        "===========================================",
        "",
        f"BATCH_ID={args.batch_id}",
        f"TOTAL_TASK_COUNT={len(classified)}",
        f"ATTEMPTED_COUNT={attempted}",
        f"EXECUTION_SUCCESS_COUNT={succeeded}",
        f"EXECUTION_FAILED_COUNT={failed}",
        f"DONE_COUNT={completed_count}",
        f"QUEUED_COUNT={queued_count}",
        f"FAILED_COUNT={failed_count}",
        f"EDGE_CANDIDATE_COUNT={len(candidates)}",
        f"REJECTED_COUNT={len(rejected)}",
        f"UNRESOLVED_COUNT={len(unresolved)}",
        f"MINIMUM_TRADES={MINIMUM_TRADES}",
        "OOS_ALLOWED=0",
        "SHADOW_ALLOWED=0",
        "PAPER_ALLOWED=0",
        "RUNTIME_CHANGED=0",
        "EXECUTION_CHANGED=0",
        "ORDERS_CHANGED=0",
        "FILLS_CHANGED=0",
        "MICRO_LIVE_ALLOWED=0",
    ]

    (output_dir / "contract.txt").write_text(
        "\n".join(contract) + "\n",
        encoding="utf-8",
    )

    print("=== POSTGRESQL EDGE PARAMETER SEARCH V1 RESULTS ===")
    print(f"batch_id={args.batch_id}")
    print(f"total_task_count={len(classified)}")
    print(f"attempted_count={attempted}")
    print(f"execution_success_count={succeeded}")
    print(f"execution_failed_count={failed}")
    print(f"done_count={completed_count}")
    print(f"queued_count={queued_count}")
    print(f"failed_count={failed_count}")
    print(f"edge_candidate_count={len(candidates)}")
    print(f"rejected_count={len(rejected)}")
    print(f"unresolved_count={len(unresolved)}")

    for classification in sorted(status_counts):
        print(
            "SEARCH_CLASSIFICATION "
            f"classification={classification} "
            f"count={status_counts[classification]}"
        )

    for rank, row in enumerate(candidates[:20], start=1):
        print(
            "EDGE_CANDIDATE "
            f"rank={rank} "
            f"strategy={row['strategy_code']} "
            f"symbol={row['symbol']} "
            f"timeframe={row['timeframe']} "
            f"trades={row['trades']} "
            f"expectancy={row['expectancy']} "
            f"profit_factor={row['profit_factor']} "
            f"max_drawdown={row['max_drawdown']} "
            f"parameter_hash={row['parameter_hash']}"
        )

    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_PARAMETER_SEARCH_V1_RESULTS_READY"
    )

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
