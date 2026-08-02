from __future__ import annotations

import os
import subprocess
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row


MSK = ZoneInfo("Europe/Moscow")
DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SERVICES = ("finam-paper-pipeline.service", "finam-paper-safe.service")
EXPECTED_CONTRACTS = ("BRQ6@RTSX", "NGQ6@RTSX")
EXPECTED_V5_OBSERVATIONS = (
    "BRQ6@RTSX",
    "SBER@MISX",
    "GDU6@RTSX",
    "CNYRUBF@RTSX",
)
SOURCE = "MONDAY_PREFLIGHT_V2"


def _active(service: str) -> bool:
    return subprocess.run(
        ["systemctl", "is-active", "--quiet", service], check=False
    ).returncode == 0


def _service_contracts() -> str:
    result = subprocess.run(
        ["systemctl", "show", "finam-paper-pipeline.service", "-p", "Environment", "-p", "ExecStart"],
        check=False, text=True, capture_output=True,
    )
    return result.stdout


def _v5_bar_contracts() -> str:
    result = subprocess.run(
        ["systemctl", "show", "finam-v5-bars-fast.service", "-p", "ExecStart"],
        check=False, text=True, capture_output=True,
    )
    return result.stdout


def required_timeframes(now: datetime) -> tuple[str, ...]:
    if now.weekday() >= 5:
        return ()
    minute = now.hour * 60 + now.minute
    if minute < 6 * 60 + 50:
        return ()
    if minute < 6 * 60 + 55:
        return ("M1",)
    if minute < 7 * 60 + 5:
        return ("M1", "M5")
    return ("M1", "M5", "M15")


