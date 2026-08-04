#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core").resolve()

PIPELINE_FILE = ROOT / "src/finam_core/pipelines/paper_pipeline.py"
RISK_FILE = ROOT / "src/finam_core/risk/portfolio_risk_gate.py"

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_runtime_gate_reachability_v1"
)

CALLERS_FILE = OUTPUT_DIR / "runtime_gate_callers.tsv"
RISK_BINDINGS_FILE = OUTPUT_DIR / "risk_gate_bindings.tsv"
EXECUTION_PATH_FILE = OUTPUT_DIR / "execution_path.tsv"
EVIDENCE_FILE = OUTPUT_DIR / "evidence.txt"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

TARGET_RUNTIME_FUNCTION = "_execute_br_signal_in_paper"
TARGET_PIPELINE_FUNCTION = "_on_quote_impl"


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    name: str
    qualified_name: str
    line: int
    end_line: int
    node: ast.FunctionDef | ast.AsyncFunctionDef
    source: str


def call_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id

    if isinstance(node.func, ast.Attribute):
        parts: list[str] = []
        current: ast.expr = node.func

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    return "<unknown>"


def expr_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    return ast.get_source_segment(source, node) or ""


def functions_from_source(
    path: pathlib.Path,
) -> tuple[str, ast.Module, list[FunctionInfo]]:
    if not path.is_file():
        raise RuntimeError(f"file_missing:{path}")

    source = path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)

    functions: list[FunctionInfo] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def _visit(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            qualified = ".".join([*self.stack, node.name])

            functions.append(
                FunctionInfo(
                    name=node.name,
                    qualified_name=qualified,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    node=node,
                    source=ast.get_source_segment(source, node) or "",
                )
            )

            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

        def visit_FunctionDef(
            self,
            node: ast.FunctionDef,
        ) -> None:
            self._visit(node)

        def visit_AsyncFunctionDef(
            self,
            node: ast.AsyncFunctionDef,
        ) -> None:
            self._visit(node)

    Visitor().visit(tree)

    return source, tree, functions


def enclosing_function(
    functions: list[FunctionInfo],
    line: int,
) -> FunctionInfo | None:
    candidates = [
        function
        for function in functions
        if function.line <= line <= function.end_line
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item.end_line - item.line
    )

    return candidates[0]


def runtime_gate_callers(
    source: str,
    tree: ast.Module,
    functions: list[FunctionInfo],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = call_name(node)

        if TARGET_RUNTIME_FUNCTION not in name:
            continue

        caller = enclosing_function(
            functions,
            node.lineno,
        )

        rows.append(
            {
                "caller_function": (
                    caller.qualified_name
                    if caller is not None
                    else "<module>"
                ),
                "caller_line": (
                    caller.line
                    if caller is not None
                    else 0
                ),
                "call_line": node.lineno,
                "call_name": name,
                "call_source": expr_text(source, node),
                "inside_on_quote_impl": int(
                    caller is not None
                    and caller.name == TARGET_PIPELINE_FUNCTION
                ),
            }
        )

    return rows


def alias_bindings(
    source: str,
    tree: ast.Module,
    functions: list[FunctionInfo],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(tree):
        if not isinstance(
            node,
            (ast.Assign, ast.AnnAssign),
        ):
            continue

        value = node.value

        if value is None:
            continue

        value_text = expr_text(source, value)

        if TARGET_RUNTIME_FUNCTION not in value_text:
            continue

        targets: list[ast.expr]

        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        else:
            targets = [node.target]

        caller = enclosing_function(
            functions,
            node.lineno,
        )

        for target in targets:
            rows.append(
                {
                    "caller_function": (
                        caller.qualified_name
                        if caller is not None
                        else "<module>"
                    ),
                    "caller_line": (
                        caller.line
                        if caller is not None
                        else 0
                    ),
                    "binding_line": node.lineno,
                    "target": expr_text(source, target),
                    "value": value_text,
                    "binding_type": "FUNCTION_ALIAS_OR_DISPATCH_BINDING",
                }
            )

    return rows


def risk_gate_bindings(
    source: str,
    tree: ast.Module,
    functions: list[FunctionInfo],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    on_quote = next(
        (
            function
            for function in functions
            if function.name == TARGET_PIPELINE_FUNCTION
        ),
        None,
    )

    if on_quote is None:
        return rows

    aliases: dict[str, str] = {}

    for node in ast.walk(on_quote.node):
        if isinstance(node, ast.Assign):
            value_text = expr_text(source, node.value)

            for target in node.targets:
                if isinstance(target, ast.Name):
                    aliases[target.id] = value_text

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                aliases[node.target.id] = expr_text(
                    source,
                    node.value,
                )

    for node in ast.walk(on_quote.node):
        if not isinstance(node, ast.Call):
            continue

        name = call_name(node)

        if not name.endswith(".check"):
            continue

        receiver = name.rsplit(".", 1)[0]
        binding = aliases.get(receiver, "")

        rows.append(
            {
                "call_line": node.lineno,
                "call_name": name,
                "receiver": receiver,
                "receiver_binding": binding,
                "portfolio_risk_marker": int(
                    "portfolio_risk" in binding.lower()
                    or "PortfolioRiskGate" in binding
                    or "portfolio_risk" in name.lower()
                ),
                "trend_filter_marker": int(
                    "trend_filter" in name.lower()
                    or "trend_filter" in binding.lower()
                ),
                "call_source": expr_text(source, node),
            }
        )

    return rows


def execution_path_rows(
    callers: list[dict[str, object]],
    aliases: list[dict[str, object]],
) -> list[dict[str, object]]:
    direct_from_on_quote = any(
        int(row["inside_on_quote_impl"]) == 1
        for row in callers
    )

    indirect_binding_present = bool(aliases)

    return [
        {
            "edge": "PIPELINE_TO_RUNTIME_GATE",
            "direct_call_present": int(direct_from_on_quote),
            "runtime_gate_caller_count": len(callers),
            "alias_or_dispatch_binding_count": len(aliases),
            "classification": (
                "DIRECT_REACHABLE"
                if direct_from_on_quote
                else (
                    "INDIRECT_BINDING_CANDIDATE"
                    if indirect_binding_present
                    else "NOT_REACHABLE_FROM_ON_QUOTE_IMPL"
                )
            ),
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }
    ]


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
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

    source, tree, functions = functions_from_source(
        PIPELINE_FILE
    )

    callers = runtime_gate_callers(
        source,
        tree,
        functions,
    )
    aliases = alias_bindings(
        source,
        tree,
        functions,
    )
    risk_bindings = risk_gate_bindings(
        source,
        tree,
        functions,
    )
    execution_path = execution_path_rows(
        callers,
        aliases,
    )

    unresolved: list[dict[str, object]] = []

    if not callers and not aliases:
        unresolved.append(
            {
                "scope": "RUNTIME_GATE",
                "symbol": TARGET_RUNTIME_FUNCTION,
                "reason": (
                    "NO_DIRECT_CALL_OR_ALIAS_BINDING_FOUND"
                ),
            }
        )

    portfolio_risk_matches = [
        row
        for row in risk_bindings
        if int(row["portfolio_risk_marker"]) == 1
    ]

    if not portfolio_risk_matches:
        unresolved.append(
            {
                "scope": "RISK_GATE",
                "symbol": "gate.check",
                "reason": (
                    "PORTFOLIO_RISK_GATE_BINDING_NOT_PROVEN"
                ),
            }
        )

    write_tsv(
        CALLERS_FILE,
        (
            "caller_function",
            "caller_line",
            "call_line",
            "call_name",
            "call_source",
            "inside_on_quote_impl",
        ),
        callers,
    )

    write_tsv(
        RISK_BINDINGS_FILE,
        (
            "call_line",
            "call_name",
            "receiver",
            "receiver_binding",
            "portfolio_risk_marker",
            "trend_filter_marker",
            "call_source",
        ),
        risk_bindings,
    )

    write_tsv(
        EXECUTION_PATH_FILE,
        (
            "edge",
            "direct_call_present",
            "runtime_gate_caller_count",
            "alias_or_dispatch_binding_count",
            "classification",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        execution_path,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "symbol",
            "reason",
        ),
        unresolved,
    )

    with EVIDENCE_FILE.open(
        "w",
        encoding="utf-8",
    ) as stream:
        stream.write(
            "DECISION OWNER RUNTIME GATE REACHABILITY V1\n"
        )
        stream.write(
            "===========================================\n\n"
        )

        stream.write("[RUNTIME_GATE_CALLERS]\n")

        for row in callers:
            stream.write(
                f"caller={row['caller_function']} "
                f"call_line={row['call_line']} "
                f"call={row['call_name']}\n"
            )

        stream.write("\n[ALIASES]\n")

        for row in aliases:
            stream.write(
                f"caller={row['caller_function']} "
                f"target={row['target']} "
                f"value={row['value']}\n"
            )

        stream.write("\n[RISK_BINDINGS]\n")

        for row in risk_bindings:
            stream.write(
                f"call={row['call_name']} "
                f"binding={row['receiver_binding']} "
                f"portfolio_risk="
                f"{row['portfolio_risk_marker']} "
                f"trend_filter="
                f"{row['trend_filter_marker']}\n"
            )

    print(
        "=== AUDIT DECISION OWNER RUNTIME "
        "GATE REACHABILITY V1 ==="
    )
    print(
        f"runtime_gate_caller_count={len(callers)}"
    )
    print(
        f"runtime_gate_alias_count={len(aliases)}"
    )
    print(
        f"risk_check_call_count={len(risk_bindings)}"
    )
    print(
        f"portfolio_risk_binding_count="
        f"{len(portfolio_risk_matches)}"
    )
    print(
        f"pipeline_to_runtime_gate_classification="
        f"{execution_path[0]['classification']}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for row in callers:
        print(
            f"RUNTIME_CALLER function="
            f"{row['caller_function']} "
            f"call_line={row['call_line']} "
            f"inside_on_quote_impl="
            f"{row['inside_on_quote_impl']}"
        )

    for row in risk_bindings:
        print(
            f"RISK_BINDING call={row['call_name']} "
            f"binding={row['receiver_binding']} "
            f"portfolio_risk="
            f"{row['portfolio_risk_marker']} "
            f"trend_filter={row['trend_filter_marker']}"
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
        "DECISION_OWNER_RUNTIME_GATE_REACHABILITY_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
