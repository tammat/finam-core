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

OUTPUT_DIR = pathlib.Path(
    "/tmp/regime_owner_candidates_v1"
)

SOURCE_FILES_FILE = (
    OUTPUT_DIR / "source_files.tsv"
)
FUNCTIONS_FILE = (
    OUTPUT_DIR / "regime_functions.tsv"
)
CONSTRUCTORS_FILE = (
    OUTPUT_DIR / "regime_constructors.tsv"
)
ASSIGNMENTS_FILE = (
    OUTPUT_DIR / "regime_assignments.tsv"
)
RETURNS_FILE = (
    OUTPUT_DIR / "regime_returns.tsv"
)
CALLS_FILE = (
    OUTPUT_DIR / "regime_calls.tsv"
)
CANDIDATES_FILE = (
    OUTPUT_DIR / "owner_candidates.tsv"
)
EXCLUDED_FILE = (
    OUTPUT_DIR / "excluded_candidates.tsv"
)
SUMMARY_FILE = (
    OUTPUT_DIR / "family_summary.tsv"
)
EVIDENCE_FILE = (
    OUTPUT_DIR / "evidence.txt"
)
UNRESOLVED_FILE = (
    OUTPUT_DIR / "unresolved.tsv"
)

REGIME_NAME_MARKERS = (
    "regime",
    "market_state",
    "market_phase",
    "trend_state",
    "volatility_state",
    "liquidity_state",
    "session_state",
)

REGIME_VALUE_MARKERS = {
    "TREND",
    "TRENDING",
    "RANGE",
    "RANGING",
    "BREAKOUT",
    "VOLATILE",
    "HIGH_VOLATILITY",
    "LOW_VOLATILITY",
    "CALM",
    "COMPRESSION",
    "EXPANSION",
    "BULL",
    "BEAR",
    "BULLISH",
    "BEARISH",
    "NEUTRAL",
    "UNKNOWN",
    "RISK_ON",
    "RISK_OFF",
}

REGIME_CONSTRUCTOR_MARKERS = (
    "Regime",
    "MarketRegime",
    "RegimeState",
    "MarketState",
    "RegimeResult",
    "RegimeDecision",
    "RegimeContext",
)

REGIME_METHOD_MARKERS = (
    "detect",
    "classify",
    "resolve",
    "evaluate",
    "infer",
    "calculate",
    "compute",
    "update",
    "identify",
)

KNOWN_NON_OWNER_FUNCTIONS = {
    "_on_quote_impl",
    "_record_live_quote_to_storage",
    "_execute_br_signal_in_paper",
    "_process_br_closed_bar_for_paper_signal",
    "_process_ng_m1_closed_bar_for_paper_signal",
    "_process_equity_closed_bar_for_paper_signal",
}

EXCLUDED_PATH_MARKERS = (
    "/presentation/",
    "/workspace_v2/",
    "/storage/",
    "/scripts/",
    "/tests/",
)

EXCLUDED_CLASS_MARKERS = (
    "Renderer",
    "ReadModel",
    "Repository",
    "Serializer",
    "Presenter",
    "ExecutionDispatcher",
    "OrdersClient",
    "PortfolioRiskGate",
)

SIDE_EFFECT_CALL_MARKERS = (
    "place_order",
    "send_order",
    "submit_order",
    "place_limit_order",
    "place_market_order",
    "execute_order",
    "orders_client",
    "systemctl",
)

SUPPORT_FUNCTION_MARKERS = (
    "_save_",
    "_persist_",
    "_log_",
    "_audit_",
    "_render_",
    "_serialize_",
    "_publish_",
    "_notify_",
    "_format_",
)

ACTIVE_FAMILIES = (
    "BR",
    "NG",
    "EQUITY",
    "GENERIC",
)


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
        return (
            f"{parent}.{node.attr}"
            if parent
            else node.attr
        )

    if isinstance(node, ast.Subscript):
        return dotted_name(node.value)

    return ""


def source_text(
    source: str,
    node: ast.AST | None,
) -> str:
    if node is None:
        return ""

    try:
        return (
            ast.get_source_segment(
                source,
                node,
            )
            or ""
        )
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


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.split(
            r"[^a-z0-9]+",
            text.lower(),
        )
        if token
    }


