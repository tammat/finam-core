#!/usr/bin/env python3
from __future__ import annotations

import ast
import pathlib
from dataclasses import dataclass


ROOT = pathlib.Path("/opt/finam-core")
RUNNER = ROOT / "scripts/research/run_postgresql_edge_parameter_search_v1.py"


@dataclass(frozen=True, slots=True)
class CallInfo:
    line: int
    function: str
    target: str


def dotted_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr

    return ""


def main() -> int:
    if not RUNNER.is_file():
        print(f"runner_file_missing={RUNNER}")
        print(
            "VERDICT="
            "POSTGRESQL_EDGE_BACKTEST_EXECUTION_PATH_V1_RUNNER_MISSING"
        )
        return 2

    source = RUNNER.read_text(
        encoding="utf-8",
        errors="replace",
    )
    tree = ast.parse(source, filename=str(RUNNER))
    lines = source.splitlines()

    imports: list[str] = []
    calls: list[CallInfo] = []
    subprocess_calls: list[tuple[int, str]] = []
    exception_handlers: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ",".join(alias.name for alias in node.names)
            imports.append(f"{module}:{names}")

        elif isinstance(node, ast.Call):
            target = dotted_name(node.func)

            enclosing = "MODULE"

            for candidate in ast.walk(tree):
                if not isinstance(
                    candidate,
                    (
                        ast.FunctionDef,
                        ast.AsyncFunctionDef,
                    ),
                ):
                    continue

                end = getattr(candidate, "end_lineno", candidate.lineno)

                if candidate.lineno <= node.lineno <= end:
                    enclosing = candidate.name
                    break

            calls.append(
                CallInfo(
                    line=node.lineno,
                    function=enclosing,
                    target=target,
                )
            )

            if target in {
                "subprocess.run",
                "subprocess.Popen",
                "subprocess.check_call",
                "subprocess.check_output",
            }:
                text = (
                    lines[node.lineno - 1].strip()
                    if 0 < node.lineno <= len(lines)
                    else ""
                )
                subprocess_calls.append(
                    (node.lineno, text)
                )

        elif isinstance(node, ast.ExceptHandler):
            if node.type is None:
                name = "bare_except"
            else:
                name = dotted_name(node.type) or ast.dump(node.type)

            exception_handlers.append(
                (node.lineno, name)
            )

    interesting_markers = (
        "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1",
        "FAILED",
        "status_code",
        "run_uuid",
        "edge_observation_v1",
        "research_trade_v1",
        "subprocess",
        "importlib",
        "build_postgresql_edge_backtest",
    )

    print("=== POSTGRESQL EDGE BACKTEST EXECUTION PATH V1 ===")
    print(f"runner_file={RUNNER.relative_to(ROOT)}")
    print(f"import_count={len(imports)}")
    print(f"call_count={len(calls)}")
    print(f"subprocess_call_count={len(subprocess_calls)}")
    print(f"exception_handler_count={len(exception_handlers)}")

    for item in sorted(set(imports)):
        print(f"IMPORT item={item}")

    for call in calls:
        if any(
            marker.lower() in call.target.lower()
            for marker in (
                "subprocess",
                "adapter",
                "backtest",
                "execute",
                "run",
                "main",
                "import_module",
                "spec_from_file_location",
            )
        ):
            print(
                "CALL "
                f"line={call.line} "
                f"function={call.function} "
                f"target={call.target}"
            )

    for line, text in subprocess_calls:
        print(
            "SUBPROCESS_CALL "
            f"line={line} "
            f"text={text!r}"
        )

    for line, name in exception_handlers:
        print(
            "EXCEPTION_HANDLER "
            f"line={line} "
            f"type={name}"
        )

    for number, line in enumerate(lines, start=1):
        if any(marker in line for marker in interesting_markers):
            print(
                "SOURCE_LINE "
                f"line={number} "
                f"text={line.strip()!r}"
            )

    candidate_files: list[pathlib.Path] = []

    for path in (ROOT / "scripts/research").glob("*.py"):
        if path == RUNNER:
            continue

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        if (
            "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1" in text
            and (
                "research_trade_v1" in text
                or "edge_observation_v1" in text
            )
            and "def main" in text
        ):
            candidate_files.append(path)

    print(f"adapter_candidate_count={len(candidate_files)}")

    for path in sorted(candidate_files):
        print(
            "ADAPTER_EXECUTION_CANDIDATE "
            f"path={path.relative_to(ROOT)}"
        )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if not candidate_files and not subprocess_calls:
        print(
            "root_cause="
            "EXECUTION_TARGET_NOT_DISCOVERED"
        )
        print(
            "VERDICT="
            "POSTGRESQL_EDGE_BACKTEST_EXECUTION_PATH_V1_BLOCKED"
        )
        return 2

    print(
        "root_cause="
        "EXECUTION_TARGET_DISCOVERED"
    )
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_BACKTEST_EXECUTION_PATH_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
