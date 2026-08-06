#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
import re
from typing import Any


ROOT = pathlib.Path("/opt/finam-core")
OUT = pathlib.Path(
    "/tmp/edge_observation_successful_writer_discovery_v1"
)

DIRECT_FILE = OUT / "direct_writers.tsv"
INDIRECT_FILE = OUT / "indirect_candidates.tsv"
CONSUMERS_FILE = OUT / "backtest_consumers.tsv"
CONTRACT_FILE = OUT / "discovery_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

SEARCH_ROOTS = (
    ROOT / "src",
    ROOT / "scripts",
    ROOT / "core",
    ROOT / "storage",
)

TEXT_SUFFIXES = {
    ".py",
    ".sql",
    ".sh",
}

SUCCESS_METRICS = {
    "trades",
    "wins",
    "losses",
    "win_rate",
    "profit_factor",
    "expectancy",
    "avg_win",
    "avg_loss",
    "max_drawdown",
    "commission",
    "slippage",
}

WRITE_PATTERN = re.compile(
    r"\b(?:INSERT\s+INTO|UPDATE)\s+"
    r"(?:analytics\.)?edge_observation_v1\b",
    re.IGNORECASE | re.DOTALL,
)

SUCCESS_STATUS_PATTERN = re.compile(
    r"\b(?:NO_TRADES|FAILED|ERROR)\b",
    re.IGNORECASE,
)


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


def source_segment(
    source: str,
    node: ast.AST | None,
) -> str:
    if node is None:
        return ""

    return (
        ast.get_source_segment(source, node) or ""
    ).strip().replace("\n", " ")[:12000]


