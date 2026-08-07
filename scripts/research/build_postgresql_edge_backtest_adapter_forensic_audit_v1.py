#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import pathlib
import re
from dataclasses import dataclass
from typing import Any, Iterable

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


ROOT = pathlib.Path("/opt/finam-core")

SEARCH_ROOTS = (
    ROOT / "scripts/research",
    ROOT / "src",
)

TARGET_MARKERS = (
    "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1",
    "edge_lab_run_v1",
    "research_trade_v1",
    "edge_observation_v1",
    "status_code = 'FAILED'",
    'status_code = "FAILED"',
    "RESULT_MISSING",
    "EDGE_OBSERVATION_MISSING",
    "run_postgresql_edge_parameter_search_v1",
    "build_postgresql_edge_backtest_adapter_v1",
)

STRATEGY_MARKERS = (
    "RSI_MEAN_REVERSION_V1",
    "ATR_IMPULSE_V1",
    "MOMENTUM_CONTINUATION_V1",
    "MEAN_REVERSION_ZSCORE_V1",
    "TREND_PULLBACK_V1",
    "VOLATILITY_BREAKOUT_FILTERED_V1",
)

ERROR_MARKERS = (
    "except Exception",
    "traceback",
    "raise RuntimeError",
    "raise ValueError",
    "SystemExit",
    "FAILED",
)

PERSISTENCE_MARKERS = (
    "INSERT INTO analytics.research_trade_v1",
    "INSERT INTO analytics.edge_observation_v1",
    "research_trade_v1",
    "edge_observation_v1",
)

BAR_MARKERS = (
    "market_bars",
    "bar_schema",
    "bar_table",
    "minimum_bars",
    "bar_limit",
)


@dataclass(frozen=True, slots=True)
class SourceMatch:
    path: pathlib.Path
    line_number: int
    line: str
    marker: str


def iter_python_files() -> Iterable[pathlib.Path]:
    seen: set[pathlib.Path] = set()

    for root in SEARCH_ROOTS:
        if not root.is_dir():
            continue

        for path in root.rglob("*.py"):
            resolved = path.resolve()

            if resolved in seen:
                continue

            seen.add(resolved)
            yield path


def find_matches(
    paths: Iterable[pathlib.Path],
    markers: tuple[str, ...],
) -> list[SourceMatch]:
    result: list[SourceMatch] = []

    for path in paths:
        try:
            lines = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines()
        except OSError:
            continue

        for line_number, line in enumerate(lines, start=1):
            for marker in markers:
                if marker in line:
                    result.append(
                        SourceMatch(
                            path=path,
                            line_number=line_number,
                            line=line.strip(),
                            marker=marker,
                        )
                    )

    return result


def function_inventory(
    path: pathlib.Path,
) -> list[dict[str, Any]]:
    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return []

    result: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
            ),
        ):
            result.append(
                {
                    "type": type(node).__name__,
                    "name": node.name,
                    "line": node.lineno,
                }
            )

    return sorted(
        result,
        key=lambda item: (
            int(item["line"]),
            str(item["name"]),
        ),
    )


