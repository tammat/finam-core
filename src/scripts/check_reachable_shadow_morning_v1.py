from __future__ import annotations

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "REACHABLE_SHADOW_MORNING_AUDIT_V1"
MSK = ZoneInfo("Europe/Moscow")


def main() -> int:
    reasons: list[str] = []
    with psycopg.connect(DB, row_factory=dict_row) as conn, conn.cursor() as cur:
        cur.execute("SELECT pg_try_advisory_xact_lock(184008) AS locked")
        if not cur.fetchone()["locked"]:
            print("VERDICT=REACHABLE_SHADOW_MORNING_AUDIT_ALREADY_RUNNING")
            return 0

        now = datetime.now(MSK)
        if now.weekday() >= 5 or (now.hour, now.minute) < (7, 5):
            print("VERDICT=REACHABLE_SHADOW_MORNING_AUDIT_OUTSIDE_WINDOW")
            return 0
        cur.execute("""
            SELECT 1 FROM analytics.reachable_shadow_morning_audit_v1
            WHERE (checked_at AT TIME ZONE 'Europe/Moscow')::date=%s
            LIMIT 1
        """, (now.date(),))
        if cur.fetchone():
            print("VERDICT=REACHABLE_SHADOW_MORNING_AUDIT_ALREADY_RECORDED")
            return 0

        cur.execute("""
            SELECT count(*)::int challenger_count,
                   count(*) FILTER (WHERE latest_bar_at>=clock_timestamp()-interval '12 minutes')::int
                     AS fresh_symbol_count,
                   coalesce(sum(matched),0)::int matched_count,
                   coalesce(sum(entered),0)::int entered_count,
                   coalesce(sum(completed),0)::int completed_count,
                   count(*) FILTER (WHERE paper_allowed)::int paper_allowed_count,
                   count(*) FILTER (WHERE real_allowed)::int real_allowed_count,
                   jsonb_agg(jsonb_build_object(
                     'challenger_code',s.challenger_code,'symbol',s.observation_symbol,
                     'frozen_at',s.frozen_at,'latest_bar_at',latest_bar_at,
                     'matched',s.matched,'entered',s.entered,'completed',s.completed,
                     'verdict',s.prospective_verdict) ORDER BY s.challenger_code) AS challengers
            FROM analytics.reachable_shadow_challenger_status_v1 s
            JOIN analytics.reachable_shadow_challenger_v1 c USING(challenger_code)
            LEFT JOIN LATERAL (
              SELECT max(ts) latest_bar_at FROM market_bars
              WHERE symbol=s.observation_symbol AND timeframe='M5'
            ) bars ON true
        """)
        summary = dict(cur.fetchone())

        cur.execute("""
            SELECT count(*)::int total
            FROM analytics.reachable_shadow_challenger_v1 c
            JOIN analytics.entry_exit_signal_shadow_pair_v2 p
              ON p.symbol_code=c.observation_symbol
             AND p.strategy_code=c.strategy_code
             AND p.side_code=c.side_code
             AND p.candidate_code=c.candidate_code
             AND p.label_start_ts<c.frozen_at
        """)
        pre_freeze_excluded = int(cur.fetchone()["total"] or 0)

        if summary["challenger_count"] == 0:
            reasons.append("NO_REACHABLE_CHALLENGERS")
        if summary["fresh_symbol_count"] < summary["challenger_count"]:
            reasons.append(
                f"M5_NOT_FRESH:{summary['fresh_symbol_count']}/{summary['challenger_count']}"
            )
        if summary["paper_allowed_count"]:
            reasons.append(f"UNSAFE_PAPER_ALLOWED:{summary['paper_allowed_count']}")
        if summary["real_allowed_count"]:
            reasons.append(f"UNSAFE_REAL_ALLOWED:{summary['real_allowed_count']}")

        unsafe = summary["paper_allowed_count"] or summary["real_allowed_count"]
        status = "BLOCK" if unsafe else ("ATTENTION" if reasons else "READY")
        evidence = {
            "challengers": summary.get("challengers") or [],
            "prospective_only": True,
            "pre_freeze_rows_excluded": pre_freeze_excluded,
            "paper_changed": False,
            "real_changed": False,
        }
        cur.execute("""
            INSERT INTO analytics.reachable_shadow_morning_audit_v1 (
              status_code,reason_codes,challenger_count,fresh_symbol_count,
              matched_count,entered_count,completed_count,pre_freeze_excluded_count,
              paper_allowed_count,real_allowed_count,evidence,source_version
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
        """, (
            status, reasons, summary["challenger_count"], summary["fresh_symbol_count"],
            summary["matched_count"], summary["entered_count"], summary["completed_count"],
            pre_freeze_excluded, summary["paper_allowed_count"],
            summary["real_allowed_count"], json.dumps(evidence, default=str), SOURCE_VERSION,
        ))
        conn.commit()

    print(f"status={status} reasons={','.join(reasons) or 'OK'}")
    print(
        f"challengers={summary['challenger_count']} fresh={summary['fresh_symbol_count']} "
        f"matched={summary['matched_count']} entered={summary['entered_count']} "
        f"completed={summary['completed_count']} pre_freeze_excluded={pre_freeze_excluded}"
    )
    print("paper_changed=0 real_changed=0")
    print(f"VERDICT={SOURCE_VERSION}_OK")
    return 1 if status == "BLOCK" else 0


if __name__ == "__main__":
    raise SystemExit(main())
