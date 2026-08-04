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
    ROOT / "src/finam_core/strategy",
    ROOT / "strategy",
    ROOT / "src/finam_core/pipelines",
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/strategy_owner_intent_points_v1"
)

STRATEGY_FILES_FILE = OUTPUT_DIR / "strategy_files.tsv"
STRATEGY_METHODS_FILE = OUTPUT_DIR / "strategy_methods.tsv"
CONSTRUCTORS_FILE = OUTPUT_DIR / "signal_constructors.tsv"
RETURNS_FILE = OUTPUT_DIR / "signal_returns.tsv"
DIRECTIONS_FILE = OUTPUT_DIR / "direction_assignments.tsv"
CALLS_FILE = OUTPUT_DIR / "strategy_calls.tsv"
CANDIDATES_FILE = OUTPUT_DIR / "owner_candidates.tsv"
EXCLUDED_FILE = OUTPUT_DIR / "excluded_candidates.tsv"
EVIDENCE_FILE = OUTPUT_DIR / "evidence.txt"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

METHOD_NAME_MARKERS = (
    "signal",
    "intent",
    "entry",
    "generate",
    "evaluate",
    "decide",
    "decision",
    "breakout",
    "setup",
    "on_bar",
    "on_quote",
)

SIGNAL_TYPE_MARKERS = (
    "Signal",
    "TradeSignal",
    "EntrySignal",
    "OrderSignal",
    "SignalEvent",
    "TradeIntent",
    "EntryIntent",
    "ExecutionIntent",
)

DIRECTION_VALUES = {
    "BUY",
    "SELL",
    "LONG",
    "SHORT",
    "BULL",
    "BEAR",
}

DIRECTION_FIELD_MARKERS = (
    "side",
    "direction",
    "action",
    "signal",
    "position_side",
    "order_side",
)

ENTRY_FIELD_MARKERS = (
    "entry",
    "entry_price",
    "price",
    "stop",
    "stop_loss",
    "take_profit",
    "target",
    "quantity",
    "qty",
    "volume",
)

DOWNSTREAM_EXCLUDED_SYMBOLS = {
    "_on_quote_impl",
    "_execute_br_signal_in_paper",
    "ExecutionDispatcher.execute",
    "ExecutionDispatcher.place_limit_order",
    "PortfolioRiskGate.check",
    "FinamOrdersClient.place_limit_order",
    "FinamOrdersClient.place_market_order",
}

DOWNSTREAM_CALL_MARKERS = (
    "orders_client",
    "place_limit_order",
    "place_market_order",
    "send_order",
    "submit_order",
    "execute_order",
    "risk_gate",
    "PortfolioRiskGate",
)


@dataclass(frozen=True, slots=True)
class MethodInfo:
    path: str
    class_name: str
    function_name: str
    qualified_name: str
    line: int
    end_line: int
    node: ast.FunctionDef | ast.AsyncFunctionDef
    full_source: str
    source: str


def dotted_name(node: ast.AST | None) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr

    return ""


def call_name(node: ast.Call) -> str:
    return dotted_name(node.func) or "<unknown>"


def source_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    try:
        return ast.get_source_segment(source, node) or ""
    except (IndexError, ValueError):
        return ""


def literal_value(node: ast.AST | None) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Constant):
        return str(node.value)

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        return dotted_name(node)

    return ""


def strategy_family(
    path: str,
    class_name: str,
    function_name: str,
) -> str:
    raw = f"{path} {class_name} {function_name}".lower()

    # BR и NG должны определяться отдельными токенами.
    # Поиск подстроки "br" ошибочно совпадает со словом "breakout".
    tokens = {
        token
        for token in re.split(r"[^a-z0-9]+", raw)
        if token
    }

    class_lower = class_name.lower()
    path_lower = path.lower()

    if (
        "equities" in tokens
        or "equity" in tokens
        or "stock" in tokens
        or "equity" in class_lower
    ):
        return "EQUITY"

    if (
        "ng" in tokens
        or class_lower.startswith("ng")
        or "/ng_" in path_lower
        or "/futures/ng_" in path_lower
    ):
        return "NG"

    if (
        "br" in tokens
        or class_lower.startswith("br")
        or "/br_" in path_lower
        or "/futures/br_" in path_lower
    ):
        return "BR"

    if "swing" in tokens:
        return "SWING"

    if (
        "fx" in tokens
        or "currency" in tokens
    ):
        return "FX"

    return "UNCLASSIFIED"


