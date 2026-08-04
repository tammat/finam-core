#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
import pathlib
from dataclasses import dataclass
from typing import Iterable


ROOT = pathlib.Path("/opt/finam-core").resolve()
PIPELINE_FILE = (
    ROOT / "src/finam_core/pipelines/paper_pipeline.py"
)

OUTPUT_DIR = pathlib.Path(
    "/tmp/decision_owner_runtime_caller_chain_v2"
)

RUNTIME_CALLS_FILE = OUTPUT_DIR / "runtime_call_sites.tsv"
CALLER_PARENTS_FILE = OUTPUT_DIR / "runtime_caller_parents.tsv"
RISK_USAGE_FILE = OUTPUT_DIR / "risk_result_usage.tsv"
BRANCH_FILE = OUTPUT_DIR / "branch_contract.tsv"
EVIDENCE_FILE = OUTPUT_DIR / "evidence.txt"
UNRESOLVED_FILE = OUTPUT_DIR / "unresolved.tsv"

RUNTIME_TARGET = "_execute_br_signal_in_paper"

RUNTIME_CALLERS = (
    "_process_ng_m1_closed_bar_for_paper_signal",
    "_process_br_closed_bar_for_paper_signal",
)


@dataclass(frozen=True, slots=True)
class FunctionInfo:
    name: str
    qualified_name: str
    line: int
    end_line: int
    node: ast.FunctionDef | ast.AsyncFunctionDef
    source: str


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)

        if parent:
            return f"{parent}.{node.attr}"

        return node.attr

    return ""


def call_name(node: ast.Call) -> str:
    return dotted_name(node.func) or "<unknown>"


def source_text(source: str, node: ast.AST | None) -> str:
    if node is None:
        return ""

    return ast.get_source_segment(source, node) or ""


def load_source() -> tuple[str, ast.Module, list[FunctionInfo]]:
    if not PIPELINE_FILE.is_file():
        raise RuntimeError(
            f"pipeline_file_missing:{PIPELINE_FILE}"
        )

    source = PIPELINE_FILE.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source)

    functions: list[FunctionInfo] = []

    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.stack: list[str] = []

        def _visit_function(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef,
        ) -> None:
            qualified_name = ".".join(
                [*self.stack, node.name]
            )

            functions.append(
                FunctionInfo(
                    name=node.name,
                    qualified_name=qualified_name,
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    node=node,
                    source=source_text(source, node),
                )
            )

            self.stack.append(node.name)
            self.generic_visit(node)
            self.stack.pop()

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

    return source, tree, functions


def enclosing_function(
    functions: Iterable[FunctionInfo],
    line: int,
) -> FunctionInfo | None:
    matches = [
        function
        for function in functions
        if function.line <= line <= function.end_line
    ]

    if not matches:
        return None

    return min(
        matches,
        key=lambda function: (
            function.end_line - function.line
        ),
    )


def ancestors(
    root: ast.AST,
) -> dict[ast.AST, ast.AST]:
    result: dict[ast.AST, ast.AST] = {}

    for parent in ast.walk(root):
        for child in ast.iter_child_nodes(parent):
            result[child] = parent

    return result


def nearest_guard(
    node: ast.AST,
    parent_index: dict[ast.AST, ast.AST],
    source: str,
) -> tuple[str, int]:
    current = node

    while current in parent_index:
        current = parent_index[current]

        if isinstance(current, ast.If):
            return (
                source_text(source, current.test),
                current.lineno,
            )

    return "", 0


def assigned_target(
    call: ast.Call,
    parent_index: dict[ast.AST, ast.AST],
    source: str,
) -> tuple[str, str]:
    parent = parent_index.get(call)

    if isinstance(parent, ast.Await):
        parent = parent_index.get(parent)

    if isinstance(parent, ast.Assign):
        targets = ",".join(
            source_text(source, target)
            for target in parent.targets
        )
        return "ASSIGN", targets

    if isinstance(parent, ast.AnnAssign):
        return (
            "ANN_ASSIGN",
            source_text(source, parent.target),
        )

    if isinstance(parent, ast.Return):
        return "RETURN", ""

    if isinstance(parent, ast.Expr):
        return "IGNORED_RESULT", ""

    return (
        type(parent).__name__
        if parent is not None
        else "UNKNOWN",
        "",
    )