def classify_family(
    path: str,
    class_name: str,
    function_name: str,
) -> str:
    raw = (
        f"{path} {class_name} "
        f"{function_name}"
    )
    tokens = tokenize(raw)
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

            relative = str(
                path.resolve().relative_to(ROOT)
            )

            if any(
                marker in f"/{relative}"
                for marker in EXCLUDED_PATH_MARKERS
            ):
                continue

            result.add(path.resolve())

    return sorted(result)


def discover_functions(
    path: pathlib.Path,
) -> tuple[ast.Module, list[FunctionInfo]]:
    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)
    relative = str(path.relative_to(ROOT))

    functions: list[FunctionInfo] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.classes: list[str] = []
            self.functions: list[str] = []

        def visit_ClassDef(
            self,
            node: ast.ClassDef,
        ) -> None:
            self.classes.append(node.name)
            self.generic_visit(node)
            self.classes.pop()

        def _visit_function(
            self,
            node: (
                ast.FunctionDef
                | ast.AsyncFunctionDef
            ),
        ) -> None:
            qualified = ".".join(
                [
                    *self.classes,
                    *self.functions,
                    node.name,
                ]
            )

            functions.append(
                FunctionInfo(
                    path=relative,
                    class_name=".".join(
                        self.classes
                    ),
                    function_name=node.name,
                    qualified_name=qualified,
                    line=node.lineno,
                    end_line=(
                        node.end_lineno
                        or node.lineno
                    ),
                    node=node,
                    source=source,
                )
            )

            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()

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

    return tree, functions


def regime_text_match(text: str) -> bool:
    lower = text.lower()

    return any(
        marker in lower
        for marker in REGIME_NAME_MARKERS
    )


def regime_value_match(text: str) -> bool:
    normalized = (
        text.upper()
        .rsplit(".", 1)[-1]
        .strip()
    )

    return normalized in REGIME_VALUE_MARKERS


