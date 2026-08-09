#!/usr/bin/env python3
"""
UNIVERSE_MARKET_DATA_FRESHNESS_AUDIT_V1

Read-only forensic audit top near-ready instruments.

Цель:
- установить фактическую причину stale M5;
- найти ingestion service/timer/script;
- проверить systemd status;
- определить, подтверждена ли возможность backfill;
- ничего не запускать;
- ничего не записывать в PostgreSQL.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import psycopg2
import psycopg2.extras


ROOT = Path("/opt/finam-core")

CONFIG_PATH = ROOT / (
    "config/research/universe_edge_search_v1.json"
)

SEARCH_ROOTS = (
    ROOT / "deploy/systemd",
    ROOT / "infra",
    ROOT / "src/scripts",
    ROOT / "scripts",
)

SYSTEMD_ROOT = Path("/etc/systemd/system")

TEXT_SUFFIXES = {
    ".py",
    ".sh",
    ".service",
    ".timer",
    ".json",
    ".conf",
    ".env",
}


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text())


def safe_read(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except (OSError, PermissionError):
        return ""


def systemctl_state(unit: str) -> tuple[str, str]:
    active = subprocess.run(
        ["systemctl", "is-active", unit],
        capture_output=True,
        text=True,
        check=False,
    )

    enabled = subprocess.run(
        ["systemctl", "is-enabled", unit],
        capture_output=True,
        text=True,
        check=False,
    )

    return (
        active.stdout.strip()
        or active.stderr.strip()
        or "unknown",
        enabled.stdout.strip()
        or enabled.stderr.strip()
        or "unknown",
    )


def candidate_files() -> list[Path]:
    files: list[Path] = []

    roots = list(SEARCH_ROOTS)

    if SYSTEMD_ROOT.exists():
        roots.append(SYSTEMD_ROOT)

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if (
                path.is_file()
                and (
                    path.suffix in TEXT_SUFFIXES
                    or path.name.endswith(".service")
                    or path.name.endswith(".timer")
                )
            ):
                files.append(path)

    return sorted(set(files))


def symbol_tokens(symbol: str) -> list[str]:
    upper = symbol.upper()

    tokens = {
        upper,
        upper.split("@", 1)[0],
    }

    if upper.endswith("@MISX"):
        tokens.add("MISX")

    if upper.endswith("@RTSX"):
        tokens.add("RTSX")

    if upper in {"BTCUSD", "ETHUSD"}:
        tokens.add("CRYPTO")

    return sorted(
        token
        for token in tokens
        if len(token) >= 3
    )


def ingestion_matches(
    symbol: str,
    files: list[Path],
) -> list[dict]:
    matches = []

    tokens = symbol_tokens(symbol)

    generic_markers = (
        "market_bars",
        "market bars",
        "market-bars",
        "backfill",
        "ingest",
        "market_data",
        "market-data",
        "bars",
    )

    for path in files:
        text = safe_read(path)

        if not text:
            continue

        upper = text.upper()

        exact = any(
            token.upper() in upper
            for token in tokens[:2]
        )

        family = False

        if symbol.upper().endswith("@MISX"):
            family = any(
                marker in upper
                for marker in (
                    "EQUITY",
                    "MISX",
                    "STOCK",
                )
            )

        elif symbol.upper().endswith("@RTSX"):
            family = any(
                marker in upper
                for marker in (
                    "FUTURES",
                    "RTSX",
                    "FUTURE",
                )
            )

        elif symbol.upper() in {
            "BTCUSD",
            "ETHUSD",
        }:
            family = any(
                marker in upper
                for marker in (
                    "CRYPTO",
                    "BTCUSD",
                    "ETHUSD",
                )
            )

        generic = any(
            marker.upper() in upper
            for marker in generic_markers
        )

        if not exact and not (family and generic):
            continue

        evidence = []

        if exact:
            evidence.append("SYMBOL_LITERAL")

        if family:
            evidence.append("ASSET_FAMILY")

        if generic:
            evidence.append("MARKET_DATA_JOB")

        exec_start = ""

        for line in text.splitlines():
            stripped = line.strip()

            if stripped.startswith("ExecStart="):
                exec_start = stripped
                break

        matches.append({
            "path": str(path),
            "evidence": ",".join(evidence),
            "exec_start": exec_start,
            "is_service": path.name.endswith(
                ".service"
            ),
            "is_timer": path.name.endswith(
                ".timer"
            ),
        })

    matches.sort(
        key=lambda row: (
            "SYMBOL_LITERAL"
            not in row["evidence"],
            not row["is_timer"],
            not row["is_service"],
            row["path"],
        )
    )

    return matches


def classify_ingestion_evidence(
    symbol: str,
    timeframe: str,
    match: dict | None,
) -> tuple[bool, str]:
    """
    Строгая классификация ingestion evidence.

    BACKFILL_READY разрешён только если найденный компонент
    действительно относится к загрузке market bars и
    подтверждает требуемый timeframe.
    """
    if not match:
        return False, "NO_MATCH"

    path = str(match.get("path") or "").lower()
    exec_start = str(
        match.get("exec_start") or ""
    ).lower()

    combined = f"{path} {exec_start}"

    # Research, UI, shadow и display-name не являются
    # ingestion owner независимо от наличия symbol literal.
    forbidden_markers = (
        "shadow_validation",
        "shadow-validation",
        "build_runtime_shadow",
        "display_name",
        "display-name",
        "/ui/",
        "/research/build_",
    )

    if any(
        marker in combined
        for marker in forbidden_markers
    ):
        return False, "NON_INGESTION_REFERENCE"

    ingestion_markers = (
        "run_continuous_market_bars_ingestion",
        "market_bars_ingestion",
        "market-bars-ingestion",
        "backfill",
        "market_pipeline",
        "market-pipeline",
        "moex-index-online",
        "crypto-backfill",
    )

    if not any(
        marker in combined
        for marker in ingestion_markers
    ):
        return False, "INGESTION_IMPLEMENTATION_NOT_CONFIRMED"

    # Если job явно перечисляет timeframe-targets,
    # требуем M5, а не только M1.
    if "--targets" in exec_start:
        symbol_upper = symbol.upper()
        tf_token = f"{symbol_upper}={timeframe.upper()}".lower()

        if symbol_upper.lower() in exec_start and tf_token not in exec_start:
            return False, "TIMEFRAME_NOT_CONFIRMED"

    return True, "CANONICAL_INGESTION_CONFIRMED"



def main() -> int:
    cfg = load_config()

    timeframe = cfg["timeframe"]
    minimum_bars = int(cfg["minimum_bars"])
    minimum_days = int(
        cfg["minimum_trading_days"]
    )
    maximum_staleness = float(
        cfg[
            "maximum_relative_staleness_hours"
        ]
    )
    minimum_range = float(
        cfg["minimum_median_range_bps"]
    )

    current_prefixes = tuple(
        str(value).upper()
        for value in cfg[
            "current_branch_prefixes"
        ]
    )

    print(
        "=== UNIVERSE MARKET DATA "
        "FRESHNESS AUDIT V1 ==="
    )
    print("mode=research_read_only")
    print(f"timeframe={timeframe}")
    print("top_n=15")
    print("market_data_writes_allowed=0")
    print("systemd_changes_allowed=0")
    print("backfill_execution_allowed=0")
    print()

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )
    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        with conn.cursor(
            cursor_factory=(
                psycopg2.extras.RealDictCursor
            )
        ) as cur:

            cur.execute(
                """
                WITH base AS (
                    SELECT
                        symbol,
                        timeframe,
                        ts,
                        open::numeric AS open,
                        high::numeric AS high,
                        low::numeric AS low,
                        close::numeric AS close
                    FROM public.market_bars
                    WHERE timeframe=%s
                ),
                latest AS (
                    SELECT max(ts) AS max_ts
                    FROM base
                ),
                stats AS (
                    SELECT
                        symbol,
                        count(*) AS bars,
                        count(
                            DISTINCT ts::date
                        ) AS trading_days,
                        min(ts) AS first_ts,
                        max(ts) AS last_ts,

                        count(*) -
                        count(DISTINCT ts)
                            AS duplicate_rows,

                        count(*) FILTER (
                            WHERE open IS NULL
                               OR high IS NULL
                               OR low IS NULL
                               OR close IS NULL
                               OR high < low
                               OR high < open
                               OR high < close
                               OR low > open
                               OR low > close
                               OR close <= 0
                        ) AS invalid_ohlc_rows,

                        percentile_cont(0.5)
                        WITHIN GROUP (
                            ORDER BY
                                CASE
                                    WHEN close > 0
                                    THEN (
                                        (high-low)
                                        / close
                                    ) * 10000
                                END
                        ) AS median_range_bps

                    FROM base
                    GROUP BY symbol
                )
                SELECT
                    s.*,
                    l.max_ts AS universe_last_ts,
                    extract(
                        epoch FROM (
                            l.max_ts-s.last_ts
                        )
                    ) / 3600.0
                        AS relative_staleness_hours
                FROM stats s
                CROSS JOIN latest l
                ORDER BY s.symbol
                """,
                (timeframe,),
            )

            rows = [
                dict(row)
                for row in cur.fetchall()
            ]

        evaluated = []

        for row in rows:
            symbol = str(row["symbol"])
            upper = symbol.upper()

            reasons = []

            bars = int(row["bars"])
            days = int(row["trading_days"])

            stale = float(
                row[
                    "relative_staleness_hours"
                ]
                or 0
            )

            median_range = float(
                row["median_range_bps"]
                or 0
            )

            if bars < minimum_bars:
                reasons.append(
                    "INSUFFICIENT_BARS"
                )

            if days < minimum_days:
                reasons.append(
                    "INSUFFICIENT_TRADING_DAYS"
                )

            if int(
                row["duplicate_rows"]
            ) > 0:
                reasons.append(
                    "DUPLICATE_TIMESTAMPS"
                )

            if int(
                row["invalid_ohlc_rows"]
            ) > 0:
                reasons.append(
                    "INVALID_OHLC"
                )

            if stale > maximum_staleness:
                reasons.append(
                    "STALE_RELATIVE_TO_UNIVERSE"
                )

            if median_range < minimum_range:
                reasons.append(
                    "LOW_BAR_RANGE"
                )

            if any(
                upper.startswith(prefix)
                for prefix in current_prefixes
            ):
                reasons.append(
                    "CURRENT_RESEARCH_BRANCH"
                )

            evaluated.append({
                **row,
                "reasons": reasons,
                "failed_gates": len(reasons),
                "stale": stale,
                "median_range": median_range,
            })

        near_ready = [
            row
            for row in evaluated
            if row["reasons"]
            == [
                "STALE_RELATIVE_TO_UNIVERSE"
            ]
        ]

        near_ready.sort(
            key=lambda row: (
                -int(row["trading_days"]),
                -int(row["bars"]),
                row["stale"],
                str(row["symbol"]),
            )
        )

        top = near_ready[:15]

        files = candidate_files()

        print("TOP15_FRESHNESS_ROWS")

        confirmed_jobs = 0
        backfill_ready = 0
        unresolved = 0

        for rank, row in enumerate(
            top,
            start=1,
        ):
            symbol = str(row["symbol"])

            matches = ingestion_matches(
                symbol,
                files,
            )

            best = (
                matches[0]
                if matches
                else None
            )

            unit_name = "NONE"
            active = "unknown"
            enabled = "unknown"
            exec_start = "NONE"
            evidence = "NONE"

            if best:
                path = Path(best["path"])

                evidence = (
                    best["evidence"]
                    or "NONE"
                )

                exec_start = (
                    best["exec_start"]
                    or "NONE"
                )

                if (
                    best["is_service"]
                    or best["is_timer"]
                ):
                    unit_name = path.name

                    active, enabled = (
                        systemctl_state(
                            unit_name
                        )
                    )

                confirmed_jobs += 1

            can_backfill, evidence_status = (
                classify_ingestion_evidence(
                    symbol,
                    timeframe,
                    best,
                )
            )

            if can_backfill:
                backfill_ready += 1
                recovery_status = "BACKFILL_READY"
            else:
                unresolved += 1
                recovery_status = evidence_status

            print(
                "FRESHNESS_ROW "
                f"rank={rank} "
                f"symbol={symbol} "
                f"bars={row['bars']} "
                f"trading_days="
                f"{row['trading_days']} "
                f"last_ts={row['last_ts']} "
                f"universe_last_ts="
                f"{row['universe_last_ts']} "
                "relative_staleness_hours="
                f"{row['stale']:.2f} "
                f"job={unit_name} "
                f"job_active={active} "
                f"job_enabled={enabled} "
                f"evidence={evidence} "
                f"recovery_status="
                f"{recovery_status}"
            )

            if best:
                print(
                    "INGESTION_EVIDENCE_ROW "
                    f"symbol={symbol} "
                    f"path={best['path']} "
                    f"exec_start="
                    f"{re.sub(r'\\s+', ' ', exec_start)}"
                )

        print()
        print(
            "SUMMARY_ROW "
            f"top15={len(top)} "
            f"ingestion_job_found="
            f"{confirmed_jobs} "
            f"backfill_ready="
            f"{backfill_ready} "
            f"unresolved={unresolved}"
        )

        print("readiness_policy_changed=0")
        print("market_data_writes_performed=0")
        print("backfill_executed=0")
        print("systemd_changed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        print(
            "VERDICT="
            "UNIVERSE_MARKET_DATA_"
            "FRESHNESS_AUDIT_V1_READY"
        )

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
