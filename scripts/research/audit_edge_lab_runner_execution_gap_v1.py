#!/usr/bin/env python3
from __future__ import annotations

import ast
import csv
from pathlib import Path
from typing import Any


ROOT = Path("/opt/finam-core")
EDGE_RUNNER = ROOT / "src/scripts/build_edge_lab_runner_v1.py"
BACKTEST_RUNNER = ROOT / "src/scripts/backtest_runner.py"

OUT = Path("/tmp/edge_lab_runner_execution_gap_v1")
FINDINGS_FILE = OUT / "findings.tsv"
CONTRACT_FILE = OUT / "contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"


def write_tsv(
    path: Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse(path: Path) -> tuple[str, ast.Module]:
    source = path.read_text(encoding="utf-8")
    return source, ast.parse(source)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    findings: list[dict[str, Any]] = []
    unresolved: list[dict[str, str]] = []

    for path in (EDGE_RUNNER, BACKTEST_RUNNER):
        if not path.is_file():
            unresolved.append(
                {
                    "scope": "SOURCE_FILE",
                    "identity": str(path.relative_to(ROOT)),
                    "reason": "FILE_MISSING",
                }
            )

    if unresolved:
        write_tsv(
            UNRESOLVED_FILE,
            ("scope", "identity", "reason"),
            unresolved,
        )
        return 1

    edge_source, edge_tree = parse(EDGE_RUNNER)
    backtest_source, backtest_tree = parse(BACKTEST_RUNNER)

    edge_calls = [
        ast.get_source_segment(edge_source, node) or ""
        for node in ast.walk(edge_tree)
        if isinstance(node, ast.Call)
    ]

    backtest_calls = [
        ast.get_source_segment(backtest_source, node) or ""
        for node in ast.walk(backtest_tree)
        if isinstance(node, ast.Call)
    ]

    edge_invokes_backtest = any(
        "run_backtest(" in call
        or "backtest_runner.py" in call
        or "subprocess.run(" in call
        or "subprocess.Popen(" in call
        for call in edge_calls
    )

    edge_writes_no_trades = (
        "INSERT INTO analytics.edge_observation_v1"
        in edge_source
        and "'NO_TRADES'" in edge_source
    )

    edge_marks_done = (
        "status_code='DONE'" in edge_source
    )

    sqlite_imported = any(
        isinstance(node, (ast.Import, ast.ImportFrom))
        and (
            any(alias.name == "sqlite3" for alias in node.names)
            if isinstance(node, ast.Import)
            else node.module == "sqlite3"
        )
        for node in ast.walk(backtest_tree)
    )

    sqlite_connect_count = sum(
        "sqlite3.connect(" in call
        for call in backtest_calls
    )

    sqlite_cli_reference_count = (
        backtest_source.count("sqlite3 data/bars.sqlite")
    )

    postgres_reference_count = sum(
        marker in backtest_source
        for marker in (
            "psycopg",
            "psycopg2",
            "build_psycopg_url",
            "DATABASE_URL",
        )
    )

    checks = (
        (
            "EDGE_RUNNER_INVOKES_BACKTEST",
            int(edge_invokes_backtest),
            "EXPECTED_1",
        ),
        (
            "EDGE_RUNNER_WRITES_NO_TRADES",
            int(edge_writes_no_trades),
            "EXPECTED_0",
        ),
        (
            "EDGE_RUNNER_MARKS_DONE",
            int(edge_marks_done),
            "EXPECTED_REVIEW",
        ),
        (
            "BACKTEST_RUNNER_SQLITE_IMPORTED",
            int(sqlite_imported),
            "EXPECTED_0",
        ),
        (
            "BACKTEST_RUNNER_SQLITE_CONNECT_COUNT",
            sqlite_connect_count,
            "EXPECTED_0",
        ),
        (
            "BACKTEST_RUNNER_SQLITE_CLI_REFERENCE_COUNT",
            sqlite_cli_reference_count,
            "EXPECTED_0",
        ),
        (
            "BACKTEST_RUNNER_POSTGRES_REFERENCE_COUNT",
            postgres_reference_count,
            "EXPECTED_GT_0",
        ),
    )

    for check_name, actual, expected in checks:
        findings.append(
            {
                "check_name": check_name,
                "actual": actual,
                "expected": expected,
                "status": (
                    "PASS"
                    if (
                        (expected == "EXPECTED_1" and actual == 1)
                        or (expected == "EXPECTED_0" and actual == 0)
                        or (
                            expected == "EXPECTED_GT_0"
                            and actual > 0
                        )
                    )
                    else "GAP_CONFIRMED"
                    if expected != "EXPECTED_REVIEW"
                    else "REVIEW"
                ),
            }
        )

    execution_gap_confirmed = (
        not edge_invokes_backtest
        and edge_writes_no_trades
        and edge_marks_done
    )

    sqlite_boundary_violation = (
        sqlite_imported
        or sqlite_connect_count > 0
        or sqlite_cli_reference_count > 0
    )

    if not execution_gap_confirmed:
        unresolved.append(
            {
                "scope": "EDGE_LAB",
                "identity": "execution_gap",
                "reason": "EXPECTED_EXECUTION_GAP_NOT_PROVEN",
            }
        )

    write_tsv(
        FINDINGS_FILE,
        (
            "check_name",
            "actual",
            "expected",
            "status",
        ),
        findings,
    )

    write_tsv(
        UNRESOLVED_FILE,
        ("scope", "identity", "reason"),
        unresolved,
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("EDGE LAB RUNNER EXECUTION GAP V1\n")
        stream.write("================================\n\n")
        stream.write("MODE=STATIC_READ_ONLY\n")
        stream.write(
            f"EXECUTION_GAP_CONFIRMED="
            f"{int(execution_gap_confirmed)}\n"
        )
        stream.write(
            f"EDGE_RUNNER_INVOKES_BACKTEST="
            f"{int(edge_invokes_backtest)}\n"
        )
        stream.write(
            f"EDGE_RUNNER_WRITES_NO_TRADES="
            f"{int(edge_writes_no_trades)}\n"
        )
        stream.write(
            f"EDGE_RUNNER_MARKS_DONE="
            f"{int(edge_marks_done)}\n"
        )
        stream.write(
            f"SQLITE_BOUNDARY_VIOLATION="
            f"{int(sqlite_boundary_violation)}\n"
        )
        stream.write(
            f"SQLITE_CONNECT_COUNT={sqlite_connect_count}\n"
        )
        stream.write(
            "SQLITE_CLI_REFERENCE_COUNT="
            f"{sqlite_cli_reference_count}\n"
        )
        stream.write(
            f"POSTGRES_REFERENCE_COUNT="
            f"{postgres_reference_count}\n"
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

    print("=== EDGE LAB RUNNER EXECUTION GAP V1 ===")
    print(
        f"execution_gap_confirmed="
        f"{int(execution_gap_confirmed)}"
    )
    print(
        f"edge_runner_invokes_backtest="
        f"{int(edge_invokes_backtest)}"
    )
    print(
        f"edge_runner_writes_no_trades="
        f"{int(edge_writes_no_trades)}"
    )
    print(
        f"edge_runner_marks_done="
        f"{int(edge_marks_done)}"
    )
    print(
        f"sqlite_boundary_violation="
        f"{int(sqlite_boundary_violation)}"
    )
    print(f"sqlite_connect_count={sqlite_connect_count}")
    print(
        f"sqlite_cli_reference_count="
        f"{sqlite_cli_reference_count}"
    )
    print(f"postgres_reference_count={postgres_reference_count}")
    print(f"unresolved_count={len(unresolved)}")
    print("source_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_LAB_RUNNER_EXECUTION_GAP_V1_READY")

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
