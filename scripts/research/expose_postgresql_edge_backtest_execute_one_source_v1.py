#!/usr/bin/env python3
from __future__ import annotations

import ast
import inspect
import pathlib
import textwrap

import finam_core.research.postgresql_edge_backtest_adapter_v1 as adapter


def dotted_name(node: ast.AST | None) -> str:
    if node is None:
        return ""

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr

    return ""


def main() -> int:
    adapter_path_text = inspect.getsourcefile(adapter)

    if adapter_path_text is None:
        raise SystemExit("ERROR=adapter_file_missing")

    adapter_path = pathlib.Path(adapter_path_text)
    module_source = adapter_path.read_text(
        encoding="utf-8",
        errors="replace",
    )
    module_tree = ast.parse(
        module_source,
        filename=str(adapter_path),
    )

    execute_source = textwrap.dedent(
        inspect.getsource(adapter.execute_one)
    )
    execute_start_line = inspect.getsourcelines(
        adapter.execute_one
    )[1]
    execute_tree = ast.parse(execute_source)

    calls: list[tuple[int, str]] = []
    returns: list[tuple[int, str]] = []
    raises: list[tuple[int, str]] = []
    handlers: list[tuple[int, str]] = []

    for node in ast.walk(execute_tree):
        absolute_line = (
            execute_start_line
            + getattr(node, "lineno", 1)
            - 1
        )

        if isinstance(node, ast.Call):
            calls.append(
                (
                    absolute_line,
                    dotted_name(node.func),
                )
            )

        elif isinstance(node, ast.Return):
            value = (
                ast.unparse(node.value)
                if node.value is not None
                else "None"
            )
            returns.append((absolute_line, value))

        elif isinstance(node, ast.Raise):
            value = (
                ast.unparse(node.exc)
                if node.exc is not None
                else "re-raise"
            )
            raises.append((absolute_line, value))

        elif isinstance(node, ast.ExceptHandler):
            handler_type = (
                dotted_name(node.type)
                if node.type is not None
                else "bare_except"
            )
            handlers.append(
                (
                    absolute_line,
                    handler_type,
                )
            )

    function_names = {
        target.split(".")[-1]
        for _, target in calls
        if target
    }

    helper_sources: list[tuple[str, int, str]] = []

    for node in module_tree.body:
        if not isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):
            continue

        if node.name not in function_names:
            continue

        start = node.lineno
        end = getattr(node, "end_lineno", node.lineno)

        helper_text = "\n".join(
            module_source.splitlines()[start - 1:end]
        )

        helper_sources.append(
            (
                node.name,
                start,
                helper_text,
            )
        )

    print("=== POSTGRESQL EDGE BACKTEST EXECUTE_ONE SOURCE V1 ===")
    print(f"adapter_file={adapter_path}")
    print(f"execute_one_start_line={execute_start_line}")
    print(f"execute_one_call_count={len(calls)}")
    print(f"execute_one_return_count={len(returns)}")
    print(f"execute_one_raise_count={len(raises)}")
    print(f"execute_one_handler_count={len(handlers)}")
    print(f"referenced_helper_count={len(helper_sources)}")

    for line, target in sorted(calls):
        print(
            "EXECUTE_ONE_CALL "
            f"line={line} "
            f"target={target}"
        )

    for line, value in sorted(returns):
        print(
            "EXECUTE_ONE_RETURN "
            f"line={line} "
            f"value={value!r}"
        )

    for line, value in sorted(raises):
        print(
            "EXECUTE_ONE_RAISE "
            f"line={line} "
            f"value={value!r}"
        )

    for line, handler_type in sorted(handlers):
        print(
            "EXECUTE_ONE_HANDLER "
            f"line={line} "
            f"type={handler_type}"
        )

    print("=== EXECUTE_ONE_SOURCE_BEGIN ===")

    for offset, line in enumerate(
        execute_source.splitlines(),
        start=execute_start_line,
    ):
        print(f"{offset:05d}: {line}")

    print("=== EXECUTE_ONE_SOURCE_END ===")

    for name, start, source in helper_sources:
        print(
            "=== HELPER_SOURCE_BEGIN "
            f"name={name} line={start} ==="
        )

        for offset, line in enumerate(
            source.splitlines(),
            start=start,
        ):
            print(f"{offset:05d}: {line}")

        print(
            "=== HELPER_SOURCE_END "
            f"name={name} ==="
        )

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_BACKTEST_EXECUTE_ONE_SOURCE_V1_EXPOSED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
