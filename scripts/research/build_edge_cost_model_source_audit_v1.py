#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
import re
from collections import Counter
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


ROOT = pathlib.Path("/opt/finam-core")
SOURCE_ARTIFACT = pathlib.Path(
    "/tmp/edge_cost_recalculation_v1/recalculated_edges.tsv"
)

OUT = pathlib.Path("/tmp/edge_cost_model_source_audit_v1")

CODE_MATCHES_FILE = OUT / "source_code_matches.tsv"
RUNNER_VERSIONS_FILE = OUT / "runner_versions.tsv"
SOURCE_VERSION_FILE = OUT / "source_version_matrix.tsv"
MISMATCH_VERSION_FILE = OUT / "mismatch_version_matrix.tsv"
CONTRACT_FILE = OUT / "audit_contract.txt"
UNRESOLVED_FILE = OUT / "unresolved.tsv"

SEARCH_ROOTS = (
    ROOT / "src",
    ROOT / "scripts",
    ROOT / "core",
    ROOT / "execution",
    ROOT / "risk",
    ROOT / "strategy",
)

SEARCH_PATTERNS = {
    "COMMISSION_CALCULATION": re.compile(
        r"\bcommission\b.*(?:=|\*|/|\+|-)|"
        r"(?:=|\*|/|\+|-).*\bcommission\b",
        re.IGNORECASE,
    ),
    "SLIPPAGE_CALCULATION": re.compile(
        r"\bslippage\b.*(?:=|\*|/|\+|-)|"
        r"(?:=|\*|/|\+|-).*\bslippage\b",
        re.IGNORECASE,
    ),
    "EXPECTANCY_CALCULATION": re.compile(
        r"\bexpectancy\b.*(?:=|sum|mean|avg)|"
        r"(?:sum|mean|avg).*\bexpectancy\b",
        re.IGNORECASE,
    ),
    "PROFIT_FACTOR_CALCULATION": re.compile(
        r"profit_factor|profitfactor|gross_profit.*gross_loss",
        re.IGNORECASE,
    ),
    "DRAWDOWN_CALCULATION": re.compile(
        r"max_drawdown|maximum_drawdown|running.*peak|high_water",
        re.IGNORECASE,
    ),
    "EDGE_OBSERVATION_WRITE": re.compile(
        r"edge_observation_v1",
        re.IGNORECASE,
    ),
    "RESEARCH_TRADE_WRITE": re.compile(
        r"research_trade_v1",
        re.IGNORECASE,
    ),
}

TEXT_SUFFIXES = {
    ".py",
    ".sql",
    ".sh",
}


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
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


