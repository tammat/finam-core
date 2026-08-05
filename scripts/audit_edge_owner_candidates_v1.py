#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
import re
from dataclasses import dataclass
from typing import Iterable


ROOT = pathlib.Path("/opt/finam-core").resolve()

SOURCE_ROOTS = (
    ROOT / "src/finam_core",
    ROOT / "core",
    ROOT / "strategy",
    ROOT / "risk",
)

OUT = pathlib.Path("/tmp/edge_owner_candidates_v1")

SOURCE_FILES_FILE = OUT / "source_files.tsv"
FUNCTIONS_FILE = OUT / "edge_functions.tsv"
ASSIGNMENTS_FILE = OUT / "edge_assignments.tsv"
RETURNS_FILE = OUT / "edge_returns.tsv"
CALLS_FILE = OUT / "edge_calls.tsv"
CANDIDATES_FILE = OUT / "owner_candidates.tsv"
EXCLUDED_FILE = OUT / "excluded_candidates.tsv"
SUMMARY_FILE = OUT / "candidate_summary.tsv"
EVIDENCE_FILE = OUT / "evidence.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

EDGE_NAME_MARKERS = (
    "edge",
    "expectancy",
    "profit_factor",
    "profitability",
    "economic_score",
    "edge_score",
    "edge_quality",
    "edge_confidence",
    "robustness",
    "out_of_sample",
    "oos",
    "walk_forward",
)

EDGE_DECISION_MARKERS = (
    "allow",
    "approve",
    "accept",
    "confirm",
    "validate",
    "qualify",
    "reject",
    "deny",
    "block",
    "eligible",
    "candidate",
    "decision",
    "gate",
)

EDGE_METRIC_MARKERS = (
    "expectancy",
    "profit_factor",
    "net_pnl",
    "win_rate",
    "winrate",
    "sharpe",
    "sortino",
    "drawdown",
    "sample_size",
    "trade_count",
    "robustness",
    "stability",
    "confidence",
    "commission",
    "slippage",
)

EDGE_VALUE_MARKERS = {
    "EDGE_CONFIRMED",
    "EDGE_REJECTED",
    "EDGE_CANDIDATE",
    "RESEARCH_CANDIDATE",
    "ROBUST",
    "NOT_ROBUST",
    "APPROVED",
    "REJECTED",
    "ELIGIBLE",
    "NOT_ELIGIBLE",
    "PASS",
    "FAIL",
}

SIDE_EFFECT_MARKERS = (
    "place_order",
    "send_order",
    "submit_order",
    "place_limit_order",
    "place_market_order",
    "execute_order",
    "orders_client",
)

SUPPORT_FUNCTION_MARKERS = (
    "_save_",
    "_persist_",
    "_log_",
    "_render_",
    "_serialize_",
    "_publish_",
    "_notify_",
    "_format_",
)

EXCLUDED_PATH_MARKERS = (
    "/presentation/",
    "/workspace_v2/",
    "/storage/",
    "/adapters/grpc/",
)

EXCLUDED_CLASS_MARKERS = (
    "Renderer",
    "Presenter",
    "Serializer",
    "Repository",
    "OrdersClient",
    "ExecutionDispatcher",
)

KNOWN_ORCHESTRATORS = {
    "_on_quote_impl",
    "_record_live_quote_to_storage",
    "_execute_br_signal_in_paper",
    "_process_br_closed_bar_for_paper_signal",
    "_process_ng_m1_closed_bar_for_paper_signal",
    "_process_equity_closed_bar_for_paper_signal",
}


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    path: str
    class_name: str
    function_name: str
    qualified_name: str
    line: int
    end_line: int
    node: ast.FunctionDef | ast.AsyncFunctionDef
    source: str


def dotted_name(node: ast.AST | None) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    if isinstance(node, ast.Subscript):
        return dotted_name(node.value)

    return ""


def source_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    try:
        return ast.get_source_segment(source, node) or ""
    except (IndexError, ValueError):
        return ""


def literal_text(node: ast.AST | None) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Constant):
        return str(node.value)

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return dotted_name(node)

    return ""


def tokens(text: str) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", text.lower())
        if token
    }


def marker_count(text: str, markers: tuple[str, ...]) -> int:
    lower = text.lower()

    return sum(marker in lower for marker in markers)


def edge_value(text: str) -> bool:
    normalized = text.upper().rsplit(".", 1)[-1].strip()
    return normalized in EDGE_VALUE_MARKERS