def runtime_call_sites(
    source: str,
    tree: ast.Module,
    functions: list[FunctionInfo],
    parent_index: dict[ast.AST, ast.AST],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = call_name(node)

        if not name.endswith(RUNTIME_TARGET):
            continue

        caller = enclosing_function(
            functions,
            node.lineno,
        )

        guard, guard_line = nearest_guard(
            node,
            parent_index,
            source,
        )

        result_usage, result_target = assigned_target(
            node,
            parent_index,
            source,
        )

        rows.append(
            {
                "caller_function": (
                    caller.name
                    if caller is not None
                    else "<module>"
                ),
                "caller_qualified_name": (
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
                "guard_line": guard_line,
                "guard_expression": guard,
                "result_usage": result_usage,
                "result_target": result_target,
                "call_source": source_text(source, node),
            }
        )

    return sorted(
        rows,
        key=lambda row: int(row["call_line"]),
    )


def caller_parent_rows(
    source: str,
    tree: ast.Module,
    functions: list[FunctionInfo],
    parent_index: dict[ast.AST, ast.AST],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = call_name(node)
        terminal = name.rsplit(".", 1)[-1]

        if terminal not in RUNTIME_CALLERS:
            continue

        caller = enclosing_function(
            functions,
            node.lineno,
        )

        guard, guard_line = nearest_guard(
            node,
            parent_index,
            source,
        )

        rows.append(
            {
                "target_function": terminal,
                "caller_function": (
                    caller.name
                    if caller is not None
                    else "<module>"
                ),
                "caller_qualified_name": (
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
                "guard_line": guard_line,
                "guard_expression": guard,
                "call_source": source_text(source, node),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            str(row["target_function"]),
            int(row["call_line"]),
        ),
    )


def assignment_bindings(
    function: FunctionInfo,
    source: str,
) -> dict[str, str]:
    bindings: dict[str, str] = {}

    for node in ast.walk(function.node):
        if isinstance(node, ast.Assign):
            value = source_text(source, node.value)

            for target in node.targets:
                if isinstance(target, ast.Name):
                    bindings[target.id] = value

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                bindings[node.target.id] = source_text(
                    source,
                    node.value,
                )

    return bindings


def condition_uses_name(
    node: ast.If,
    name: str,
) -> bool:
    return any(
        isinstance(child, ast.Name)
        and child.id == name
        for child in ast.walk(node.test)
    )


def risk_result_usage(
    source: str,
    functions: list[FunctionInfo],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []

    for function in functions:
        bindings = assignment_bindings(
            function,
            source,
        )

        for node in ast.walk(function.node):
            if not isinstance(node, ast.Call):
                continue

            if call_name(node) != "gate.check":
                continue

            result_usage = "UNUSED"
            result_target = ""
            decision_condition = ""
            decision_line = 0

            parent_index = ancestors(function.node)
            parent = parent_index.get(node)

            if isinstance(parent, ast.Await):
                parent = parent_index.get(parent)

            if isinstance(parent, ast.Assign):
                result_usage = "ASSIGNED"
                targets = [
                    target
                    for target in parent.targets
                    if isinstance(target, ast.Name)
                ]

                if targets:
                    result_target = targets[0].id

                    for candidate in ast.walk(function.node):
                        if (
                            isinstance(candidate, ast.If)
                            and condition_uses_name(
                                candidate,
                                result_target,
                            )
                        ):
                            decision_condition = source_text(
                                source,
                                candidate.test,
                            )
                            decision_line = candidate.lineno
                            break

            elif isinstance(parent, ast.If):
                result_usage = "DIRECT_CONDITION"
                decision_condition = source_text(
                    source,
                    parent.test,
                )
                decision_line = parent.lineno

            receiver_binding = bindings.get("gate", "")

            rows.append(
                {
                    "function": function.name,
                    "function_line": function.line,
                    "call_line": node.lineno,
                    "call_name": call_name(node),
                    "receiver_binding": receiver_binding,
                    "result_usage": result_usage,
                    "result_target": result_target,
                    "decision_line": decision_line,
                    "decision_condition": decision_condition,
                    "authoritative_binding": int(
                        "PortfolioRiskGate" in receiver_binding
                    ),
                    "decision_result_consumed": int(
                        result_usage
                        in {
                            "ASSIGNED",
                            "DIRECT_CONDITION",
                        }
                        and bool(decision_condition)
                    ),
                }
            )

    return rows


def branch_contract(
    runtime_calls: list[dict[str, object]],
    parent_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    caller_names = {
        str(row["caller_function"])
        for row in runtime_calls
    }

    parent_target_names = {
        str(row["target_function"])
        for row in parent_rows
    }

    result: list[dict[str, object]] = []

    for branch, caller in (
        ("NG_M1", "_process_ng_m1_closed_bar_for_paper_signal"),
        ("BR", "_process_br_closed_bar_for_paper_signal"),
    ):
        runtime_call_present = int(
            caller in caller_names
        )
        upstream_call_present = int(
            caller in parent_target_names
        )

        result.append(
            {
                "branch": branch,
                "runtime_caller": caller,
                "upstream_call_present": (
                    upstream_call_present
                ),
                "runtime_call_present": (
                    runtime_call_present
                ),
                "chain_complete": int(
                    upstream_call_present
                    and runtime_call_present
                ),
                "owner_confirmed": 0,
                "runtime_instrumentation": 0,
            }
        )

    return result


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

    source, tree, functions = load_source()
    parent_index = ancestors(tree)

    runtime_calls = runtime_call_sites(
        source,
        tree,
        functions,
        parent_index,
    )
    parent_rows = caller_parent_rows(
        source,
        tree,
        functions,
        parent_index,
    )
    risk_rows = risk_result_usage(
        source,
        functions,
    )
    branch_rows = branch_contract(
        runtime_calls,
        parent_rows,
    )

    unresolved: list[dict[str, object]] = []

    for expected in RUNTIME_CALLERS:
        if not any(
            row["caller_function"] == expected
            for row in runtime_calls
        ):
            unresolved.append(
                {
                    "scope": "RUNTIME_CALL",
                    "symbol": expected,
                    "reason": (
                        "RUNTIME_TARGET_CALL_NOT_FOUND"
                    ),
                }
            )

        if not any(
            row["target_function"] == expected
            for row in parent_rows
        ):
            unresolved.append(
                {
                    "scope": "UPSTREAM_CALL",
                    "symbol": expected,
                    "reason": (
                        "UPSTREAM_CALLER_NOT_FOUND"
                    ),
                }
            )

    authoritative_risk_rows = [
        row
        for row in risk_rows
        if int(row["authoritative_binding"]) == 1
        and int(row["decision_result_consumed"]) == 1
    ]

    if not authoritative_risk_rows:
        unresolved.append(
            {
                "scope": "RISK",
                "symbol": "PortfolioRiskGate.check",
                "reason": (
                    "AUTHORITATIVE_RESULT_USAGE_NOT_PROVEN"
                ),
            }
        )

    write_tsv(
        RUNTIME_CALLS_FILE,
        (
            "caller_function",
            "caller_qualified_name",
            "caller_line",
            "call_line",
            "call_name",
            "guard_line",
            "guard_expression",
            "result_usage",
            "result_target",
            "call_source",
        ),
        runtime_calls,
    )

    write_tsv(
        CALLER_PARENTS_FILE,
        (
            "target_function",
            "caller_function",
            "caller_qualified_name",
            "caller_line",
            "call_line",
            "call_name",
            "guard_line",
            "guard_expression",
            "call_source",
        ),
        parent_rows,
    )

    write_tsv(
        RISK_USAGE_FILE,
        (
            "function",
            "function_line",
            "call_line",
            "call_name",
            "receiver_binding",
            "result_usage",
            "result_target",
            "decision_line",
            "decision_condition",
            "authoritative_binding",
            "decision_result_consumed",
        ),
        risk_rows,
    )

    write_tsv(
        BRANCH_FILE,
        (
            "branch",
            "runtime_caller",
            "upstream_call_present",
            "runtime_call_present",
            "chain_complete",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        branch_rows,
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
            "DECISION OWNER RUNTIME CALLER CHAIN V2\n"
        )
        stream.write(
            "======================================\n\n"
        )

        stream.write("[RUNTIME_CALL_SITES]\n")

        for row in runtime_calls:
            stream.write(
                f"caller={row['caller_function']} "
                f"call_line={row['call_line']} "
                f"guard={row['guard_expression']} "
                f"result_usage={row['result_usage']}\n"
            )

        stream.write("\n[UPSTREAM_CALLERS]\n")

        for row in parent_rows:
            stream.write(
                f"target={row['target_function']} "
                f"caller={row['caller_function']} "
                f"call_line={row['call_line']} "
                f"guard={row['guard_expression']}\n"
            )

        stream.write("\n[RISK_RESULT_USAGE]\n")

        for row in risk_rows:
            stream.write(
                f"function={row['function']} "
                f"call_line={row['call_line']} "
                f"binding={row['receiver_binding']} "
                f"usage={row['result_usage']} "
                f"condition={row['decision_condition']} "
                f"authoritative="
                f"{row['authoritative_binding']} "
                f"consumed="
                f"{row['decision_result_consumed']}\n"
            )

    complete_branches = sum(
        int(row["chain_complete"])
        for row in branch_rows
    )

    print(
        "=== AUDIT DECISION OWNER "
        "RUNTIME CALLER CHAIN V2 ==="
    )
    print(
        f"runtime_call_site_count="
        f"{len(runtime_calls)}"
    )
    print(
        f"runtime_caller_parent_count="
        f"{len(parent_rows)}"
    )
    print(
        f"risk_result_usage_count="
        f"{len(risk_rows)}"
    )
    print(
        f"authoritative_risk_usage_count="
        f"{len(authoritative_risk_rows)}"
    )
    print(
        f"complete_runtime_branch_count="
        f"{complete_branches}"
    )
    print(f"unresolved_count={len(unresolved)}")

    for row in branch_rows:
        print(
            f"BRANCH name={row['branch']} "
            f"upstream={row['upstream_call_present']} "
            f"runtime={row['runtime_call_present']} "
            f"complete={row['chain_complete']}"
        )

    for row in parent_rows:
        print(
            f"UPSTREAM target={row['target_function']} "
            f"caller={row['caller_function']} "
            f"call_line={row['call_line']}"
        )

    for row in authoritative_risk_rows:
        print(
            "RISK_OWNER_EVIDENCE "
            "symbol=PortfolioRiskGate.check "
            f"function={row['function']} "
            f"call_line={row['call_line']} "
            f"decision_line={row['decision_line']}"
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
        "DECISION_OWNER_RUNTIME_CALLER_CHAIN_V2_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
