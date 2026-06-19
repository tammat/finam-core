#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path


# Русский комментарий:
# EQUITY_STRATEGY_METHOD_SIGNATURE_AUDIT_V1
# Read-only audit.
# Цель — определить публичные методы equity strategies и безопасную точку вызова
# из paper_pipeline MTF closed-bar path.


ROOT = Path(".").resolve()

FILES = [
    Path("src/finam_core/strategy/equities/volatility_breakout_equity.py"),
    Path("src/finam_core/strategy/equities/mean_reversion_equity.py"),
    Path("src/finam_core/strategy/equities/trend_pullback_equity.py"),
    Path("src/finam_core/strategy/strategy_factory.py"),
    Path("src/finam_core/strategy/quote_signal_processor.py"),
    Path("src/finam_core/strategy/signal_router.py"),
    Path("src/finam_core/pipelines/paper_pipeline.py"),
]


def source(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def line_context(lines: list[str], line_no: int, radius: int = 5) -> None:
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    for idx in range(start, end + 1):
        print(f"EQUITY_METHOD_CONTEXT line={idx} code={lines[idx - 1].strip()}")


def method_args(fn: ast.FunctionDef) -> str:
    args = []
    for a in fn.args.args:
        args.append(a.arg)
    if fn.args.vararg:
        args.append("*" + fn.args.vararg.arg)
    for a in fn.args.kwonlyargs:
        args.append(a.arg + "=")
    if fn.args.kwarg:
        args.append("**" + fn.args.kwarg.arg)
    return ",".join(args)


def main() -> int:
    print("=== EQUITY STRATEGY METHOD SIGNATURE AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"root={ROOT}")
    print()

    method_rows = 0
    target_method_rows = 0
    pipeline_dispatch_hits = 0

    for rel in FILES:
        path = ROOT / rel
        text = source(path)
        if not text:
            print(f"EQUITY_METHOD_FILE_MISSING file={rel}")
            continue

        lines = text.splitlines()

        try:
            tree = ast.parse(text)
        except SyntaxError as exc:
            print(f"EQUITY_METHOD_PARSE_FAILED file={rel} error={exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_name = node.name
                for body_node in node.body:
                    if isinstance(body_node, ast.FunctionDef):
                        name = body_node.name
                        if name.startswith("_"):
                            continue

                        method_rows += 1
                        is_target = name in {
                            "on_quote",
                            "on_bar",
                            "on_bars",
                            "generate",
                            "route",
                            "process",
                            "create",
                        }
                        if is_target:
                            target_method_rows += 1

                        print(
                            "EQUITY_METHOD_ROW "
                            f"file={rel} "
                            f"class={class_name} "
                            f"method={name} "
                            f"line={body_node.lineno} "
                            f"args={method_args(body_node)} "
                            f"is_target={int(is_target)}"
                        )

                        if is_target:
                            line_context(lines, body_node.lineno, radius=6)

        # Русский комментарий: отдельно ищем MTF close dispatch.
        for idx, line in enumerate(lines, start=1):
            if (
                "_process_br_closed_bar_for_paper_signal" in line
                or "_process_ng_m1_closed_bar_for_paper_signal" in line
                or "PIPE_MTF_BAR_CLOSED" in line
                or "strategy_by_symbol" in line
                or "QuoteSignalRouter" in line
                or "quote_signal_processor" in line
            ):
                pipeline_dispatch_hits += 1
                print(
                    "EQUITY_PIPELINE_DISPATCH_HIT "
                    f"file={rel} line={idx} code={line.strip()}"
                )
                if rel.name == "paper_pipeline.py":
                    line_context(lines, idx, radius=5)

    print()
    print("EQUITY_STRATEGY_METHOD_SIGNATURE_AUDIT_SUMMARY")
    print(f"method_rows={method_rows}")
    print(f"target_method_rows={target_method_rows}")
    print(f"pipeline_dispatch_hits={pipeline_dispatch_hits}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if target_method_rows > 0 and pipeline_dispatch_hits > 0:
        print("VERDICT=EQUITY_METHOD_SIGNATURE_AND_DISPATCH_POINTS_FOUND")
    elif target_method_rows > 0:
        print("VERDICT=EQUITY_METHOD_SIGNATURE_FOUND_DISPATCH_REVIEW_REQUIRED")
    else:
        print("VERDICT=EQUITY_METHOD_SIGNATURE_NOT_FOUND")

    print("EQUITY_STRATEGY_METHOD_SIGNATURE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
