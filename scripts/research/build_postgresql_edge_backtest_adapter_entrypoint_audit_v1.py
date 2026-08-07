#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import pathlib
from dataclasses import dataclass
from typing import Iterable


ROOT = pathlib.Path("/opt/finam-core")

SEARCH_ROOTS = (
    ROOT / "scripts/research",
    ROOT / "src",
)

REQUIRED_MARKERS = (
    "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1",
    "edge_lab_run_v1",
)

EXECUTION_MARKERS = (
    "claim",
    "queued",
    "run_uuid",
    "status_code",
    "FAILED",
    "DONE",
    "research_trade_v1",
    "edge_observation_v1",
)

STRATEGY_MARKERS = (
    "RSI_MEAN_REVERSION_V1",
    "ATR_IMPULSE_V1",
    "MOMENTUM_CONTINUATION_V1",
    "MEAN_REVERSION_ZSCORE_V1",
)

EXCLUDED_NAME_PARTS = (
    "audit_",
    "test_",
    "discover_",
    "expose_",
    "diagnostic",
    "forensic",
)


@dataclass(frozen=True, slots=True)
class Candidate:
    path: pathlib.Path
    score: int
    markers: tuple[str, ...]


def relative(path: pathlib.Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def iter_python_files() -> Iterable[pathlib.Path]:
    seen: set[pathlib.Path] = set()

    for search_root in SEARCH_ROOTS:
        if not search_root.is_dir():
            continue

        for path in search_root.rglob("*.py"):
            resolved = path.resolve()

            if resolved in seen:
                continue

            seen.add(resolved)
            yield path


def source_objects(path: pathlib.Path) -> list[tuple[str, str, int]]:
    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return []

    result: list[tuple[str, str, int]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            result.append(
                ("FUNCTION", node.name, node.lineno)
            )
        elif isinstance(node, ast.AsyncFunctionDef):
            result.append(
                ("ASYNC_FUNCTION", node.name, node.lineno)
            )
        elif isinstance(node, ast.ClassDef):
            result.append(
                ("CLASS", node.name, node.lineno)
            )

    return sorted(result, key=lambda item: item[2])


def exception_handlers(path: pathlib.Path) -> list[tuple[int, str]]:
    try:
        source = path.read_text(
            encoding="utf-8",
            errors="replace",
        )
        tree = ast.parse(source, filename=str(path))
    except (OSError, SyntaxError):
        return []

    lines = source.splitlines()
    result: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue

        if node.type is None:
            exception_name = "bare_except"
        elif isinstance(node.type, ast.Name):
            exception_name = node.type.id
        elif isinstance(node.type, ast.Attribute):
            exception_name = node.type.attr
        else:
            exception_name = ast.dump(node.type)

        line_text = (
            lines[node.lineno - 1].strip()
            if 0 < node.lineno <= len(lines)
            else ""
        )

        result.append(
            (
                node.lineno,
                f"{exception_name}:{line_text}",
            )
        )

    return sorted(result)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Edge Backtest Adapter Entrypoint Audit V1"
        )
    )
    parser.add_argument(
        "--failed-batch-id",
        required=True,
    )
    args = parser.parse_args()

    candidates: list[Candidate] = []

    for path in iter_python_files():
        name = path.name.lower()

        if any(part in name for part in EXCLUDED_NAME_PARTS):
            continue

        try:
            source = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            continue

        found_required = tuple(
            marker
            for marker in REQUIRED_MARKERS
            if marker in source
        )

        if len(found_required) != len(REQUIRED_MARKERS):
            continue

        found_execution = tuple(
            marker
            for marker in EXECUTION_MARKERS
            if marker in source
        )

        found_strategy = tuple(
            marker
            for marker in STRATEGY_MARKERS
            if marker in source
        )

        score = (
            len(found_required) * 100
            + len(found_execution) * 10
            + len(found_strategy) * 5
        )

        candidates.append(
            Candidate(
                path=path,
                score=score,
                markers=(
                    found_required
                    + found_execution
                    + found_strategy
                ),
            )
        )

    candidates.sort(
        key=lambda item: (
            -item.score,
            relative(item.path),
        )
    )

    print(
        "=== POSTGRESQL EDGE BACKTEST ADAPTER "
        "ENTRYPOINT AUDIT V1 ==="
    )
    print(f"failed_batch_id={args.failed_batch_id}")
    print(f"candidate_count={len(candidates)}")

    for rank, candidate in enumerate(
        candidates,
        start=1,
    ):
        path = candidate.path

        print(
            "ADAPTER_CANDIDATE "
            f"rank={rank} "
            f"path={relative(path)} "
            f"score={candidate.score} "
            f"markers={','.join(candidate.markers)}"
        )

        for object_type, name, line in source_objects(path):
            print(
                "SOURCE_OBJECT "
                f"rank={rank} "
                f"path={relative(path)} "
                f"type={object_type} "
                f"name={name} "
                f"line={line}"
            )

        for line, handler in exception_handlers(path):
            print(
                "EXCEPTION_HANDLER "
                f"rank={rank} "
                f"path={relative(path)} "
                f"line={line} "
                f"handler={handler!r}"
            )

    print("db_writes_performed=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")

    if not candidates:
        print(
            "root_cause="
            "ADAPTER_ENTRYPOINT_NOT_DISCOVERED"
        )
        print(
            "VERDICT="
            "POSTGRESQL_EDGE_BACKTEST_ADAPTER_ENTRYPOINT_AUDIT_V1_BLOCKED"
        )
        return 2

    print(
        "recommended_adapter_file="
        f"{relative(candidates[0].path)}"
    )
    print(
        "root_cause="
        "ADAPTER_ENTRYPOINT_DISCOVERED"
    )
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_BACKTEST_ADAPTER_ENTRYPOINT_AUDIT_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
