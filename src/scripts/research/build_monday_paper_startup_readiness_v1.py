#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess

import psycopg
from psycopg.rows import dict_row


REQUIRED_TIMERS = [
    "finam-multi-asset-breakout-history.timer",
    "finam-multi-asset-compression-history.timer",
    "runtime-rebalance.timer",
]

REQUIRED_SERVICES = [
    "finam-marketcore-dashboard.service",
]


def systemctl_is_active(unit: str) -> bool:
    result = subprocess.run(
        ["systemctl", "is-active", unit],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == "active"


def systemctl_is_enabled(unit: str) -> bool:
    result = subprocess.run(
        ["systemctl", "is-enabled", unit],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() in {"enabled", "static"}


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    failures = []

    env_flags = {
        "RUNTIME_ALLOW_TRADING": os.getenv("RUNTIME_ALLOW_TRADING", "0"),
        "EXECUTION_ENABLED": os.getenv("EXECUTION_ENABLED", "0"),
        "REAL_TRADING_ENABLED": os.getenv("REAL_TRADING_ENABLED", "0"),
    }

    for key, value in env_flags.items():
        if value != "0":
            failures.append(f"{key}_NOT_ZERO")

    timer_rows = []
    for timer in REQUIRED_TIMERS:
        active = systemctl_is_active(timer)
        enabled = systemctl_is_enabled(timer)
        timer_rows.append((timer, active, enabled))
        if not active:
            failures.append(f"{timer}_NOT_ACTIVE")
        if not enabled:
            failures.append(f"{timer}_NOT_ENABLED")

    service_rows = []
    for service in REQUIRED_SERVICES:
        active = systemctl_is_active(service)
        service_rows.append((service, active))
        if not active:
            failures.append(f"{service}_NOT_ACTIVE")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("select count(*)::int as c from runtime_active_universe where is_enabled = true")
            runtime_active = cur.fetchone()["c"]

            cur.execute("""
                select count(*)::int as c
                from runtime_active_universe
                where is_enabled = true and symbol like '%@MISX'
            """)
            active_equities = cur.fetchone()["c"]

            cur.execute("""
                select count(*)::int as c
                from market_bars
                where symbol in ('IMOEX','RTSI') and timeframe in ('M1','M5')
            """)
            index_bars = cur.fetchone()["c"]

            cur.execute("select count(*)::int as c from analytics_multi_asset_compression_snapshot_v1")
            compression_snapshots = cur.fetchone()["c"]

            cur.execute("select count(*)::int as c from analytics_multi_asset_breakout_snapshot_v1")
            breakout_snapshots = cur.fetchone()["c"]

            cur.execute("""
                select count(*)::int as c
                from analytics_multi_asset_compression_follow_through_market_bars_v2
            """)
            compression_follow_v2 = cur.fetchone()["c"]

    if runtime_active < 8:
        failures.append("RUNTIME_ACTIVE_LT_8")
    if active_equities < 8:
        failures.append("ACTIVE_EQUITIES_LT_8")
    if index_bars <= 0:
        failures.append("INDEX_BARS_MISSING")
    if compression_snapshots <= 0:
        failures.append("COMPRESSION_HISTORY_MISSING")
    if breakout_snapshots <= 0:
        failures.append("BREAKOUT_HISTORY_MISSING")
    if compression_follow_v2 <= 0:
        failures.append("COMPRESSION_FOLLOW_V2_MISSING")

    verdict = "MONDAY_PAPER_STARTUP_READY" if not failures else "MONDAY_PAPER_STARTUP_BLOCKED"

    print("=== MONDAY_PAPER_STARTUP_READINESS_V1 ===")
    for key, value in env_flags.items():
        print(f"{key.lower()}={value}")

    for timer, active, enabled in timer_rows:
        print(f"TIMER_ROW unit={timer} active={int(active)} enabled={int(enabled)}")

    for service, active in service_rows:
        print(f"SERVICE_ROW unit={service} active={int(active)}")

    print(f"runtime_active={runtime_active}")
    print(f"active_equities={active_equities}")
    print(f"index_bars={index_bars}")
    print(f"compression_snapshots={compression_snapshots}")
    print(f"breakout_snapshots={breakout_snapshots}")
    print(f"compression_follow_v2={compression_follow_v2}")
    print(f"failures={','.join(failures) if failures else 'NONE'}")
    print(f"VERDICT={verdict}")
    print("TEST_MONDAY_PAPER_STARTUP_READINESS_V1_OK")

    return 0 if verdict == "MONDAY_PAPER_STARTUP_READY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