def classify_scope(path: str, class_name: str, function_name: str) -> str:
    raw = f"{path} {class_name} {function_name}".lower()
    token_set = tokens(raw)

    if "research" in token_set or "/research/" in raw:
        return "RESEARCH"

    if "analytics" in token_set or "/analytics/" in raw:
        return "ANALYTICS"

    if "runtime" in token_set or "/runtime/" in raw:
        return "RUNTIME"

    if "strategy" in token_set or "/strategy/" in raw:
        return "STRATEGY"

    if "risk" in token_set or "/risk/" in raw:
        return "RISK"

    return "GENERIC"


def discover_files() -> list[pathlib.Path]:
    result: set[pathlib.Path] = set()

    for source_root in SOURCE_ROOTS:
        if not source_root.is_dir():
            continue

        for path in source_root.rglob("*.py"):
            if "__pycache__" in path.parts:
                continue

            if path.name.startswith("test_"):
                continue

            relative = str(path.resolve().relative_to(ROOT))

            if any(marker in f"/{relative}" for marker in EXCLUDED_PATH_MARKERS):
                continue

            result.add(path.resolve())

    return sorted(result)


def discover_functions(
    path: pathlib.Path,
) -> tuple[ast.Module, list[FunctionInfo]]:
    source = path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(source)
    relative = str(path.relative_to(ROOT))
    functions: list[FunctionInfo] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []
            self.function_stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            self._visit_function(node)

        def _visit_function(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            qualified = ".".join(
                [
                    *self.class_stack,
                    *self.function_stack,
                    node.name,
                ]
            )

            functions.append(
                FunctionInfo(
                    path=relative,
                    class_name=".".join(self.class_stack),
                    function_name=node.name,
                    qualified_name=qualified,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    node=node,
                    source=source,
                )
            )

            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

    Visitor().visit(tree)

    return tree, functions


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: Iterable[dict[str, object]],
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

    source_rows: list[dict[str, object]] = []
    functions: list[FunctionInfo] = []
    unresolved: list[dict[str, object]] = []

    for path in discover_files():
        relative = str(path.relative_to(ROOT))

        try:
            tree, discovered = discover_functions(path)
        except (OSError, SyntaxError) as exc:
            unresolved.append(
                {
                    "scope": "SOURCE_FILE",
                    "path": relative,
                    "symbol": "",
                    "reason": str(exc),
                }
            )
            continue

        functions.extend(discovered)

        source_rows.append(
            {
                "path": relative,
                "bytes": path.stat().st_size,
                "class_count": sum(
                    isinstance(node, ast.ClassDef)
                    for node in ast.walk(tree)
                ),
                "function_count": len(discovered),
            }
        )

    assignment_rows: list[dict[str, object]] = []
    return_rows: list[dict[str, object]] = []
    call_rows: list[dict[str, object]] = []

    candidates: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []
    edge_function_rows: list[dict[str, object]] = []

    for function in functions:
        assignment_count = 0
        metric_assignment_count = 0
        decision_return_count = 0
        edge_return_count = 0
        edge_call_count = 0
        side_effect_count = 0

        function_source = source_text(function.source, function.node)
        function_marker_count = marker_count(
            function.qualified_name,
            EDGE_NAME_MARKERS,
        )
        decision_name_count = marker_count(
            function.qualified_name,
            EDGE_DECISION_MARKERS,
        )
        metric_source_count = marker_count(
            function_source,
            EDGE_METRIC_MARKERS,
        )

        for node in ast.walk(function.node):
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                value = node.value

                if value is None:
                    continue

                if isinstance(node, ast.Assign):
                    targets = node.targets
                else:
                    targets = [node.target]

                target_source = ",".join(
                    source_text(function.source, target)
                    for target in targets
                )
                value_source = source_text(function.source, value)
                combined = f"{target_source} {value_source}"

                edge_marker = marker_count(combined, EDGE_NAME_MARKERS)
                metric_marker = marker_count(combined, EDGE_METRIC_MARKERS)

                if edge_marker or metric_marker:
                    assignment_count += 1
                    metric_assignment_count += int(metric_marker > 0)

                    assignment_rows.append(
                        {
                            "scope": classify_scope(
                                function.path,
                                function.class_name,
                                function.function_name,
                            ),
                            "path": function.path,
                            "qualified_name": function.qualified_name,
                            "function_line": function.line,
                            "assignment_line": node.lineno,
                            "target": target_source,
                            "value": value_source,
                            "edge_marker_count": edge_marker,
                            "metric_marker_count": metric_marker,
                        }
                    )

            elif isinstance(node, ast.Return):
                value_source = source_text(function.source, node.value)
                literal = literal_text(node.value)

                has_edge = (
                    marker_count(value_source, EDGE_NAME_MARKERS) > 0
                    or edge_value(literal)
                )
                has_decision = (
                    marker_count(value_source, EDGE_DECISION_MARKERS) > 0
                    or edge_value(literal)
                )

                if has_edge or has_decision:
                    edge_return_count += int(has_edge)
                    decision_return_count += int(has_decision)

                    return_rows.append(
                        {
                            "scope": classify_scope(
                                function.path,
                                function.class_name,
                                function.function_name,
                            ),
                            "path": function.path,
                            "qualified_name": function.qualified_name,
                            "function_line": function.line,
                            "return_line": node.lineno,
                            "edge_marker": int(has_edge),
                            "decision_marker": int(has_decision),
                            "return_source": value_source,
                        }
                    )

            elif isinstance(node, ast.Call):
                call = dotted_name(node.func)
                lower = call.lower()

                if any(marker in lower for marker in SIDE_EFFECT_MARKERS):
                    side_effect_count += 1

                if (
                    marker_count(call, EDGE_NAME_MARKERS) > 0
                    or (
                        marker_count(call, EDGE_DECISION_MARKERS) > 0
                        and marker_count(function_source, EDGE_NAME_MARKERS) > 0
                    )
                ):
                    edge_call_count += 1

                    call_rows.append(
                        {
                            "scope": classify_scope(
                                function.path,
                                function.class_name,
                                function.function_name,
                            ),
                            "path": function.path,
                            "caller": function.qualified_name,
                            "caller_line": function.line,
                            "call_line": node.lineno,
                            "call_name": call,
                            "call_source": source_text(function.source, node),
                        }
                    )

        raw_score = (
            function_marker_count * 8
            + decision_name_count * 3
            + assignment_count * 5
            + metric_assignment_count * 4
            + edge_return_count * 7
            + decision_return_count * 5
            + min(edge_call_count, 5) * 2
            + min(metric_source_count, 8)
            - side_effect_count * 8
        )

        reason = ""

        if function.function_name in KNOWN_ORCHESTRATORS:
            reason = "KNOWN_PIPELINE_ORCHESTRATOR"

        elif any(
            marker in function.class_name
            for marker in EXCLUDED_CLASS_MARKERS
        ):
            reason = "KNOWN_NON_EDGE_OWNER_CLASS"

        elif any(
            marker in function.function_name
            for marker in SUPPORT_FUNCTION_MARKERS
        ):
            reason = "SUPPORT_FUNCTION"

        elif side_effect_count > 0:
            reason = "ORDER_OR_EXECUTION_SIDE_EFFECT"

        elif (
            function_marker_count == 0
            and assignment_count == 0
            and edge_return_count == 0
            and decision_return_count == 0
        ):
            reason = "NO_EDGE_DECISION_EVIDENCE"

        owner_candidate = int(
            not reason
            and raw_score >= 15
            and (
                edge_return_count > 0
                or decision_return_count > 0
                or (
                    assignment_count > 0
                    and function_marker_count > 0
                )
            )
        )

        row = {
            "scope": classify_scope(
                function.path,
                function.class_name,
                function.function_name,
            ),
            "path": function.path,
            "class_name": function.class_name,
            "function": function.function_name,
            "qualified_name": function.qualified_name,
            "line": function.line,
            "edge_name_marker_count": function_marker_count,
            "decision_name_marker_count": decision_name_count,
            "edge_assignment_count": assignment_count,
            "metric_assignment_count": metric_assignment_count,
            "edge_return_count": edge_return_count,
            "decision_return_count": decision_return_count,
            "edge_call_count": edge_call_count,
            "metric_source_count": metric_source_count,
            "side_effect_count": side_effect_count,
            "score": raw_score,
            "classification": (
                "EDGE_OWNER_CANDIDATE"
                if owner_candidate
                else "REVIEW_CANDIDATE"
            ),
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }

        if reason:
            excluded.append(
                {
                    **row,
                    "classification": "EXCLUDED",
                    "reason": reason,
                }
            )
        elif raw_score > 0:
            candidates.append(row)

        if (
            function_marker_count > 0
            or assignment_count > 0
            or edge_return_count > 0
            or decision_return_count > 0
        ):
            edge_function_rows.append(
                {
                    "scope": row["scope"],
                    "path": function.path,
                    "class_name": function.class_name,
                    "function": function.function_name,
                    "qualified_name": function.qualified_name,
                    "line": function.line,
                    "end_line": function.end_line,
                }
            )

    candidates.sort(
        key=lambda row: (
            str(row["scope"]),
            -int(row["score"]),
            str(row["path"]),
            int(row["line"]),
        )
    )

    excluded.sort(
        key=lambda row: (
            str(row["reason"]),
            str(row["path"]),
            int(row["line"]),
        )
    )

    summary: list[dict[str, object]] = []

    for scope in ("RESEARCH", "ANALYTICS", "RUNTIME", "STRATEGY", "RISK", "GENERIC"):
        rows = [row for row in candidates if row["scope"] == scope]

        owner_rows = [
            row
            for row in rows
            if row["classification"] == "EDGE_OWNER_CANDIDATE"
        ]

        summary.append(
            {
                "scope": scope,
                "candidate_count": len(rows),
                "owner_candidate_count": len(owner_rows),
                "owner_candidate_symbols": ",".join(
                    str(row["qualified_name"])
                    for row in owner_rows
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    candidate_fields = (
        "scope",
        "path",
        "class_name",
        "function",
        "qualified_name",
        "line",
        "edge_name_marker_count",
        "decision_name_marker_count",
        "edge_assignment_count",
        "metric_assignment_count",
        "edge_return_count",
        "decision_return_count",
        "edge_call_count",
        "metric_source_count",
        "side_effect_count",
        "score",
        "classification",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    write_tsv(
        SOURCE_FILES_FILE,
        ("path", "bytes", "class_count", "function_count"),
        source_rows,
    )

    write_tsv(
        FUNCTIONS_FILE,
        (
            "scope",
            "path",
            "class_name",
            "function",
            "qualified_name",
            "line",
            "end_line",
        ),
        edge_function_rows,
    )

    write_tsv(
        ASSIGNMENTS_FILE,
        (
            "scope",
            "path",
            "qualified_name",
            "function_line",
            "assignment_line",
            "target",
            "value",
            "edge_marker_count",
            "metric_marker_count",
        ),
        assignment_rows,
    )

    write_tsv(
        RETURNS_FILE,
        (
            "scope",
            "path",
            "qualified_name",
            "function_line",
            "return_line",
            "edge_marker",
            "decision_marker",
            "return_source",
        ),
        return_rows,
    )

    write_tsv(
        CALLS_FILE,
        (
            "scope",
            "path",
            "caller",
            "caller_line",
            "call_line",
            "call_name",
            "call_source",
        ),
        call_rows,
    )

    write_tsv(CANDIDATES_FILE, candidate_fields, candidates)

    write_tsv(
        EXCLUDED_FILE,
        (*candidate_fields, "reason"),
        excluded,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "scope",
            "candidate_count",
            "owner_candidate_count",
            "owner_candidate_symbols",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        summary,
    )

    write_tsv(
        UNRESOLVED_FILE,
        ("scope", "path", "symbol", "reason"),
        unresolved,
    )

    owner_candidate_count = sum(
        row["classification"] == "EDGE_OWNER_CANDIDATE"
        for row in candidates
    )

    with EVIDENCE_FILE.open("w", encoding="utf-8") as stream:
        stream.write("EDGE OWNER CANDIDATES V1\n")
        stream.write("========================\n\n")

        for row in candidates:
            stream.write(
                f"CANDIDATE scope={row['scope']} "
                f"symbol={row['qualified_name']} "
                f"path={row['path']} "
                f"score={row['score']} "
                f"classification={row['classification']} "
                f"assignments={row['edge_assignment_count']} "
                f"returns={row['edge_return_count']} "
                f"decisions={row['decision_return_count']} "
                f"calls={row['edge_call_count']} "
                f"side_effects={row['side_effect_count']}\n"
            )

    print("=== AUDIT EDGE OWNER CANDIDATES V1 ===")
    print(f"source_file_count={len(source_rows)}")
    print(f"function_count={len(functions)}")
    print(f"edge_function_count={len(edge_function_rows)}")
    print(f"edge_assignment_count={len(assignment_rows)}")
    print(f"edge_return_count={len(return_rows)}")
    print(f"edge_call_count={len(call_rows)}")
    print(f"candidate_count={len(candidates)}")
    print(f"edge_owner_candidate_count={owner_candidate_count}")
    print(f"excluded_candidate_count={len(excluded)}")
    print(f"unresolved_count={len(unresolved)}")

    for row in candidates[:60]:
        print(
            f"CANDIDATE scope={row['scope']} "
            f"class={row['classification']} "
            f"score={row['score']} "
            f"path={row['path']} "
            f"symbol={row['qualified_name']} "
            f"assignments={row['edge_assignment_count']} "
            f"returns={row['edge_return_count']} "
            f"decisions={row['decision_return_count']} "
            f"calls={row['edge_call_count']} "
            f"side_effects={row['side_effect_count']}"
        )

    print("confirmed_owner_count=0")
    print("owner_assignment_performed=0")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_OWNER_CANDIDATES_V1_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