def relative(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Edge Backtest Adapter "
            "Forensic Audit V1"
        )
    )
    parser.add_argument("--batch-id", required=True)
    args = parser.parse_args()

    python_files = list(iter_python_files())

    target_matches = find_matches(
        python_files,
        TARGET_MARKERS,
    )

    candidate_paths = sorted(
        {
            match.path
            for match in target_matches
        }
    )

    strategy_matches = find_matches(
        candidate_paths,
        STRATEGY_MARKERS,
    )
    error_matches = find_matches(
        candidate_paths,
        ERROR_MARKERS,
    )
    persistence_matches = find_matches(
        candidate_paths,
        PERSISTENCE_MARKERS,
    )
    bar_matches = find_matches(
        candidate_paths,
        BAR_MARKERS,
    )

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    run_uuid::text,
                    research_batch_id,
                    research_code,
                    strategy_code,
                    strategy_version,
                    symbol,
                    timeframe,
                    status_code,
                    parameter_hash,
                    parameter_json,
                    dataset_version,
                    runner_version,
                    source_version,
                    created_at,
                    started_at,
                    finished_at
                FROM analytics.edge_lab_run_v1
                WHERE research_batch_id = %s
                ORDER BY created_at, id
                """,
                (args.batch_id,),
            )

            runs = [
                dict(row)
                for row in cursor.fetchall()
            ]

            if not runs:
                raise SystemExit(
                    f"ERROR=batch_not_found:{args.batch_id}"
                )

            run_uuids = [
                row["run_uuid"]
                for row in runs
            ]

            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    count(*)::bigint AS trade_count
                FROM analytics.research_trade_v1
                WHERE run_uuid::text = ANY(%s)
                GROUP BY run_uuid
                """,
                (run_uuids,),
            )

            trade_counts = {
                row["run_uuid"]: int(
                    row["trade_count"] or 0
                )
                for row in cursor.fetchall()
            }

            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    count(*)::bigint AS observation_count,
                    max(verdict_code) AS verdict_code
                FROM analytics.edge_observation_v1
                WHERE run_uuid::text = ANY(%s)
                GROUP BY run_uuid
                """,
                (run_uuids,),
            )

            observation_counts = {
                row["run_uuid"]: {
                    "count": int(
                        row["observation_count"] or 0
                    ),
                    "verdict": row["verdict_code"],
                }
                for row in cursor.fetchall()
            }

            for run in runs:
                cursor.execute(
                    """
                    SELECT
                        count(*)::bigint AS bar_count,
                        min(ts) AS first_ts,
                        max(ts) AS last_ts
                    FROM public.market_bars
                    WHERE symbol = %s
                      AND timeframe = %s
                    """,
                    (
                        run["symbol"],
                        run["timeframe"],
                    ),
                )

                run["bar_coverage"] = dict(
                    cursor.fetchone()
                )

    print(
        "=== POSTGRESQL EDGE BACKTEST ADAPTER "
        "FORENSIC AUDIT V1 ==="
    )
    print(f"batch_id={args.batch_id}")
    print(f"python_file_count={len(python_files)}")
    print(f"candidate_file_count={len(candidate_paths)}")
    print(f"target_match_count={len(target_matches)}")
    print(f"strategy_match_count={len(strategy_matches)}")
    print(f"error_match_count={len(error_matches)}")
    print(
        f"persistence_match_count="
        f"{len(persistence_matches)}"
    )
    print(f"bar_match_count={len(bar_matches)}")

    for run in runs:
        run_uuid = run["run_uuid"]
        trade_count = trade_counts.get(run_uuid, 0)
        observation = observation_counts.get(
            run_uuid,
            {
                "count": 0,
                "verdict": None,
            },
        )
        bars = run["bar_coverage"]

        print(
            "FORENSIC_RUN "
            f"run_uuid={run_uuid} "
            f"status={run['status_code']} "
            f"strategy={run['strategy_code']} "
            f"symbol={run['symbol']} "
            f"timeframe={run['timeframe']} "
            f"runner={run['runner_version']} "
            f"source={run['source_version']} "
            f"trade_count={trade_count} "
            f"observation_count="
            f"{observation['count']} "
            f"observation_verdict="
            f"{observation['verdict']} "
            f"bar_count={bars['bar_count']} "
            f"bar_first_ts={bars['first_ts']} "
            f"bar_last_ts={bars['last_ts']} "
            "parameter_json="
            + json.dumps(
                run["parameter_json"],
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )

    for path in candidate_paths:
        print(f"CANDIDATE_FILE path={relative(path)}")

        for item in function_inventory(path):
            print(
                "SOURCE_OBJECT "
                f"path={relative(path)} "
                f"type={item['type']} "
                f"name={item['name']} "
                f"line={item['line']}"
            )

    groups = (
        ("TARGET", target_matches),
        ("STRATEGY", strategy_matches),
        ("ERROR", error_matches),
        ("PERSISTENCE", persistence_matches),
        ("BAR", bar_matches),
    )

    for group_name, matches in groups:
        for match in matches:
            print(
                "SOURCE_MATCH "
                f"group={group_name} "
                f"path={relative(match.path)} "
                f"line={match.line_number} "
                f"marker={match.marker!r} "
                f"text={match.line!r}"
            )

    failed_count = sum(
        str(run["status_code"]) == "FAILED"
        for run in runs
    )
    result_missing_count = sum(
        trade_counts.get(run["run_uuid"], 0) == 0
        and observation_counts.get(
            run["run_uuid"],
            {"count": 0},
        )["count"] == 0
        for run in runs
    )
    bars_present_count = sum(
        int(
            run["bar_coverage"]["bar_count"]
            or 0
        ) > 0
        for run in runs
    )

    if not candidate_paths:
        root_cause = "ADAPTER_SOURCE_NOT_DISCOVERED"
    elif failed_count > 0 and bars_present_count == 0:
        root_cause = "BAR_INPUT_MISSING"
    elif failed_count > 0 and result_missing_count > 0:
        root_cause = (
            "ADAPTER_FAILED_BEFORE_RESULT_PERSISTENCE"
        )
    else:
        root_cause = "FORENSIC_REVIEW_REQUIRED"

    print(f"run_count={len(runs)}")
    print(f"failed_run_count={failed_count}")
    print(
        f"result_missing_count="
        f"{result_missing_count}"
    )
    print(
        f"bars_present_run_count="
        f"{bars_present_count}"
    )
    print(f"root_cause={root_cause}")
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
        "POSTGRESQL_EDGE_BACKTEST_ADAPTER_FORENSIC_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
