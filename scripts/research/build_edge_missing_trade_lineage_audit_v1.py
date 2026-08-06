#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from collections import Counter
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


OUT = pathlib.Path("/tmp/edge_missing_trade_lineage_audit_v1")

RUNS_FILE = OUT / "missing_trade_runs.tsv"
SUMMARY_FILE = OUT / "missing_trade_summary.tsv"
PRIORITY_FILE = OUT / "candidate_priority.tsv"
CONTRACT_FILE = OUT / "lineage_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


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


def relation_exists(
    cursor: RealDictCursor,
    schema_name: str,
    relation_name: str,
) -> bool:
    cursor.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = %s
              AND table_name = %s
            UNION ALL
            SELECT 1
            FROM information_schema.views
            WHERE table_schema = %s
              AND table_name = %s
        ) AS exists
        """,
        (
            schema_name,
            relation_name,
            schema_name,
            relation_name,
        ),
    )
    return bool(cursor.fetchone()["exists"])


def relation_columns(
    cursor: RealDictCursor,
    schema_name: str,
    relation_name: str,
) -> set[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        """,
        (schema_name, relation_name),
    )
    return {
        str(row["column_name"])
        for row in cursor.fetchall()
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, str]] = []

    with psycopg2.connect(build_psycopg_url()) as connection:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                WITH trade_runs AS (
                    SELECT DISTINCT
                        run_uuid,
                        research_code,
                        strategy_code,
                        symbol,
                        timeframe
                    FROM analytics.research_trade_v1
                )
                SELECT
                    o.run_uuid::text,
                    o.research_batch_id,
                    o.research_code,
                    o.strategy_code,
                    o.strategy_version,
                    o.symbol,
                    o.timeframe,
                    o.parameter_hash,
                    o.dataset_version,
                    o.market_data_version,
                    o.runner_version,
                    o.market_regime,
                    o.bars_used,
                    o.trades,
                    o.wins,
                    o.losses,
                    o.win_rate,
                    o.profit_factor,
                    o.expectancy,
                    o.max_drawdown,
                    o.commission,
                    o.slippage,
                    o.stability_score,
                    o.confidence_score,
                    o.verdict_code,
                    o.source_version,
                    o.created_at,
                    o.updated_at
                FROM analytics.edge_observation_v1 o
                LEFT JOIN trade_runs t
                  ON t.run_uuid = o.run_uuid
                 AND t.research_code = o.research_code
                 AND t.strategy_code = o.strategy_code
                 AND t.symbol = o.symbol
                 AND t.timeframe = o.timeframe
                WHERE t.run_uuid IS NULL
                ORDER BY
                    o.strategy_code,
                    o.symbol,
                    o.timeframe,
                    o.created_at
                """
            )
            rows = [dict(row) for row in cursor.fetchall()]

            metadata_candidates = (
                ("analytics", "edge_lab_run_v1"),
                ("analytics", "research_run_v1"),
                ("analytics", "research_queue_v1"),
                ("analytics", "parameter_search_job_v1"),
            )

            metadata_relations: list[tuple[str, str, set[str]]] = []

            for schema_name, relation_name in metadata_candidates:
                if not relation_exists(
                    cursor,
                    schema_name,
                    relation_name,
                ):
                    continue

                columns = relation_columns(
                    cursor,
                    schema_name,
                    relation_name,
                )

                if "run_uuid" in columns:
                    metadata_relations.append(
                        (schema_name, relation_name, columns)
                    )

            run_metadata: dict[str, list[str]] = {}

            for schema_name, relation_name, _columns in metadata_relations:
                cursor.execute(
                    f"""
                    SELECT DISTINCT run_uuid::text
                    FROM {schema_name}.{relation_name}
                    WHERE run_uuid IS NOT NULL
                    """
                )

                for metadata_row in cursor.fetchall():
                    run_uuid = str(metadata_row["run_uuid"])
                    run_metadata.setdefault(run_uuid, []).append(
                        f"{schema_name}.{relation_name}"
                    )

    classified_rows: list[dict[str, Any]] = []

    for row in rows:
        run_uuid = str(row["run_uuid"])
        metadata_sources = run_metadata.get(run_uuid, [])

        trades = int(row["trades"] or 0)
        expectancy = row["expectancy"]
        profit_factor = row["profit_factor"]
        commission = row["commission"]
        slippage = row["slippage"]

        has_complete_summary = all(
            value is not None
            for value in (
                expectancy,
                profit_factor,
                commission,
                slippage,
            )
        )

        positive_candidate = (
            trades >= 30
            and expectancy is not None
            and expectancy > 0
            and profit_factor is not None
            and profit_factor > 1
        )

        if not metadata_sources:
            classification = "RUN_METADATA_MISSING"
            replay_status = "NOT_REPLAYABLE"
            reason = "NO_RUN_METADATA_RELATION_MATCH"
        elif trades <= 0:
            classification = "SUMMARY_ONLY_RUN"
            replay_status = "NOT_REQUIRED"
            reason = "DECLARED_TRADES_ZERO"
        elif has_complete_summary:
            classification = "TRADE_PERSISTENCE_NOT_SUPPORTED"
            replay_status = "REPLAY_CANDIDATE"
            reason = "AGGREGATE_PRESENT_DETAILED_TRADES_ABSENT"
        else:
            classification = "TRADE_PERSISTENCE_FAILURE"
            replay_status = "REPLAY_CANDIDATE"
            reason = "INCOMPLETE_AGGREGATE_AND_TRADES_ABSENT"

        priority = (
            "HIGH"
            if positive_candidate and replay_status == "REPLAY_CANDIDATE"
            else "MEDIUM"
            if replay_status == "REPLAY_CANDIDATE"
            else "LOW"
        )

        classified_rows.append(
            {
                **row,
                "metadata_sources": ",".join(metadata_sources),
                "classification": classification,
                "replay_status": replay_status,
                "priority": priority,
                "reason": reason,
            }
        )

    classification_counts = Counter(
        row["classification"]
        for row in classified_rows
    )

    priority_rows = sorted(
        (
            row
            for row in classified_rows
            if row["priority"] in {"HIGH", "MEDIUM"}
        ),
        key=lambda row: (
            row["priority"] != "HIGH",
            -(float(row["expectancy"] or 0)),
            -(float(row["profit_factor"] or 0)),
            -(int(row["trades"] or 0)),
        ),
    )

    summary_rows = [
        {
            "classification": classification,
            "row_count": count,
        }
        for classification, count in sorted(
            classification_counts.items()
        )
    ]

    write_tsv(
        RUNS_FILE,
        (
            "run_uuid",
            "research_batch_id",
            "research_code",
            "strategy_code",
            "strategy_version",
            "symbol",
            "timeframe",
            "parameter_hash",
            "dataset_version",
            "market_data_version",
            "runner_version",
            "market_regime",
            "bars_used",
            "trades",
            "wins",
            "losses",
            "win_rate",
            "profit_factor",
            "expectancy",
            "max_drawdown",
            "commission",
            "slippage",
            "stability_score",
            "confidence_score",
            "verdict_code",
            "source_version",
            "created_at",
            "updated_at",
            "metadata_sources",
            "classification",
            "replay_status",
            "priority",
            "reason",
        ),
        classified_rows,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "classification",
            "row_count",
        ),
        summary_rows,
    )

    write_tsv(
        PRIORITY_FILE,
        (
            "priority",
            "run_uuid",
            "research_code",
            "strategy_code",
            "strategy_version",
            "symbol",
            "timeframe",
            "market_regime",
            "parameter_hash",
            "trades",
            "expectancy",
            "profit_factor",
            "max_drawdown",
            "commission",
            "slippage",
            "confidence_score",
            "verdict_code",
            "classification",
            "replay_status",
            "metadata_sources",
        ),
        priority_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    high_priority_count = sum(
        row["priority"] == "HIGH"
        for row in classified_rows
    )
    replay_candidate_count = sum(
        row["replay_status"] == "REPLAY_CANDIDATE"
        for row in classified_rows
    )
    metadata_missing_count = sum(
        row["classification"] == "RUN_METADATA_MISSING"
        for row in classified_rows
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("EDGE MISSING TRADE LINEAGE AUDIT V1\n")
        stream.write("===================================\n\n")
        stream.write("MODE=READ_ONLY\n")
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write(
            f"MISSING_TRADE_RUN_COUNT={len(classified_rows)}\n"
        )
        stream.write(
            f"REPLAY_CANDIDATE_COUNT={replay_candidate_count}\n"
        )
        stream.write(
            f"HIGH_PRIORITY_COUNT={high_priority_count}\n"
        )
        stream.write(
            f"RUN_METADATA_MISSING_COUNT={metadata_missing_count}\n"
        )
        stream.write(f"UNRESOLVED_COUNT={len(unresolved)}\n")
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== EDGE MISSING TRADE LINEAGE AUDIT V1 ===")
    print(f"missing_trade_run_count={len(classified_rows)}")
    print(f"replay_candidate_count={replay_candidate_count}")
    print(f"high_priority_count={high_priority_count}")
    print(f"run_metadata_missing_count={metadata_missing_count}")
    print(f"unresolved_count={len(unresolved)}")

    for classification, count in sorted(
        classification_counts.items()
    ):
        print(
            "MISSING_TRADE_CLASS "
            f"classification={classification} "
            f"count={count}"
        )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_MISSING_TRADE_LINEAGE_AUDIT_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
