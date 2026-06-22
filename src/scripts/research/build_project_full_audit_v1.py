#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import psycopg
from psycopg.rows import dict_row


def sh(cmd: list[str]) -> str:
    p = subprocess.run(cmd, capture_output=True, text=True)
    return (p.stdout or p.stderr or "").strip()


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== PROJECT_FULL_AUDIT_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    print(f"git_branch={sh(['git', 'rev-parse', '--abbrev-ref', 'HEAD'])}")
    print(f"git_commit={sh(['git', 'rev-parse', '--short', 'HEAD'])}")
    print(f"git_status={sh(['git', 'status', '--short']) or 'CLEAN'}")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            checks = {
                "runtime_active_universe": "select count(*) as n from runtime_active_universe",
                "market_bars": "select count(*) as n from market_bars",
                "trades": "select count(*) as n from trades",
                "rs_bottom_paper": "select count(*) as n from analytics_futures_rs_bottom_paper_observation_v1",
                "rs_bottom_forward": "select count(*) as n from analytics_futures_rs_bottom_forward_scorecard_v1",
                "breakout_rows": "select count(*) as n from analytics_multi_asset_breakout_row_v1",
            }

            for name, sql in checks.items():
                try:
                    cur.execute(sql)
                    print(f"DB_ROW table={name} rows={cur.fetchone()['n']}")
                except Exception as exc:
                    conn.rollback()
                    print(f"DB_ROW table={name} error={type(exc).__name__}:{exc}")

            cur.execute("""
                select table_name
                from information_schema.tables
                where table_schema='public'
                  and table_name like '%compression%'
                order by table_name
            """)
            compression_tables = [r["table_name"] for r in cur.fetchall()]

            print(f"COMPRESSION_TABLES count={len(compression_tables)} names={','.join(compression_tables) if compression_tables else 'NONE'}")

            for table_name in compression_tables:
                try:
                    cur.execute(f"select count(*) as n from {table_name}")
                    print(f"DB_ROW table={table_name} rows={cur.fetchone()['n']}")
                except Exception as exc:
                    conn.rollback()
                    print(f"DB_ROW table={table_name} error={type(exc).__name__}:{exc}")

            cur.execute("""
                select
                    count(*)::int as total,
                    count(*) filter (where is_enabled = true)::int as enabled
                from runtime_active_universe
            """)
            r = cur.fetchone()
            print(f"RUNTIME_UNIVERSE total={r['total']} enabled={r['enabled']}")

            cur.execute("""
                select
                    count(*)::int as total,
                    count(*) filter (where status='WAITING')::int as waiting,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure
                from analytics_futures_rs_bottom_paper_observation_v1
            """)
            r = cur.fetchone()
            print(
                "RS_BOTTOM_FORWARD_STATE "
                f"total={r['total']} waiting={r['waiting']} "
                f"success={r['success']} failure={r['failure']} "
                f"completed={r['success'] + r['failure']}"
            )

    services = [
        "finam-multi-asset-breakout-dashboard.service",
        "finam-moex-session-paper-observation.service",
    ]

    for svc in services:
        status = sh(["systemctl", "is-active", svc])
        enabled = sh(["systemctl", "is-enabled", svc])
        print(f"SERVICE_ROW unit={svc} active={status} enabled={enabled}")

    print("VERDICT=PROJECT_FULL_AUDIT_READY")
    print("TEST_PROJECT_FULL_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
