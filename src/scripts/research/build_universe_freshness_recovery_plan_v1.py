#!/usr/bin/env python3
"""
UNIVERSE_FRESHNESS_RECOVERY_PLAN_V1

Read-only план восстановления M5 freshness для инструментов,
которые предыдущим forensic audit подтверждены как BACKFILL_READY.

Ничего не запускает.
Не делает backfill.
Не стартует/restart systemd.
Не пишет в PostgreSQL.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass

import psycopg2
import psycopg2.extras


TIMEFRAME = "M5"

MOEX_EQUITY_TARGETS = {
    "SBERP@MISX",
    "VTBR@MISX",
    "NVTK@MISX",
    "T@MISX",
    "SBER@MISX",
    "LKOH@MISX",
    "PLZL@MISX",
}

MOEX_INDEX_TARGETS = {
    "IMOEX",
    "RTSI",
}

CRYPTO_TARGETS = {
    "ETHUSD",
}


TARGETS = (
    "SBERP@MISX",
    "VTBR@MISX",
    "NVTK@MISX",
    "T@MISX",
    "SBER@MISX",
    "LKOH@MISX",
    "PLZL@MISX",
    "IMOEX",
    "RTSI",
    "ETHUSD",
)

EXPECTED_OWNER = {
    "SBERP@MISX": "finam-paper-pipeline.service",
    "VTBR@MISX": "finam-paper-pipeline.service",
    "NVTK@MISX": "finam-paper-pipeline.service",
    "T@MISX": "finam-paper-pipeline.service",
    "SBER@MISX": "finam-paper-pipeline.service",
    "LKOH@MISX": "finam-paper-pipeline.service",
    "PLZL@MISX": "finam-paper-pipeline.service",
    "IMOEX": "finam-moex-index-online.timer",
    "RTSI": "finam-moex-index-online.timer",
    "ETHUSD": "finam-crypto-backfill.timer",
}


@dataclass(frozen=True)
class UnitState:
    unit: str
    active: str
    enabled: str
    fragment_path: str
    triggers: str


def run_command(args: list[str]) -> str:
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
    )

    text = (
        result.stdout.strip()
        or result.stderr.strip()
        or "NONE"
    )

    return re.sub(r"\s+", " ", text)


def unit_property(unit: str, prop: str) -> str:
    value = run_command(
        [
            "systemctl",
            "show",
            unit,
            f"--property={prop}",
            "--value",
        ]
    )

    return value or "NONE"


def unit_state(unit: str) -> UnitState:
    return UnitState(
        unit=unit,
        active=run_command(
            ["systemctl", "is-active", unit]
        ),
        enabled=run_command(
            ["systemctl", "is-enabled", unit]
        ),
        fragment_path=unit_property(
            unit,
            "FragmentPath",
        ),
        triggers=unit_property(
            unit,
            "Triggers",
        ),
    )


def timer_service(timer: str) -> str:
    # systemd timer foo.timer обычно активирует foo.service.
    if timer.endswith(".timer"):
        return timer[:-6] + ".service"
    return "NONE"


def exec_start(unit: str) -> str:
    return unit_property(unit, "ExecStart")


def recent_journal(unit: str) -> str:
    result = subprocess.run(
        [
            "journalctl",
            "-u",
            unit,
            "-n",
            "12",
            "--no-pager",
            "-o",
            "short-iso",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    text = (
        result.stdout.strip()
        or result.stderr.strip()
        or "NONE"
    )

    lines = [
        re.sub(r"\s+", " ", line.strip())
        for line in text.splitlines()
        if line.strip()
    ]

    return " || ".join(lines[-12:]) or "NONE"


def main() -> int:
    print("=== UNIVERSE FRESHNESS RECOVERY PLAN V1 ===")
    print("mode=read_only_plan")
    print(f"timeframe={TIMEFRAME}")
    print(f"targets={len(TARGETS)}")
    print("backfill_execution_allowed=0")
    print("systemd_changes_allowed=0")
    print("market_data_writes_allowed=0")
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
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:

            cur.execute(
                """
                WITH universe_latest AS (
                    SELECT max(ts) AS latest_ts
                    FROM public.market_bars
                    WHERE timeframe=%s
                )
                SELECT
                    b.symbol,
                    count(*) AS bars,
                    count(DISTINCT b.ts::date)
                        AS trading_days,
                    max(b.ts) AS last_ts,
                    u.latest_ts AS universe_last_ts,
                    extract(
                        epoch FROM (
                            u.latest_ts-max(b.ts)
                        )
                    ) / 3600.0
                        AS relative_staleness_hours
                FROM public.market_bars b
                CROSS JOIN universe_latest u
                WHERE b.symbol = ANY(%s)
                  AND b.timeframe=%s
                GROUP BY
                    b.symbol,
                    u.latest_ts
                ORDER BY b.symbol
                """,
                (
                    TIMEFRAME,
                    list(TARGETS),
                    TIMEFRAME,
                ),
            )

            rows = {
                str(row["symbol"]): dict(row)
                for row in cur.fetchall()
            }

        ready = 0
        review = 0

        print("RECOVERY_PLAN_ROWS")

        for symbol in TARGETS:
            row = rows.get(symbol)

            if row is None:
                print(
                    "RECOVERY_PLAN_ROW "
                    f"symbol={symbol} "
                    "status=REVIEW_REQUIRED "
                    "reason=M5_SERIES_NOT_FOUND"
                )
                review += 1
                continue

            owner = EXPECTED_OWNER[symbol]
            state = unit_state(owner)

            effective_unit = owner
            linked_service = "NONE"

            if owner.endswith(".timer"):
                linked_service = timer_service(owner)
                effective_unit = linked_service

            effective_exec = exec_start(
                effective_unit
            )

            journal = recent_journal(
                effective_unit
            )

            owner_exists = (
                state.fragment_path != "NONE"
                and "not found" not in
                state.fragment_path.lower()
            )

            exec_confirmed = (
                effective_exec != "NONE"
                and "not found"
                not in effective_exec.lower()
            )

            # Recovery readiness нельзя определять только
            # существованием systemd unit / ExecStart.
            #
            # MOEX в выходной нельзя сравнивать по wall-clock
            # freshness с 24/7 crypto.
            #
            # ETHUSD уже отдельно подтверждён как configured
            # target, который остаётся stale после успешного job.
            if symbol in MOEX_INDEX_TARGETS:
                if owner_exists and exec_confirmed:
                    status = "NO_RECOVERY_REQUIRED"
                    reason = (
                        "MOEX_ONLINE_INGESTION_PATH_HEALTHY_"
                        "CALENDAR_REVIEW"
                    )
                else:
                    status = "REVIEW_REQUIRED"
                    reason = (
                        "MOEX_INDEX_INGESTION_PATH_"
                        "NOT_CONFIRMED"
                    )
                    review += 1

            elif symbol in MOEX_EQUITY_TARGETS:
                status = "REVIEW_REQUIRED"
                reason = (
                    "MOEX_CALENDAR_AWARE_FRESHNESS_REQUIRED"
                )
                review += 1

            elif symbol in CRYPTO_TARGETS:
                status = "REVIEW_REQUIRED"
                reason = (
                    "ETHUSD_TARGET_CONFIGURED_BUT_STALE"
                )
                review += 1

            elif owner_exists and exec_confirmed:
                status = "PLAN_READY"
                reason = (
                    "CANONICAL_RECOVERY_PATH_CONFIRMED"
                )
                ready += 1

            else:
                status = "REVIEW_REQUIRED"
                reason = (
                    "RECOVERY_EXECUTION_PATH_"
                    "NOT_CONFIRMED"
                )
                review += 1

            print(
                "RECOVERY_PLAN_ROW "
                f"symbol={symbol} "
                f"last_ts={row['last_ts']} "
                "relative_staleness_hours="
                f"{float(row['relative_staleness_hours']):.2f} "
                f"owner={owner} "
                f"owner_active={state.active} "
                f"owner_enabled={state.enabled} "
                f"linked_service={linked_service} "
                f"effective_unit={effective_unit} "
                f"status={status} "
                f"reason={reason}"
            )

            print(
                "RECOVERY_EXEC_ROW "
                f"symbol={symbol} "
                f"unit={effective_unit} "
                f"exec_start={effective_exec}"
            )

            print(
                "RECOVERY_JOURNAL_ROW "
                f"symbol={symbol} "
                f"unit={effective_unit} "
                f"journal={journal}"
            )

        print()
        print(
            "SUMMARY_ROW "
            f"targets={len(TARGETS)} "
            f"plan_ready={ready} "
            f"review_required={review}"
        )

        print("recovery_commands_executed=0")
        print("backfill_executed=0")
        print("market_data_writes_performed=0")
        print("systemd_changed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        print(
            "VERDICT="
            "UNIVERSE_FRESHNESS_RECOVERY_PLAN_V1_READY"
        )

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