def main() -> int:
    now = datetime.now(MSK)
    failures: list[str] = []
    attention: list[str] = []

    for service in SERVICES:
        if not _active(service):
            failures.append(f"SERVICE_INACTIVE:{service}")

    effective = _service_contracts()
    for contract in EXPECTED_CONTRACTS:
        if contract not in effective:
            failures.append(f"ACTIVE_CONTRACT_MISSING:{contract}")

    v5_effective = _v5_bar_contracts()
    for contract in EXPECTED_V5_OBSERVATIONS:
        if contract not in v5_effective:
            failures.append(f"V5_OBSERVATION_SOURCE_MISSING:{contract}")

    load_1m = float(os.getloadavg()[0])
    if load_1m >= 3.0:
        attention.append(f"HOST_LOAD_HIGH:{load_1m:.2f}")

    stat = os.statvfs("/")
    free_pct = 100.0 * stat.f_bavail / max(stat.f_blocks, 1)
    if free_pct < 15.0:
        failures.append(f"ROOT_DISK_LOW:{free_pct:.1f}")

    with psycopg.connect(DB, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics.market_open_preflight_v2 (
                check_id UUID PRIMARY KEY, checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                status_code TEXT NOT NULL, reason_codes TEXT NOT NULL,
                load_1m NUMERIC NOT NULL, root_free_pct NUMERIC NOT NULL,
                required_timeframes TEXT NOT NULL, freshness JSONB NOT NULL,
                stale_lifecycle_count BIGINT NOT NULL DEFAULT 0,
                source_version TEXT NOT NULL
            )
            """
        )
        freshness: dict[str, str | None] = {}
        for timeframe in required_timeframes(now):
            cur.execute(
                "SELECT max(ts) latest FROM market_bars WHERE timeframe=%s",
                (timeframe,),
            )
            latest = cur.fetchone()["latest"]
            freshness[timeframe] = latest.isoformat() if latest else None
            maximum_age = {"M1": 180, "M5": 480, "M15": 1200}[timeframe]
            if latest is None or (now - latest).total_seconds() > maximum_age:
                failures.append(f"BAR_NOT_FRESH:{timeframe}")

        cur.execute(
            """
            SELECT count(*) AS total
            FROM position_lifecycle_state l
            LEFT JOIN real_portfolio_positions p ON p.symbol=l.symbol AND p.qty<>0
            WHERE l.remaining_qty<>0 AND l.updated_at < now()-interval '24 hours'
              AND p.symbol IS NULL
            """
        )
        stale_lifecycle = int(cur.fetchone()["total"])
        if stale_lifecycle:
            failures.append(f"ORPHAN_LIFECYCLE:{stale_lifecycle}")

        cur.execute("""
            SELECT count(*) AS total
            FROM analytics.entry_exit_recommendation_v1
            WHERE metrics #>> '{negative_control,control_code}'='TIME_SHIFTED_ENTRY_V2'
              AND (metrics #>> '{economics_decomposition,gross_expectancy_r}' IS NULL
                OR metrics #>> '{economics_decomposition,roundtrip_cost_r}' IS NULL)
        """)
        economics_missing = int(cur.fetchone()["total"])
        if economics_missing:
            attention.append(f"EDGE_ECONOMICS_BACKFILL_PENDING:{economics_missing}")

        cur.execute("""
            SELECT count(*) AS total FROM (
              SELECT strategy_code,symbol_group,side_code,count(*)
              FROM analytics.entry_exit_promotion_workflow_v1
              WHERE workflow_stage NOT IN ('REJECTED','ROLLED_BACK','SUPERSEDED')
              GROUP BY 1,2,3 HAVING count(*)>1
            ) duplicated
        """)
        duplicate_active = int(cur.fetchone()["total"])
        if duplicate_active:
            failures.append(f"DUPLICATE_ACTIVE_SHADOW_CANDIDATE:{duplicate_active}")

        cur.execute("""
            SELECT count(DISTINCT CASE
              WHEN symbol_group='BR' THEN 'BRQ6@RTSX'
              WHEN symbol_group='GOLD' THEN 'GDU6@RTSX'
              WHEN symbol_group='CNY' THEN 'CNYRUBF@RTSX'
              WHEN symbol_group='SBER' THEN 'SBER@MISX' END) AS total
            FROM analytics.entry_exit_promotion_workflow_v1
            WHERE symbol_group IN ('BR','GOLD','CNY','SBER')
              AND workflow_stage NOT IN ('REJECTED','ROLLED_BACK','SUPERSEDED')
        """)
        v5_research_branches = int(cur.fetchone()["total"])
        if v5_research_branches < len(EXPECTED_V5_OBSERVATIONS):
            attention.append(
                f"V5_RESEARCH_BRANCH_INCOMPLETE:{v5_research_branches}/{len(EXPECTED_V5_OBSERVATIONS)}"
            )

        status = "BLOCK" if failures else ("ATTENTION" if attention else "READY")
        reasons = failures + attention
        cur.execute(
            """
            INSERT INTO analytics.market_open_preflight_v2 (
                check_id,status_code,reason_codes,load_1m,root_free_pct,
                required_timeframes,freshness,stale_lifecycle_count,source_version
            ) VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
            """,
            (str(uuid.uuid4()), status, ",".join(reasons) or "OK", load_1m,
             free_pct, ",".join(required_timeframes(now)),
             __import__("json").dumps(freshness), stale_lifecycle, SOURCE),
        )
        conn.commit()

    print(f"MONDAY_PREFLIGHT status={status}")
    print(f"reasons={','.join(reasons) or 'OK'}")
    print(f"load_1m={load_1m:.2f} root_free_pct={free_pct:.1f}")
    print(f"required_timeframes={','.join(required_timeframes(now)) or 'PRE_OPEN'}")
    print(f"edge_economics_missing={economics_missing}")
    print(f"duplicate_active_shadow_candidates={duplicate_active}")
    print(f"v5_research_branches={v5_research_branches}/{len(EXPECTED_V5_OBSERVATIONS)}")
    print("real_trading_enabled=0")
    print("VERDICT=MONDAY_PREFLIGHT_V2_OK")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