def discover_files() -> list[pathlib.Path]:
    files: set[pathlib.Path] = set()

    for source_root in SOURCE_ROOTS:
        if not source_root.is_dir():
            continue

        for path in source_root.rglob("*.py"):
            if path.name.startswith("test_"):
                continue

            if "__pycache__" in path.parts:
                continue

            files.add(path.resolve())

    return sorted(files)


def discover_methods(
    path: pathlib.Path,
) -> tuple[str, ast.Module, list[MethodInfo]]:
    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)

    relative_path = str(path.relative_to(ROOT))
    result: list[MethodInfo] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[str] = []
            self.function_stack: list[str] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_stack.append(node.name)
            self.generic_visit(node)
            self.class_stack.pop()

        def _visit_function(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            class_name = ".".join(self.class_stack)
            names = [
                *self.class_stack,
                *self.function_stack,
                node.name,
            ]
            qualified_name = ".".join(names)

            result.append(
                MethodInfo(
                    path=relative_path,
                    class_name=class_name,
                    function_name=node.name,
                    qualified_name=qualified_name,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    node=node,
                    full_source=source,
                    source=source_text(source, node),
                )
            )

            self.function_stack.append(node.name)
            self.generic_visit(node)
            self.function_stack.pop()

        def visit_FunctionDef(
            self,
            node: ast.FunctionDef,
        ) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            self._visit_function(node)

    Visitor().visit(tree)

    return source, tree, result


def keyword_map(node: ast.Call) -> dict[str, ast.AST]:
    return {
        keyword.arg: keyword.value
        for keyword in node.keywords
        if keyword.arg is not None
    }


def signal_constructor_rows(
    method: MethodInfo,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(method.node):
        if not isinstance(node, ast.Call):
            continue

        constructor = call_name(node)
        terminal_name = constructor.rsplit(".", 1)[-1]

        constructor_marker = any(
            marker.lower() in terminal_name.lower()
            for marker in SIGNAL_TYPE_MARKERS
        )

        keywords = keyword_map(node)
        direction_keys = sorted(
            key
            for key in keywords
            if any(
                marker in key.lower()
                for marker in DIRECTION_FIELD_MARKERS
            )
        )
        entry_keys = sorted(
            key
            for key in keywords
            if any(
                marker in key.lower()
                for marker in ENTRY_FIELD_MARKERS
            )
        )

        direction_values = sorted(
            {
                literal_value(keywords[key])
                for key in direction_keys
                if literal_value(keywords[key])
            }
        )

        has_direction_value = any(
            value.upper().rsplit(".", 1)[-1]
            in DIRECTION_VALUES
            for value in direction_values
        )

        semantic_constructor = bool(
            constructor_marker
            or (
                direction_keys
                and (
                    entry_keys
                    or has_direction_value
                )
            )
        )

        if not semantic_constructor:
            continue

        rows.append(
            {
                "family": strategy_family(
                    method.path,
                    method.class_name,
                    method.function_name,
                ),
                "path": method.path,
                "class_name": method.class_name,
                "function": method.function_name,
                "qualified_name": method.qualified_name,
                "function_line": method.line,
                "call_line": node.lineno,
                "constructor": constructor,
                "direction_fields": ",".join(direction_keys),
                "direction_values": ",".join(direction_values),
                "entry_fields": ",".join(entry_keys),
                "constructor_source": source_text(
                    method.full_source,
                    node,
                ),
            }
        )

    return rows


def signal_return_rows(
    method: MethodInfo,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(method.node):
        if not isinstance(node, ast.Return):
            continue

        value = node.value
        shape = type(value).__name__ if value is not None else "None"
        value_text = source_text(method.full_source, value)
        value_lower = value_text.lower()

        signal_marker = any(
            marker.lower() in value_lower
            for marker in (
                *SIGNAL_TYPE_MARKERS,
                "signal",
                "intent",
                "buy",
                "sell",
                "long",
                "short",
            )
        )

        absence_marker = (
            value is None
            or (
                isinstance(value, ast.Constant)
                and value.value in {None, False}
            )
        )

        if not signal_marker and not absence_marker:
            continue

        rows.append(
            {
                "family": strategy_family(
                    method.path,
                    method.class_name,
                    method.function_name,
                ),
                "path": method.path,
                "class_name": method.class_name,
                "function": method.function_name,
                "qualified_name": method.qualified_name,
                "function_line": method.line,
                "return_line": node.lineno,
                "return_shape": shape,
                "signal_marker": int(signal_marker),
                "absence_marker": int(absence_marker),
                "return_source": value_text,
            }
        )

    return rows


def direction_assignment_rows(
    method: MethodInfo,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(method.node):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue

        value = node.value
        if value is None:
            continue

        value_text = source_text(method.full_source, value)
        normalized_value = literal_value(value).upper().rsplit(".", 1)[-1]

        if normalized_value not in DIRECTION_VALUES:
            continue

        targets: list[ast.AST]

        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            targets = [node.target]

        target_text = ",".join(
            source_text(method.full_source, target)
            for target in targets
        )

        rows.append(
            {
                "family": strategy_family(
                    method.path,
                    method.class_name,
                    method.function_name,
                ),
                "path": method.path,
                "class_name": method.class_name,
                "function": method.function_name,
                "qualified_name": method.qualified_name,
                "function_line": method.line,
                "assignment_line": node.lineno,
                "target": target_text,
                "direction": normalized_value,
                "value_source": value_text,
            }
        )

    return rows


def strategy_call_rows(
    method: MethodInfo,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(method.node):
        if not isinstance(node, ast.Call):
            continue

        name = call_name(node)
        lower = name.lower()

        if not any(marker in lower for marker in METHOD_NAME_MARKERS):
            continue

        rows.append(
            {
                "caller_path": method.path,
                "caller_class": method.class_name,
                "caller_function": method.function_name,
                "caller_qualified_name": method.qualified_name,
                "caller_line": method.line,
                "call_line": node.lineno,
                "call_name": name,
                "call_source": source_text(
                    method.full_source,
                    node,
                ),
            }
        )

    return rows


def downstream_side_effect_count(method: MethodInfo) -> int:
    return sum(
        1
        for node in ast.walk(method.node)
        if isinstance(node, ast.Call)
        and any(
            marker.lower() in call_name(node).lower()
            for marker in DOWNSTREAM_CALL_MARKERS
        )
    )


def candidate_rows(
    methods: list[MethodInfo],
    constructors: list[dict[str, object]],
    returns: list[dict[str, object]],
    directions: list[dict[str, object]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    constructor_count: dict[str, int] = {}
    positive_return_count: dict[str, int] = {}
    absence_return_count: dict[str, int] = {}
    direction_count: dict[str, int] = {}

    for row in constructors:
        key = str(row["qualified_name"])
        constructor_count[key] = constructor_count.get(key, 0) + 1

    for row in returns:
        key = str(row["qualified_name"])

        if int(row["signal_marker"]) == 1:
            positive_return_count[key] = (
                positive_return_count.get(key, 0) + 1
            )

        if int(row["absence_marker"]) == 1:
            absence_return_count[key] = (
                absence_return_count.get(key, 0) + 1
            )

    for row in directions:
        key = str(row["qualified_name"])
        direction_count[key] = direction_count.get(key, 0) + 1

    candidates: list[dict[str, object]] = []
    excluded: list[dict[str, object]] = []

    for method in methods:
        key = method.qualified_name
        constructor_hits = constructor_count.get(key, 0)
        positive_returns = positive_return_count.get(key, 0)
        absence_returns = absence_return_count.get(key, 0)
        direction_hits = direction_count.get(key, 0)
        method_name_hits = sum(
            marker in method.function_name.lower()
            for marker in METHOD_NAME_MARKERS
        )
        downstream_hits = downstream_side_effect_count(method)

        score = (
            constructor_hits * 6
            + positive_returns * 5
            + direction_hits * 4
            + min(absence_returns, 2) * 2
            + min(method_name_hits, 3) * 2
            - downstream_hits * 4
        )

        exclusion_reason = ""

        if key in DOWNSTREAM_EXCLUDED_SYMBOLS:
            exclusion_reason = "KNOWN_NON_STRATEGY_OWNER"

        elif method.function_name in {
            "_on_quote_impl",
            "_execute_br_signal_in_paper",
        }:
            exclusion_reason = "KNOWN_ORCHESTRATION_OR_RUNTIME_GATE"

        elif downstream_hits > 0 and (
            constructor_hits == 0
            and positive_returns == 0
        ):
            exclusion_reason = "DOWNSTREAM_SIDE_EFFECT_BOUNDARY"

        elif (
            constructor_hits == 0
            and positive_returns == 0
            and direction_hits == 0
        ):
            exclusion_reason = "NO_TRADE_INTENT_EVIDENCE"

        owner_candidate = int(
            not exclusion_reason
            and score >= 8
            and (
                constructor_hits > 0
                or positive_returns > 0
            )
            and direction_hits > 0
        )

        row = {
            "family": strategy_family(
                method.path,
                method.class_name,
                method.function_name,
            ),
            "path": method.path,
            "class_name": method.class_name,
            "function": method.function_name,
            "qualified_name": method.qualified_name,
            "line": method.line,
            "constructor_count": constructor_hits,
            "positive_signal_return_count": positive_returns,
            "absence_return_count": absence_returns,
            "direction_assignment_count": direction_hits,
            "method_name_marker_count": method_name_hits,
            "downstream_side_effect_count": downstream_hits,
            "score": score,
            "classification": (
                "TRADE_INTENT_OWNER_CANDIDATE"
                if owner_candidate
                else "REVIEW_CANDIDATE"
            ),
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }

        if exclusion_reason:
            excluded.append(
                {
                    **row,
                    "classification": "EXCLUDED",
                    "reason": exclusion_reason,
                }
            )
        else:
            candidates.append(row)

    candidates.sort(
        key=lambda row: (
            str(row["family"]),
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

    return candidates, excluded


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: Iterable[dict[str, object]],
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
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    files = discover_files()
    methods: list[MethodInfo] = []
    unresolved: list[dict[str, object]] = []
    strategy_file_rows: list[dict[str, object]] = []

    for path in files:
        relative = str(path.relative_to(ROOT))

        try:
            source, tree, discovered = discover_methods(path)
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

        methods.extend(discovered)

        strategy_file_rows.append(
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

    constructor_rows: list[dict[str, object]] = []
    return_rows: list[dict[str, object]] = []
    direction_rows: list[dict[str, object]] = []
    call_rows: list[dict[str, object]] = []

    for method in methods:
        constructor_rows.extend(
            signal_constructor_rows(method)
        )
        return_rows.extend(
            signal_return_rows(method)
        )
        direction_rows.extend(
            direction_assignment_rows(method)
        )
        call_rows.extend(
            strategy_call_rows(method)
        )

    candidates, excluded = candidate_rows(
        methods,
        constructor_rows,
        return_rows,
        direction_rows,
    )

    method_rows = [
        {
            "family": strategy_family(
                method.path,
                method.class_name,
                method.function_name,
            ),
            "path": method.path,
            "class_name": method.class_name,
            "function": method.function_name,
            "qualified_name": method.qualified_name,
            "line": method.line,
            "end_line": method.end_line,
        }
        for method in methods
    ]

    write_tsv(
        STRATEGY_FILES_FILE,
        (
            "path",
            "bytes",
            "class_count",
            "function_count",
        ),
        strategy_file_rows,
    )

    write_tsv(
        STRATEGY_METHODS_FILE,
        (
            "family",
            "path",
            "class_name",
            "function",
            "qualified_name",
            "line",
            "end_line",
        ),
        method_rows,
    )

    write_tsv(
        CONSTRUCTORS_FILE,
        (
            "family",
            "path",
            "class_name",
            "function",
            "qualified_name",
            "function_line",
            "call_line",
            "constructor",
            "direction_fields",
            "direction_values",
            "entry_fields",
            "constructor_source",
        ),
        constructor_rows,
    )

    write_tsv(
        RETURNS_FILE,
        (
            "family",
            "path",
            "class_name",
            "function",
            "qualified_name",
            "function_line",
            "return_line",
            "return_shape",
            "signal_marker",
            "absence_marker",
            "return_source",
        ),
        return_rows,
    )

    write_tsv(
        DIRECTIONS_FILE,
        (
            "family",
            "path",
            "class_name",
            "function",
            "qualified_name",
            "function_line",
            "assignment_line",
            "target",
            "direction",
            "value_source",
        ),
        direction_rows,
    )

    write_tsv(
        CALLS_FILE,
        (
            "caller_path",
            "caller_class",
            "caller_function",
            "caller_qualified_name",
            "caller_line",
            "call_line",
            "call_name",
            "call_source",
        ),
        call_rows,
    )

    candidate_fields = (
        "family",
        "path",
        "class_name",
        "function",
        "qualified_name",
        "line",
        "constructor_count",
        "positive_signal_return_count",
        "absence_return_count",
        "direction_assignment_count",
        "method_name_marker_count",
        "downstream_side_effect_count",
        "score",
        "classification",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    write_tsv(
        CANDIDATES_FILE,
        candidate_fields,
        candidates,
    )

    write_tsv(
        EXCLUDED_FILE,
        (*candidate_fields, "reason"),
        excluded,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "path",
            "symbol",
            "reason",
        ),
        unresolved,
    )

    confirmed_candidate_count = sum(
        row["classification"]
        == "TRADE_INTENT_OWNER_CANDIDATE"
        for row in candidates
    )

    families = sorted(
        {
            str(row["family"])
            for row in candidates
        }
    )

    with EVIDENCE_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "STRATEGY OWNER INTENT POINTS V1\n"
        )
        stream.write(
            "================================\n\n"
        )

        for row in candidates:
            stream.write(
                f"CANDIDATE family={row['family']} "
                f"path={row['path']} "
                f"symbol={row['qualified_name']} "
                f"score={row['score']} "
                f"classification={row['classification']} "
                f"constructors={row['constructor_count']} "
                f"signal_returns="
                f"{row['positive_signal_return_count']} "
                f"absence_returns={row['absence_return_count']} "
                f"directions="
                f"{row['direction_assignment_count']} "
                f"downstream="
                f"{row['downstream_side_effect_count']}\n"
            )

    print("=== AUDIT STRATEGY OWNER INTENT POINTS V1 ===")
    print(f"source_file_count={len(strategy_file_rows)}")
    print(f"method_count={len(methods)}")
    print(f"signal_constructor_count={len(constructor_rows)}")
    print(f"signal_return_count={len(return_rows)}")
    print(f"direction_assignment_count={len(direction_rows)}")
    print(f"strategy_call_count={len(call_rows)}")
    print(f"owner_candidate_count={len(candidates)}")
    print(
        f"trade_intent_owner_candidate_count="
        f"{confirmed_candidate_count}"
    )
    print(f"excluded_candidate_count={len(excluded)}")
    print(f"strategy_family_count={len(families)}")
    print(f"unresolved_count={len(unresolved)}")

    for row in candidates[:40]:
        print(
            f"CANDIDATE family={row['family']} "
            f"class={row['classification']} "
            f"score={row['score']} "
            f"path={row['path']} "
            f"symbol={row['qualified_name']} "
            f"constructors={row['constructor_count']} "
            f"signal_returns="
            f"{row['positive_signal_return_count']} "
            f"absence_returns={row['absence_return_count']} "
            f"directions={row['direction_assignment_count']} "
            f"downstream="
            f"{row['downstream_side_effect_count']}"
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
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "STRATEGY_OWNER_INTENT_POINTS_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