def constructor_rows(
    function: FunctionInfo,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(function.node):
        if not isinstance(node, ast.Call):
            continue

        constructor = dotted_name(node.func)
        terminal = constructor.rsplit(".", 1)[-1]

        if not (
            any(
                marker.lower()
                in terminal.lower()
                for marker
                in REGIME_CONSTRUCTOR_MARKERS
            )
            or regime_text_match(constructor)
        ):
            continue

        rows.append(
            {
                "family": classify_family(
                    function.path,
                    function.class_name,
                    function.function_name,
                ),
                "path": function.path,
                "class_name": (
                    function.class_name
                ),
                "function": (
                    function.function_name
                ),
                "qualified_name": (
                    function.qualified_name
                ),
                "function_line": function.line,
                "call_line": node.lineno,
                "constructor": constructor,
                "source": source_text(
                    function.source,
                    node,
                ),
            }
        )

    return rows


def assignment_rows(
    function: FunctionInfo,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(function.node):
        if not isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):
            continue

        value = node.value

        if value is None:
            continue

        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            targets = [node.target]

        target_source = ",".join(
            source_text(
                function.source,
                target,
            )
            for target in targets
        )

        value_source = source_text(
            function.source,
            value,
        )

        if not (
            regime_text_match(target_source)
            or regime_text_match(value_source)
            or regime_value_match(
                literal_text(value)
            )
        ):
            continue

        rows.append(
            {
                "family": classify_family(
                    function.path,
                    function.class_name,
                    function.function_name,
                ),
                "path": function.path,
                "class_name": (
                    function.class_name
                ),
                "function": (
                    function.function_name
                ),
                "qualified_name": (
                    function.qualified_name
                ),
                "function_line": function.line,
                "assignment_line": node.lineno,
                "target": target_source,
                "value": value_source,
                "regime_value": int(
                    regime_value_match(
                        literal_text(value)
                    )
                ),
            }
        )

    return rows


def return_rows(
    function: FunctionInfo,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(function.node):
        if not isinstance(node, ast.Return):
            continue

        value = node.value
        value_source = source_text(
            function.source,
            value,
        )

        regime_marker = int(
            regime_text_match(value_source)
            or regime_value_match(
                literal_text(value)
            )
        )

        absence_marker = int(
            value is None
            or (
                isinstance(
                    value,
                    ast.Constant,
                )
                and value.value is None
            )
        )

        if not (
            regime_marker
            or absence_marker
        ):
            continue

        rows.append(
            {
                "family": classify_family(
                    function.path,
                    function.class_name,
                    function.function_name,
                ),
                "path": function.path,
                "class_name": (
                    function.class_name
                ),
                "function": (
                    function.function_name
                ),
                "qualified_name": (
                    function.qualified_name
                ),
                "function_line": function.line,
                "return_line": node.lineno,
                "regime_marker": regime_marker,
                "absence_marker": absence_marker,
                "return_source": value_source,
            }
        )

    return rows


def call_rows(
    function: FunctionInfo,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(function.node):
        if not isinstance(node, ast.Call):
            continue

        call = dotted_name(node.func)
        lower = call.lower()

        if not (
            regime_text_match(call)
            or any(
                marker in lower
                for marker in REGIME_METHOD_MARKERS
            )
        ):
            continue

        rows.append(
            {
                "caller_path": function.path,
                "caller_class": (
                    function.class_name
                ),
                "caller_function": (
                    function.function_name
                ),
                "caller_qualified_name": (
                    function.qualified_name
                ),
                "caller_line": function.line,
                "call_line": node.lineno,
                "call_name": call,
                "call_source": source_text(
                    function.source,
                    node,
                ),
            }
        )

    return rows


def side_effect_count(
    function: FunctionInfo,
) -> int:
    return sum(
        1
        for node in ast.walk(function.node)
        if isinstance(node, ast.Call)
        and any(
            marker in dotted_name(
                node.func
            ).lower()
            for marker
            in SIDE_EFFECT_CALL_MARKERS
        )
    )


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

    source_rows: list[
        dict[str, object]
    ] = []
    functions: list[FunctionInfo] = []
    unresolved: list[
        dict[str, object]
    ] = []

    for path in discover_files():
        relative = str(
            path.relative_to(ROOT)
        )

        try:
            tree, discovered = (
                discover_functions(path)
            )
        except (
            OSError,
            SyntaxError,
        ) as exc:
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
                    isinstance(
                        node,
                        ast.ClassDef,
                    )
                    for node in ast.walk(tree)
                ),
                "function_count": len(
                    discovered
                ),
            }
        )

    constructors: list[
        dict[str, object]
    ] = []
    assignments: list[
        dict[str, object]
    ] = []
    returns: list[
        dict[str, object]
    ] = []
    calls: list[
        dict[str, object]
    ] = []

    for function in functions:
        constructors.extend(
            constructor_rows(function)
        )
        assignments.extend(
            assignment_rows(function)
        )
        returns.extend(
            return_rows(function)
        )
        calls.extend(
            call_rows(function)
        )

    constructor_count: dict[str, int] = {}
    assignment_count: dict[str, int] = {}
    regime_return_count: dict[str, int] = {}
    absence_return_count: dict[str, int] = {}
    regime_call_count: dict[str, int] = {}

    for row in constructors:
        symbol = str(
            row["qualified_name"]
        )
        constructor_count[symbol] = (
            constructor_count.get(
                symbol,
                0,
            )
            + 1
        )

    for row in assignments:
        symbol = str(
            row["qualified_name"]
        )
        assignment_count[symbol] = (
            assignment_count.get(
                symbol,
                0,
            )
            + 1
        )

    for row in returns:
        symbol = str(
            row["qualified_name"]
        )

        if int(
            row["regime_marker"]
        ) == 1:
            regime_return_count[symbol] = (
                regime_return_count.get(
                    symbol,
                    0,
                )
                + 1
            )

        if int(
            row["absence_marker"]
        ) == 1:
            absence_return_count[symbol] = (
                absence_return_count.get(
                    symbol,
                    0,
                )
                + 1
            )

    for row in calls:
        caller = str(
            row["caller_qualified_name"]
        )
        regime_call_count[caller] = (
            regime_call_count.get(
                caller,
                0,
            )
            + 1
        )

    candidates: list[
        dict[str, object]
    ] = []
    excluded: list[
        dict[str, object]
    ] = []

    for function in functions:
        symbol = function.qualified_name

        constructors_found = (
            constructor_count.get(
                symbol,
                0,
            )
        )
        assignments_found = (
            assignment_count.get(
                symbol,
                0,
            )
        )
        regime_returns_found = (
            regime_return_count.get(
                symbol,
                0,
            )
        )
        absence_returns_found = (
            absence_return_count.get(
                symbol,
                0,
            )
        )
        calls_found = (
            regime_call_count.get(
                symbol,
                0,
            )
        )

        function_name_score = sum(
            marker
            in function.function_name.lower()
            for marker in (
                *REGIME_NAME_MARKERS,
                *REGIME_METHOD_MARKERS,
            )
        )

        class_name_score = int(
            regime_text_match(
                function.class_name
            )
        )

        side_effects = side_effect_count(
            function
        )

        score = (
            constructors_found * 7
            + assignments_found * 5
            + regime_returns_found * 6
            + min(
                absence_returns_found,
                2,
            )
            * 2
            + min(
                calls_found,
                3,
            )
            * 2
            + min(
                function_name_score,
                3,
            )
            * 3
            + class_name_score * 4
            - side_effects * 6
        )

        reason = ""

        if (
            function.function_name
            in KNOWN_NON_OWNER_FUNCTIONS
        ):
            reason = (
                "KNOWN_PIPELINE_ORCHESTRATOR"
            )

        elif any(
            marker
            in function.class_name
            for marker
            in EXCLUDED_CLASS_MARKERS
        ):
            reason = (
                "KNOWN_NON_REGIME_OWNER_CLASS"
            )

        elif any(
            marker
            in function.function_name
            for marker
            in SUPPORT_FUNCTION_MARKERS
        ):
            reason = "SUPPORT_FUNCTION"

        elif side_effects > 0:
            reason = (
                "ORDER_OR_EXECUTION_SIDE_EFFECT"
            )

        elif (
            constructors_found == 0
            and assignments_found == 0
            and regime_returns_found == 0
            and function_name_score == 0
            and class_name_score == 0
        ):
            reason = (
                "NO_REGIME_DECISION_EVIDENCE"
            )

        owner_candidate = int(
            not reason
            and score >= 10
            and (
                assignments_found > 0
                or regime_returns_found > 0
                or constructors_found > 0
            )
        )

        row = {
            "family": classify_family(
                function.path,
                function.class_name,
                function.function_name,
            ),
            "path": function.path,
            "class_name": (
                function.class_name
            ),
            "function": (
                function.function_name
            ),
            "qualified_name": symbol,
            "line": function.line,
            "constructor_count": (
                constructors_found
            ),
            "regime_assignment_count": (
                assignments_found
            ),
            "regime_return_count": (
                regime_returns_found
            ),
            "absence_return_count": (
                absence_returns_found
            ),
            "regime_call_count": (
                calls_found
            ),
            "function_name_marker_count": (
                function_name_score
            ),
            "class_name_marker_count": (
                class_name_score
            ),
            "side_effect_count": (
                side_effects
            ),
            "score": score,
            "classification": (
                "REGIME_OWNER_CANDIDATE"
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
                    "classification": (
                        "EXCLUDED"
                    ),
                    "reason": reason,
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

    function_rows = [
        {
            "family": classify_family(
                function.path,
                function.class_name,
                function.function_name,
            ),
            "path": function.path,
            "class_name": (
                function.class_name
            ),
            "function": (
                function.function_name
            ),
            "qualified_name": (
                function.qualified_name
            ),
            "line": function.line,
            "end_line": function.end_line,
        }
        for function in functions
        if (
            regime_text_match(
                function.qualified_name
            )
            or any(
                marker
                in function.function_name.lower()
                for marker
                in REGIME_METHOD_MARKERS
            )
        )
    ]

    candidate_fields = (
        "family",
        "path",
        "class_name",
        "function",
        "qualified_name",
        "line",
        "constructor_count",
        "regime_assignment_count",
        "regime_return_count",
        "absence_return_count",
        "regime_call_count",
        "function_name_marker_count",
        "class_name_marker_count",
        "side_effect_count",
        "score",
        "classification",
        "owner_confirmed",
        "runtime_instrumentation",
    )

    family_summary: list[
        dict[str, object]
    ] = []

    for family in ACTIVE_FAMILIES:
        family_rows = [
            row
            for row in candidates
            if row["family"] == family
        ]

        owner_rows = [
            row
            for row in family_rows
            if row["classification"]
            == "REGIME_OWNER_CANDIDATE"
        ]

        family_summary.append(
            {
                "family": family,
                "candidate_count": len(
                    family_rows
                ),
                "owner_candidate_count": len(
                    owner_rows
                ),
                "owner_candidate_symbols": (
                    ",".join(
                        str(
                            row[
                                "qualified_name"
                            ]
                        )
                        for row
                        in owner_rows
                    )
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    write_tsv(
        SOURCE_FILES_FILE,
        (
            "path",
            "bytes",
            "class_count",
            "function_count",
        ),
        source_rows,
    )

    write_tsv(
        FUNCTIONS_FILE,
        (
            "family",
            "path",
            "class_name",
            "function",
            "qualified_name",
            "line",
            "end_line",
        ),
        function_rows,
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
            "source",
        ),
        constructors,
    )

    write_tsv(
        ASSIGNMENTS_FILE,
        (
            "family",
            "path",
            "class_name",
            "function",
            "qualified_name",
            "function_line",
            "assignment_line",
            "target",
            "value",
            "regime_value",
        ),
        assignments,
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
            "regime_marker",
            "absence_marker",
            "return_source",
        ),
        returns,
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
        calls,
    )

    write_tsv(
        CANDIDATES_FILE,
        candidate_fields,
        candidates,
    )

    write_tsv(
        EXCLUDED_FILE,
        (
            *candidate_fields,
            "reason",
        ),
        excluded,
    )

    write_tsv(
        SUMMARY_FILE,
        (
            "family",
            "candidate_count",
            "owner_candidate_count",
            "owner_candidate_symbols",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        family_summary,
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

    owner_candidate_count = sum(
        row["classification"]
        == "REGIME_OWNER_CANDIDATE"
        for row in candidates
    )

    with EVIDENCE_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "REGIME OWNER CANDIDATES V1\n"
        )
        stream.write(
            "==========================\n\n"
        )

        for row in candidates:
            stream.write(
                f"CANDIDATE "
                f"family={row['family']} "
                f"path={row['path']} "
                f"symbol="
                f"{row['qualified_name']} "
                f"score={row['score']} "
                f"classification="
                f"{row['classification']} "
                f"constructors="
                f"{row['constructor_count']} "
                f"assignments="
                f"{row['regime_assignment_count']} "
                f"returns="
                f"{row['regime_return_count']} "
                f"calls="
                f"{row['regime_call_count']} "
                f"side_effects="
                f"{row['side_effect_count']}\n"
            )

    print(
        "=== AUDIT REGIME OWNER "
        "CANDIDATES V1 ==="
    )
    print(
        f"source_file_count="
        f"{len(source_rows)}"
    )
    print(
        f"function_count="
        f"{len(functions)}"
    )
    print(
        f"regime_function_count="
        f"{len(function_rows)}"
    )
    print(
        f"regime_constructor_count="
        f"{len(constructors)}"
    )
    print(
        f"regime_assignment_count="
        f"{len(assignments)}"
    )
    print(
        f"regime_return_count="
        f"{len(returns)}"
    )
    print(
        f"regime_call_count="
        f"{len(calls)}"
    )
    print(
        f"candidate_count="
        f"{len(candidates)}"
    )
    print(
        f"regime_owner_candidate_count="
        f"{owner_candidate_count}"
    )
    print(
        f"excluded_candidate_count="
        f"{len(excluded)}"
    )
    print(
        f"unresolved_count="
        f"{len(unresolved)}"
    )

    for row in candidates[:50]:
        print(
            f"CANDIDATE "
            f"family={row['family']} "
            f"class="
            f"{row['classification']} "
            f"score={row['score']} "
            f"path={row['path']} "
            f"symbol="
            f"{row['qualified_name']} "
            f"constructors="
            f"{row['constructor_count']} "
            f"assignments="
            f"{row['regime_assignment_count']} "
            f"returns="
            f"{row['regime_return_count']} "
            f"calls="
            f"{row['regime_call_count']} "
            f"side_effects="
            f"{row['side_effect_count']}"
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
    print(
        "VERDICT="
        "REGIME_OWNER_CANDIDATES_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