def enclosing_function(
    node: ast.AST,
    parents: dict[ast.AST, ast.AST],
) -> str:
    current = node

    while current in parents:
        current = parents[current]

        if isinstance(
            current,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            return current.name

    return "<module>"


def extract_string_literals(
    node: ast.AST,
) -> list[str]:
    values: list[str] = []

    for child in ast.walk(node):
        if (
            isinstance(child, ast.Constant)
            and isinstance(child.value, str)
        ):
            values.append(child.value)

        if isinstance(child, ast.JoinedStr):
            values.append(ast.unparse(child))

    return values


def classify_writer(sql_text: str) -> tuple[int, int, str]:
    normalized = " ".join(sql_text.split())
    lowered = normalized.lower()

    metric_count = sum(
        metric in lowered
        for metric in SUCCESS_METRICS
    )

    contains_blocked_status = int(
        SUCCESS_STATUS_PATTERN.search(normalized) is not None
    )

    successful_candidate = int(
        metric_count >= 5
        and not contains_blocked_status
    )

    if successful_candidate:
        classification = "SUCCESS_METRIC_WRITER_CANDIDATE"
    elif contains_blocked_status:
        classification = "NON_SUCCESS_PLACEHOLDER_WRITER"
    else:
        classification = "PARTIAL_OR_SCORE_ONLY_WRITER"

    return metric_count, successful_candidate, classification


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    direct_rows: list[dict[str, Any]] = []
    indirect_rows: list[dict[str, Any]] = []
    consumer_rows: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

    for search_root in SEARCH_ROOTS:
        if not search_root.is_dir():
            continue

        for path in search_root.rglob("*"):
            if (
                not path.is_file()
                or path.suffix not in TEXT_SUFFIXES
            ):
                continue

            relative_path = str(path.relative_to(ROOT))

            try:
                source = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError:
                continue

            if path.suffix != ".py":
                for match in WRITE_PATTERN.finditer(source):
                    fragment = source[
                        max(0, match.start() - 200):
                        min(len(source), match.start() + 4000)
                    ]

                    metric_count, successful, classification = (
                        classify_writer(fragment)
                    )

                    direct_rows.append(
                        {
                            "file_path": relative_path,
                            "function_name": "<non_python>",
                            "line_no": (
                                source[:match.start()].count("\n")
                                + 1
                            ),
                            "write_type": (
                                "INSERT"
                                if "INSERT" in match.group(0).upper()
                                else "UPDATE"
                            ),
                            "success_metric_count": metric_count,
                            "successful_writer_candidate": successful,
                            "classification": classification,
                            "sql_text": " ".join(fragment.split())[:12000],
                        }
                    )

                continue

            try:
                tree = ast.parse(source)
            except SyntaxError as error:
                unresolved.append(
                    {
                        "scope": "SOURCE_PARSE",
                        "identity": relative_path,
                        "reason": (
                            f"SYNTAX_ERROR:{error.lineno}:"
                            f"{error.msg}"
                        ),
                    }
                )
                continue

            parents: dict[ast.AST, ast.AST] = {}

            for parent in ast.walk(tree):
                for child in ast.iter_child_nodes(parent):
                    parents[child] = parent

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    call_text = source_segment(source, node)
                    string_literals = extract_string_literals(node)
                    combined_text = "\n".join(
                        [call_text, *string_literals]
                    )

                    if WRITE_PATTERN.search(combined_text):
                        metric_count, successful, classification = (
                            classify_writer(combined_text)
                        )

                        write_match = WRITE_PATTERN.search(
                            combined_text
                        )

                        direct_rows.append(
                            {
                                "file_path": relative_path,
                                "function_name": enclosing_function(
                                    node,
                                    parents,
                                ),
                                "line_no": getattr(node, "lineno", 0),
                                "write_type": (
                                    "INSERT"
                                    if write_match
                                    and "INSERT" in write_match.group(0).upper()
                                    else "UPDATE"
                                ),
                                "success_metric_count": metric_count,
                                "successful_writer_candidate": successful,
                                "classification": classification,
                                "sql_text": combined_text[:12000],
                            }
                        )

                    lowered_call = call_text.lower()

                    if (
                        "run_backtest(" in lowered_call
                        or "metrics, trades" in lowered_call
                        or "metrics, _" in lowered_call
                    ):
                        consumer_rows.append(
                            {
                                "file_path": relative_path,
                                "function_name": enclosing_function(
                                    node,
                                    parents,
                                ),
                                "line_no": getattr(node, "lineno", 0),
                                "consumer_type": "BACKTEST_CALL",
                                "text": call_text,
                            }
                        )

                    if any(
                        marker in lowered_call
                        for marker in (
                            "save",
                            "persist",
                            "upsert",
                            "repository",
                            "store",
                        )
                    ) and any(
                        metric in lowered_call
                        for metric in (
                            "profit_factor",
                            "expectancy",
                            "max_drawdown",
                            "commission",
                            "slippage",
                        )
                    ):
                        indirect_rows.append(
                            {
                                "file_path": relative_path,
                                "function_name": enclosing_function(
                                    node,
                                    parents,
                                ),
                                "line_no": getattr(node, "lineno", 0),
                                "candidate_type": "METRIC_PERSISTENCE_CALL",
                                "text": call_text,
                            }
                        )

                if isinstance(
                    node,
                    (ast.FunctionDef, ast.AsyncFunctionDef),
                ):
                    function_text = source_segment(source, node)
                    lowered_function = function_text.lower()

                    if (
                        any(
                            marker in node.name.lower()
                            for marker in (
                                "save",
                                "persist",
                                "write",
                                "store",
                                "upsert",
                            )
                        )
                        and any(
                            metric in lowered_function
                            for metric in (
                                "profit_factor",
                                "expectancy",
                                "max_drawdown",
                                "commission",
                                "slippage",
                            )
                        )
                    ):
                        indirect_rows.append(
                            {
                                "file_path": relative_path,
                                "function_name": node.name,
                                "line_no": node.lineno,
                                "candidate_type": "PERSISTENCE_FUNCTION",
                                "text": function_text,
                            }
                        )

    successful_direct_rows = [
        row
        for row in direct_rows
        if row["successful_writer_candidate"] == 1
    ]

    placeholder_rows = [
        row
        for row in direct_rows
        if row["classification"]
        == "NON_SUCCESS_PLACEHOLDER_WRITER"
    ]

    score_only_rows = [
        row
        for row in direct_rows
        if row["classification"]
        == "PARTIAL_OR_SCORE_ONLY_WRITER"
    ]

    write_tsv(
        DIRECT_FILE,
        (
            "file_path",
            "function_name",
            "line_no",
            "write_type",
            "success_metric_count",
            "successful_writer_candidate",
            "classification",
            "sql_text",
        ),
        direct_rows,
    )

    write_tsv(
        INDIRECT_FILE,
        (
            "file_path",
            "function_name",
            "line_no",
            "candidate_type",
            "text",
        ),
        indirect_rows,
    )

    write_tsv(
        CONSUMERS_FILE,
        (
            "file_path",
            "function_name",
            "line_no",
            "consumer_type",
            "text",
        ),
        consumer_rows,
    )

    if not successful_direct_rows:
        unresolved.append(
            {
                "scope": "EDGE_OBSERVATION_WRITER",
                "identity": "successful_metrics",
                "reason": "SUCCESSFUL_DIRECT_WRITER_NOT_FOUND",
            }
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

    with CONTRACT_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "EDGE OBSERVATION SUCCESSFUL WRITER DISCOVERY V1\n"
        )
        stream.write(
            "================================================\n\n"
        )
        stream.write("MODE=STATIC_READ_ONLY\n")
        stream.write(
            f"DIRECT_WRITER_COUNT={len(direct_rows)}\n"
        )
        stream.write(
            "SUCCESSFUL_DIRECT_WRITER_COUNT="
            f"{len(successful_direct_rows)}\n"
        )
        stream.write(
            f"PLACEHOLDER_WRITER_COUNT={len(placeholder_rows)}\n"
        )
        stream.write(
            f"SCORE_ONLY_WRITER_COUNT={len(score_only_rows)}\n"
        )
        stream.write(
            f"INDIRECT_CANDIDATE_COUNT={len(indirect_rows)}\n"
        )
        stream.write(
            f"BACKTEST_CONSUMER_COUNT={len(consumer_rows)}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("SOURCE_CHANGED=0\n")
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print(
        "=== EDGE OBSERVATION SUCCESSFUL "
        "WRITER DISCOVERY V1 ==="
    )
    print(f"direct_writer_count={len(direct_rows)}")
    print(
        "successful_direct_writer_count="
        f"{len(successful_direct_rows)}"
    )
    print(
        f"placeholder_writer_count={len(placeholder_rows)}"
    )
    print(f"score_only_writer_count={len(score_only_rows)}")
    print(
        f"indirect_candidate_count={len(indirect_rows)}"
    )
    print(f"backtest_consumer_count={len(consumer_rows)}")
    print(f"unresolved_count={len(unresolved)}")
    print("source_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "EDGE_OBSERVATION_SUCCESSFUL_WRITER_DISCOVERY_V1_READY"
    )

    # Отсутствие writer является допустимым результатом discovery.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
