#!/usr/bin/env python3
"""
ETHUSD_BACKFILL_PATH_AUDIT_V1

Read-only forensic audit crypto backfill path.

Цель:
- раскрыть фактический ExecStart crypto service;
- определить shell/python chain;
- найти BTCUSD/ETHUSD target contract;
- проверить, присутствует ли ETHUSD в реальном ingestion path;
- вывести relevant journal evidence;
- сравнить фактическую M5 freshness BTCUSD/ETHUSD.

Не выполняет backfill.
Не меняет systemd.
Не пишет в PostgreSQL.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


UNIT = "finam-crypto-backfill.service"
TIMEFRAME = "M5"
SYMBOLS = ("BTCUSD", "ETHUSD")
PROJECT_ROOT = Path("/opt/finam-core")


def run(args: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )

    text = (
        result.stdout.strip()
        or result.stderr.strip()
        or ""
    )

    return result.returncode, text


def systemd_property(prop: str) -> str:
    _, text = run([
        "systemctl",
        "show",
        UNIT,
        f"--property={prop}",
        "--value",
    ])
    return text or "NONE"


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_existing_paths(text: str) -> list[Path]:
    """
    Извлекает абсолютные project paths из systemd ExecStart.

    systemctl show возвращает ExecStart в структурированном
    формате { path=... ; argv[]=... }, поэтому shlex здесь
    ненадёжен.
    """
    results: list[Path] = []

    candidates = re.findall(
        r"/opt/finam-core/[A-Za-z0-9_./@+-]+",
        text,
    )

    for raw in candidates:
        raw = raw.rstrip(";,]}")

        candidate = Path(raw)

        try:
            resolved = candidate.resolve()
        except OSError:
            continue

        if (
            resolved.exists()
            and resolved.is_file()
            and PROJECT_ROOT in resolved.parents
        ):
            results.append(resolved)

    return sorted(set(results))


def child_project_paths(path: Path, text: str) -> list[Path]:
    """
    Ищет вызовы следующих shell/python компонентов внутри
    найденного orchestration script.
    """
    results: list[Path] = []

    patterns = (
        r"/opt/finam-core/[A-Za-z0-9_./@+-]+",
        r"(?:src|scripts)/[A-Za-z0-9_./@+-]+\.(?:py|sh)",
    )

    for pattern in patterns:
        for raw in re.findall(pattern, text):
            raw = raw.rstrip(";,)]}\"'")

            candidate = Path(raw)

            if not candidate.is_absolute():
                candidate = PROJECT_ROOT / candidate

            try:
                resolved = candidate.resolve()
            except OSError:
                continue

            if (
                resolved.exists()
                and resolved.is_file()
                and PROJECT_ROOT in resolved.parents
                and resolved != path
            ):
                results.append(resolved)

    return sorted(set(results))


def symbol_evidence(text: str, symbol: str) -> list[str]:
    upper = text.upper()

    evidence = []

    if symbol.upper() in upper:
        evidence.append("SYMBOL_LITERAL")

    root = symbol.upper().replace("USD", "")

    if root in upper:
        evidence.append("ROOT_LITERAL")

    if "--SYMBOLS" in upper or "--TARGETS" in upper:
        evidence.append("TARGET_ARGUMENT")

    return evidence


def main() -> int:
    print("=== ETHUSD BACKFILL PATH AUDIT V1 ===")
    print("mode=research_read_only")
    print(f"unit={UNIT}")
    print(f"timeframe={TIMEFRAME}")
    print("backfill_execution_allowed=0")
    print("systemd_changes_allowed=0")
    print("market_data_writes_allowed=0")
    print()

    exec_start = systemd_property("ExecStart")
    fragment_path = systemd_property("FragmentPath")
    result = systemd_property("Result")
    main_status = systemd_property("ExecMainStatus")

    print(
        "SERVICE_ROW "
        f"result={result} "
        f"exec_main_status={main_status} "
        f"fragment_path={fragment_path}"
    )

    print(
        "SERVICE_EXEC_ROW "
        f"exec_start={normalize(exec_start)}"
    )

    root_paths = extract_existing_paths(exec_start)

    print()
    print("EXECUTION_CHAIN_ROWS")

    inspected_text: dict[str, str] = {}
    pending = list(root_paths)
    visited: set[Path] = set()

    while pending:
        path = pending.pop(0)

        if path in visited:
            continue

        visited.add(path)

        try:
            source_text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            source_text = ""

        inspected_text[str(path)] = source_text

        btc = symbol_evidence(
            source_text,
            "BTCUSD",
        )
        eth = symbol_evidence(
            source_text,
            "ETHUSD",
        )

        print(
            "EXECUTION_CHAIN_ROW "
            f"path={path} "
            f"btc_evidence={','.join(btc) or 'NONE'} "
            f"eth_evidence={','.join(eth) or 'NONE'}"
        )

        for line_no, line in enumerate(
            source_text.splitlines(),
            start=1,
        ):
            upper = line.upper()

            if (
                "BTC" in upper
                or "ETH" in upper
                or "SYMBOL" in upper
                or "TARGET" in upper
                or "BACKFILL" in upper
            ):
                print(
                    "CHAIN_SOURCE_ROW "
                    f"path={path} "
                    f"line={line_no} "
                    f"text={normalize(line)}"
                )

        for child in child_project_paths(
            path,
            source_text,
        ):
            if child not in visited:
                pending.append(child)

    db = os.environ["DATABASE_URL"]

    with psycopg.connect(
        db,
        row_factory=dict_row,
    ) as conn:
        conn.execute("SET TRANSACTION READ ONLY")

        rows = conn.execute(
            """
            WITH latest AS (
                SELECT max(ts) AS max_ts
                FROM public.market_bars
                WHERE symbol IN ('BTCUSD','ETHUSD')
                  AND timeframe=%s
            )
            SELECT
                b.symbol,
                count(*) AS bars,
                min(b.ts) AS first_ts,
                max(b.ts) AS last_ts,
                extract(
                    epoch FROM (
                        l.max_ts-max(b.ts)
                    )
                ) / 3600.0
                    AS relative_staleness_hours
            FROM public.market_bars b
            CROSS JOIN latest l
            WHERE b.symbol = ANY(%s)
              AND b.timeframe=%s
            GROUP BY b.symbol,l.max_ts
            ORDER BY b.symbol
            """,
            (
                TIMEFRAME,
                list(SYMBOLS),
                TIMEFRAME,
            ),
        ).fetchall()

    by_symbol = {
        str(row["symbol"]): row
        for row in rows
    }

    print()
    print("MARKET_DATA_ROWS")

    for symbol in SYMBOLS:
        row = by_symbol.get(symbol)

        if not row:
            print(
                "MARKET_DATA_ROW "
                f"symbol={symbol} "
                "status=MISSING"
            )
            continue

        stale = float(
            row["relative_staleness_hours"]
            or 0
        )

        print(
            "MARKET_DATA_ROW "
            f"symbol={symbol} "
            f"bars={row['bars']} "
            f"first_ts={row['first_ts']} "
            f"last_ts={row['last_ts']} "
            f"relative_staleness_hours={stale:.2f}"
        )

    _, journal = run([
        "journalctl",
        "-u",
        UNIT,
        "-n",
        "250",
        "--no-pager",
        "-o",
        "short-iso",
    ])

    btc_lines = []
    eth_lines = []

    for line in journal.splitlines():
        upper = line.upper()

        if "BTC" in upper:
            btc_lines.append(normalize(line))

        if "ETH" in upper:
            eth_lines.append(normalize(line))

    print()
    print(
        "JOURNAL_SUMMARY "
        f"btc_mentions={len(btc_lines)} "
        f"eth_mentions={len(eth_lines)}"
    )

    for line in eth_lines[-30:]:
        print(
            "ETH_JOURNAL_ROW "
            f"text={line}"
        )

    all_source = "\n".join(
        inspected_text.values()
    ).upper()

    btc_target_confirmed = (
        "BTCUSD" in all_source
    )

    eth_target_confirmed = (
        "ETHUSD" in all_source
    )

    eth = by_symbol.get("ETHUSD")
    btc = by_symbol.get("BTCUSD")

    btc_fresh = (
        btc is not None
        and float(
            btc["relative_staleness_hours"]
            or 0
        ) <= 1.0
    )

    eth_fresh = (
        eth is not None
        and float(
            eth["relative_staleness_hours"]
            or 0
        ) <= 1.0
    )

    print()
    print(
        f"btc_target_confirmed="
        f"{int(btc_target_confirmed)}"
    )
    print(
        f"eth_target_confirmed="
        f"{int(eth_target_confirmed)}"
    )
    print(f"btc_fresh={int(btc_fresh)}")
    print(f"eth_fresh={int(eth_fresh)}")

    print("backfill_executed=0")
    print("market_data_writes_performed=0")
    print("systemd_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if not eth_target_confirmed:
        verdict = (
            "ETHUSD_BACKFILL_PATH_"
            "TARGET_NOT_CONFIGURED"
        )
    elif eth_target_confirmed and not eth_fresh:
        verdict = (
            "ETHUSD_BACKFILL_PATH_"
            "TARGET_CONFIGURED_BUT_STALE"
        )
    elif eth_fresh:
        verdict = (
            "ETHUSD_BACKFILL_PATH_"
            "FRESH"
        )
    else:
        verdict = (
            "ETHUSD_BACKFILL_PATH_"
            "REVIEW_REQUIRED"
        )

    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
