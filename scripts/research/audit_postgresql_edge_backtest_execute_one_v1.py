#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import inspect
import pathlib
from dataclasses import dataclass
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

import finam_core.research.postgresql_edge_backtest_adapter_v1 as adapter
from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True, slots=True)
class SourceObject:
    object_type: str
    name: str
    line: int
    end_line: int


def dotted_name(node: ast.AST | None) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr

    return ""


def source_objects(tree: ast.AST) -> list[SourceObject]:
    result: list[SourceObject] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            result.append(
                SourceObject(
                    object_type="FUNCTION",
                    name=node.name,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                )
            )
        elif isinstance(node, ast.AsyncFunctionDef):
            result.append(
                SourceObject(
                    object_type="ASYNC_FUNCTION",
                    name=node.name,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                )
            )
        elif isinstance(node, ast.ClassDef):
            result.append(
                SourceObject(
                    object_type="CLASS",
                    name=node.name,
                    line=node.lineno,
                    end_line=getattr(node, "end_lineno", node.lineno),
                )
            )

    return sorted(result, key=lambda item: item.line)


def enclosing_function(
    line_number: int,
    objects: list[SourceObject],
) -> str:
    candidates = [
        item
        for item in objects
        if item.object_type in {"FUNCTION", "ASYNC_FUNCTION"}
        and item.line <= line_number <= item.end_line
    ]

    if not candidates:
        return "MODULE"

    candidates.sort(
        key=lambda item: (
            item.end_line - item.line,
            -item.line,
        )
    )

    return candidates[0].name


