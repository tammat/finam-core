#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
from datetime import datetime

import psycopg2


def main() -> int:
    parser = argparse.ArgumentParser(description="Operator-confirmed market event risk; never creates orders.")
    parser.add_argument("--event", required=True)
    parser.add_argument("--title-ru", required=True)
    parser.add_argument("--level", choices=("NORMAL", "ELEVATED", "SHOCK", "RECOVERY"), required=True)
    parser.add_argument("--patterns", default="*")
    parser.add_argument("--starts-at", required=True)
    parser.add_argument("--expires-at")
    parser.add_argument("--source-url")
    parser.add_argument("--note")
    parser.add_argument("--actor", default="operator")
    args = parser.parse_args()
    patterns = [item.strip().upper() for item in args.patterns.split(",") if item.strip()]
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor() as cur:
        cur.execute("""
          INSERT INTO analytics.market_event_risk_v1(
            event_code,title_ru,category_code,risk_level,symbol_patterns,starts_at,
            expires_at,is_active,source_url,source_note,confirmed_by)
          VALUES(%s,%s,'GEOPOLITICS',%s,%s,%s,%s,true,%s,%s,%s)
          ON CONFLICT(event_code) DO UPDATE SET title_ru=excluded.title_ru,
            risk_level=excluded.risk_level,symbol_patterns=excluded.symbol_patterns,
            starts_at=excluded.starts_at,expires_at=excluded.expires_at,is_active=true,
            source_url=excluded.source_url,source_note=excluded.source_note,
            confirmed_by=excluded.confirmed_by,updated_at=clock_timestamp()
        """, (args.event,args.title_ru,args.level,patterns,datetime.fromisoformat(args.starts_at),
              datetime.fromisoformat(args.expires_at) if args.expires_at else None,
              args.source_url,args.note,args.actor))
    print(f"event={args.event} level={args.level} patterns={','.join(patterns)}")
    print("paper_profile_changed=0 real_trading_enabled=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