def scan_source_code() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for search_root in SEARCH_ROOTS:
        if not search_root.is_dir():
            continue

        for path in search_root.rglob("*"):
            if not path.is_file():
                continue

            if path.suffix not in TEXT_SUFFIXES:
                continue

            try:
                source = path.read_text(
                    encoding="utf-8",
                    errors="replace",
                )
            except OSError:
                continue

            relative_path = str(path.relative_to(ROOT))

            for line_no, line in enumerate(
                source.splitlines(),
                start=1,
            ):
                stripped = line.strip()

                if not stripped:
                    continue

                for match_type, pattern in SEARCH_PATTERNS.items():
                    if not pattern.search(stripped):
                        continue

                    rows.append(
                        {
                            "file_path": relative_path,
                            "line_no": line_no,
                            "match_type": match_type,
                            "line_text": stripped[:500],
                        }
                    )

    return rows


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    unresolved: list[dict[str, str]] = []
    code_matches = scan_source_code()

    if not SOURCE_ARTIFACT.is_file():
        unresolved.append(
            {
                "scope": "ARTIFACT",
                "identity": str(SOURCE_ARTIFACT),
                "reason": "EDGE_COST_RECALCULATION_ARTIFACT_MISSING",
            }
        )
        recalculated_rows: list[dict[str, str]] = []
    else:
        with SOURCE_ARTIFACT.open(
            "r",
            encoding="utf-8",
            newline="",
        ) as stream:
            recalculated_rows = list(
                csv.DictReader(stream, delimiter="\t")
            )

    with psycopg2.connect(build_psycopg_url()) as connection:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    runner_version,
                    source_version,
                    strategy_code,
                    symbol,
                    timeframe,
                    count(*)::bigint AS observation_count,
                    count(*) FILTER (
                        WHERE commission = 0
                    )::bigint AS zero_commission_count,
                    count(*) FILTER (
                        WHERE slippage = 0
                    )::bigint AS zero_slippage_count,
                    min(created_at) AS first_created_at,
                    max(created_at) AS last_created_at
                FROM analytics.edge_observation_v1
                GROUP BY
                    runner_version,
                    source_version,
                    strategy_code,
                    symbol,
                    timeframe
                ORDER BY observation_count DESC
                """
            )
            runner_rows = [
                dict(row)
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT
                    source_version,
                    strategy_code,
                    symbol,
                    timeframe,
                    count(*)::bigint AS trade_count,
                    count(*) FILTER (
                        WHERE commission = 0
                    )::bigint AS zero_commission_trade_count,
                    count(*) FILTER (
                        WHERE slippage = 0
                    )::bigint AS zero_slippage_trade_count,
                    sum(commission)::numeric AS commission_sum,
                    sum(slippage)::numeric AS slippage_sum,
                    min(created_at) AS first_created_at,
                    max(created_at) AS last_created_at
                FROM analytics.research_trade_v1
                GROUP BY
                    source_version,
                    strategy_code,
                    symbol,
                    timeframe
                ORDER BY trade_count DESC
                """
            )
            source_version_rows = [
                dict(row)
                for row in cursor.fetchall()
            ]

    mismatch_counter: Counter[
        tuple[str, str, str, str, str]
    ] = Counter()

    for row in recalculated_rows:
        if row.get("classification") != "COST_RECALCULATION_MISMATCH":
            continue

        key = (
            row.get("strategy_code", ""),
            row.get("strategy_version", ""),
            row.get("symbol", ""),
            row.get("timeframe", ""),
            row.get("source_version", ""),
        )
        mismatch_counter[key] += 1

    mismatch_rows = [
        {
            "strategy_code": key[0],
            "strategy_version": key[1],
            "symbol": key[2],
            "timeframe": key[3],
            "source_version": key[4],
            "mismatch_count": count,
        }
        for key, count in sorted(
            mismatch_counter.items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]

    write_tsv(
        CODE_MATCHES_FILE,
        (
            "file_path",
            "line_no",
            "match_type",
            "line_text",
        ),
        code_matches,
    )

    write_tsv(
        RUNNER_VERSIONS_FILE,
        (
            "runner_version",
            "source_version",
            "strategy_code",
            "symbol",
            "timeframe",
            "observation_count",
            "zero_commission_count",
            "zero_slippage_count",
            "first_created_at",
            "last_created_at",
        ),
        runner_rows,
    )

    write_tsv(
        SOURCE_VERSION_FILE,
        (
            "source_version",
            "strategy_code",
            "symbol",
            "timeframe",
            "trade_count",
            "zero_commission_trade_count",
            "zero_slippage_trade_count",
            "commission_sum",
            "slippage_sum",
            "first_created_at",
            "last_created_at",
        ),
        source_version_rows,
    )

    write_tsv(
        MISMATCH_VERSION_FILE,
        (
            "strategy_code",
            "strategy_version",
            "symbol",
            "timeframe",
            "source_version",
            "mismatch_count",
        ),
        mismatch_rows,
    )

    write_tsv(
        UNRESOLVED_FILE,
        (
            "scope",
            "identity",
            "reason",
        ),
        unresolved,
    )

    observation_writer_match_count = sum(
        row["match_type"] == "EDGE_OBSERVATION_WRITE"
        for row in code_matches
    )
    trade_writer_match_count = sum(
        row["match_type"] == "RESEARCH_TRADE_WRITE"
        for row in code_matches
    )
    cost_calculation_match_count = sum(
        row["match_type"] in {
            "COMMISSION_CALCULATION",
            "SLIPPAGE_CALCULATION",
        }
        for row in code_matches
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("EDGE COST MODEL SOURCE AUDIT V1\n")
        stream.write("===============================\n\n")
        stream.write("MODE=READ_ONLY\n")
        stream.write("DATABASE=POSTGRESQL_ONLY\n")
        stream.write(
            f"SOURCE_CODE_MATCH_COUNT={len(code_matches)}\n"
        )
        stream.write(
            "EDGE_OBSERVATION_WRITER_MATCH_COUNT="
            f"{observation_writer_match_count}\n"
        )
        stream.write(
            "RESEARCH_TRADE_WRITER_MATCH_COUNT="
            f"{trade_writer_match_count}\n"
        )
        stream.write(
            "COST_CALCULATION_MATCH_COUNT="
            f"{cost_calculation_match_count}\n"
        )
        stream.write(
            f"RUNNER_VERSION_GROUP_COUNT={len(runner_rows)}\n"
        )
        stream.write(
            "TRADE_SOURCE_VERSION_GROUP_COUNT="
            f"{len(source_version_rows)}\n"
        )
        stream.write(
            f"MISMATCH_VERSION_GROUP_COUNT={len(mismatch_rows)}\n"
        )
        stream.write(
            f"UNRESOLVED_COUNT={len(unresolved)}\n"
        )
        stream.write("DB_WRITES_PERFORMED=0\n")
        stream.write("RUNTIME_CHANGED=0\n")
        stream.write("EXECUTION_CHANGED=0\n")
        stream.write("ORDERS_CHANGED=0\n")
        stream.write("FILLS_CHANGED=0\n")
        stream.write("MICRO_LIVE_ALLOWED=0\n")

    print("=== EDGE COST MODEL SOURCE AUDIT V1 ===")
    print(f"source_code_match_count={len(code_matches)}")
    print(
        "edge_observation_writer_match_count="
        f"{observation_writer_match_count}"
    )
    print(
        "research_trade_writer_match_count="
        f"{trade_writer_match_count}"
    )
    print(
        "cost_calculation_match_count="
        f"{cost_calculation_match_count}"
    )
    print(f"runner_version_group_count={len(runner_rows)}")
    print(
        "trade_source_version_group_count="
        f"{len(source_version_rows)}"
    )
    print(
        "mismatch_version_group_count="
        f"{len(mismatch_rows)}"
    )
    print(f"unresolved_count={len(unresolved)}")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=EDGE_COST_MODEL_SOURCE_AUDIT_V1_READY")

    return 0 if not unresolved else 1


if __name__ == "__main__":
    raise SystemExit(main())