def main() -> int:
    parser = argparse.ArgumentParser(
        description="PostgreSQL Edge Backtest execute_one Audit V1"
    )
    parser.add_argument("--run-uuid", required=True)
    args = parser.parse_args()

    adapter_file_text = inspect.getsourcefile(adapter)

    if adapter_file_text is None:
        raise SystemExit("ERROR=adapter_source_file_missing")

    adapter_file = pathlib.Path(adapter_file_text)
    source = adapter_file.read_text(
        encoding="utf-8",
        errors="replace",
    )
    lines = source.splitlines()
    tree = ast.parse(source, filename=str(adapter_file))
    objects = source_objects(tree)

    execute_one_object = next(
        (
            item
            for item in objects
            if item.object_type == "FUNCTION"
            and item.name == "execute_one"
        ),
        None,
    )

    if execute_one_object is None:
        raise SystemExit("ERROR=execute_one_function_missing")

    calls: list[dict[str, Any]] = []
    returns: list[dict[str, Any]] = []
    raises: list[dict[str, Any]] = []
    handlers: list[dict[str, Any]] = []
    status_mutations: list[dict[str, Any]] = []
    strategy_lines: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        node_line = getattr(node, "lineno", 0)

        if not (
            execute_one_object.line
            <= node_line
            <= execute_one_object.end_line
        ):
            continue

        if isinstance(node, ast.Call):
            calls.append(
                {
                    "line": node_line,
                    "target": dotted_name(node.func),
                    "text": (
                        lines[node_line - 1].strip()
                        if 0 < node_line <= len(lines)
                        else ""
                    ),
                }
            )

        elif isinstance(node, ast.Return):
            returns.append(
                {
                    "line": node_line,
                    "value": ast.unparse(node.value)
                    if node.value is not None
                    else "None",
                }
            )

        elif isinstance(node, ast.Raise):
            raises.append(
                {
                    "line": node_line,
                    "value": ast.unparse(node.exc)
                    if node.exc is not None
                    else "re-raise",
                }
            )

        elif isinstance(node, ast.ExceptHandler):
            handlers.append(
                {
                    "line": node_line,
                    "type": dotted_name(node.type)
                    if node.type is not None
                    else "bare_except",
                    "name": node.name or "",
                }
            )

    markers = (
        "FAILED",
        "DONE",
        "status_code",
        "strategy_code",
        "RSI_MEAN_REVERSION_V1",
        "unsupported",
        "market_bars",
        "bar_schema",
        "bar_table",
        "parameter_json",
        "research_trade_v1",
        "edge_observation_v1",
        "traceback",
        "except Exception",
    )

    for number in range(
        execute_one_object.line,
        execute_one_object.end_line + 1,
    ):
        text = lines[number - 1]

        if any(marker in text for marker in markers):
            strategy_lines.append(
                {
                    "line": number,
                    "text": text.strip(),
                }
            )

        if (
            "UPDATE" in text.upper()
            and "edge_lab_run_v1" in text
        ):
            status_mutations.append(
                {
                    "line": number,
                    "text": text.strip(),
                }
            )

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    run_uuid::text,
                    research_batch_id,
                    research_code,
                    strategy_code,
                    strategy_version,
                    symbol,
                    timeframe,
                    status_code,
                    parameter_json,
                    runner_version,
                    source_version,
                    created_at,
                    started_at,
                    finished_at
                FROM analytics.edge_lab_run_v1
                WHERE run_uuid = %s::uuid
                """,
                (args.run_uuid,),
            )

            run = cursor.fetchone()

            if run is None:
                raise SystemExit(
                    f"ERROR=run_not_found:{args.run_uuid}"
                )

            cursor.execute(
                """
                SELECT
                    count(*)::bigint AS trade_count
                FROM analytics.research_trade_v1
                WHERE run_uuid = %s::uuid
                """,
                (args.run_uuid,),
            )
            trade_count = int(
                cursor.fetchone()["trade_count"] or 0
            )

            cursor.execute(
                """
                SELECT
                    count(*)::bigint AS observation_count
                FROM analytics.edge_observation_v1
                WHERE run_uuid = %s::uuid
                """,
                (args.run_uuid,),
            )
            observation_count = int(
                cursor.fetchone()["observation_count"] or 0
            )

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
            bars = dict(cursor.fetchone())

    print("=== POSTGRESQL EDGE BACKTEST EXECUTE_ONE AUDIT V1 ===")
    print(f"adapter_file={adapter_file}")
    print(f"execute_one_line={execute_one_object.line}")
    print(f"execute_one_end_line={execute_one_object.end_line}")
    print(f"run_uuid={run['run_uuid']}")
    print(f"batch_id={run['research_batch_id']}")
    print(f"strategy_code={run['strategy_code']}")
    print(f"symbol={run['symbol']}")
    print(f"timeframe={run['timeframe']}")
    print(f"status_code={run['status_code']}")
    print(f"runner_version={run['runner_version']}")
    print(f"source_version={run['source_version']}")
    print(f"parameter_json={run['parameter_json']}")
    print(f"trade_count={trade_count}")
    print(f"observation_count={observation_count}")
    print(f"bar_count={bars['bar_count']}")
    print(f"bar_first_ts={bars['first_ts']}")
    print(f"bar_last_ts={bars['last_ts']}")
    print(f"call_count={len(calls)}")
    print(f"return_count={len(returns)}")
    print(f"raise_count={len(raises)}")
    print(f"exception_handler_count={len(handlers)}")

    for item in calls:
        print(
            "EXECUTE_ONE_CALL "
            f"line={item['line']} "
            f"target={item['target']} "
            f"text={item['text']!r}"
        )

    for item in returns:
        print(
            "EXECUTE_ONE_RETURN "
            f"line={item['line']} "
            f"value={item['value']!r}"
        )

    for item in raises:
        print(
            "EXECUTE_ONE_RAISE "
            f"line={item['line']} "
            f"value={item['value']!r}"
        )

    for item in handlers:
        print(
            "EXECUTE_ONE_HANDLER "
            f"line={item['line']} "
            f"type={item['type']} "
            f"name={item['name']}"
        )

    for item in strategy_lines:
        print(
            "EXECUTE_ONE_SOURCE "
            f"line={item['line']} "
            f"text={item['text']!r}"
        )

    for item in status_mutations:
        print(
            "EXECUTE_ONE_STATUS_MUTATION "
            f"line={item['line']} "
            f"text={item['text']!r}"
        )

    if int(bars["bar_count"] or 0) == 0:
        root_cause = "EXECUTE_ONE_BAR_INPUT_MISSING"
    elif trade_count == 0 and observation_count == 0:
        root_cause = "EXECUTE_ONE_FAILED_BEFORE_PERSISTENCE"
    else:
        root_cause = "EXECUTE_ONE_RESULT_PRESENT"

    print(f"root_cause={root_cause}")
    print("db_writes_performed=0")
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
        "POSTGRESQL_EDGE_BACKTEST_EXECUTE_ONE_AUDIT_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
