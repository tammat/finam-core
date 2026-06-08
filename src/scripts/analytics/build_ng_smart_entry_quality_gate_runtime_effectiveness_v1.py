#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SINCE_MSK = os.getenv("NG_GATE_RUNTIME_SINCE_MSK", "2026-06-08 17:40:00")
SINCE_UTC = os.getenv("NG_GATE_RUNTIME_SINCE_UTC", "2026-06-08 14:40:00+00")

LOG_CMD = [
    "journalctl",
    "-u",
    "finam-paper-pipeline.service",
    "--since",
    SINCE_MSK,
    "--no-pager",
    "-l",
]

GATE_RE = re.compile(
    r"PIPE_NG_SMART_ENTRY_QUALITY_GATE_V1 .*?"
    r"symbol=(?P<symbol>\S+) .*?"
    r"entry_reason=(?P<entry_reason>\S+) .*?"
    r"regime=(?P<regime>\S*) .*?"
    r"allowed=(?P<allowed>[01]) .*?"
    r"action=(?P<action>\S+) .*?"
    r"reason=(?P<reason>\S+)"
)

SQL_TRADES_AFTER = """
select
    symbol,
    side,
    payload->>'intent_type' as intent_type,
    payload->>'reason' as reason,
    count(*) as rows,
    max(ts) as last_ts
from trades
where ts >= %s
  and symbol='NGN6@RTSX'
  and is_invalid=false
group by symbol, side, payload->>'intent_type', payload->>'reason'
order by last_ts desc;
"""

SQL_CLOSED_AFTER = """
select
    count(*) as trades,
    round(coalesce(sum(net_pnl),0)::numeric,6) as net_pnl,
    round(coalesce(avg(net_pnl),0)::numeric,6) as expectancy,
    round(
        100.0 * sum(case when net_pnl > 0 then 1 else 0 end) / nullif(count(*),0),
        2
    ) as winrate
from closed_trades
where root_symbol='NG'
  and source='closed_trade_engine_v1_1'
  and coalesce(exit_ts, closed_at, created_at) >= %s;
"""

def main() -> None:
    print("=== NG SMART ENTRY QUALITY GATE RUNTIME EFFECTIVENESS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"since_msk={SINCE_MSK}")
    print(f"since_utc={SINCE_UTC}")
    print()

    proc = subprocess.run(LOG_CMD, text=True, capture_output=True, check=False)

    gate_rows = []
    for line in proc.stdout.splitlines():
        m = GATE_RE.search(line)
        if not m:
            continue
        gate_rows.append(m.groupdict())

    total = len(gate_rows)
    blocked = sum(1 for r in gate_rows if r["allowed"] == "0")
    allowed = sum(1 for r in gate_rows if r["allowed"] == "1")

    by_regime = {}
    for r in gate_rows:
        key = (r["regime"] or "EMPTY", r["action"], r["reason"])
        by_regime[key] = by_regime.get(key, 0) + 1

    print("GATE_RUNTIME_SUMMARY")
    print(f"GATE_TOTAL={total}")
    print(f"GATE_ALLOWED={allowed}")
    print(f"GATE_BLOCKED={blocked}")
    print()

    print("GATE_BY_REGIME")
    if not by_regime:
        print("NONE")
    for (regime, action, reason), rows in sorted(by_regime.items()):
        print(
            "GATE_REGIME_ROW "
            f"regime={regime} action={action} reason={reason} rows={rows}"
        )
    print()

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_TRADES_AFTER, (SINCE_UTC,))
            trade_rows = cur.fetchall()

            cur.execute(SQL_CLOSED_AFTER, (SINCE_UTC,))
            closed = cur.fetchone()

    print("NG_TRADES_AFTER_GATE")
    if not trade_rows:
        print("NONE")
    for r in trade_rows:
        print(
            "TRADE_ROW "
            f"symbol={r['symbol']} side={r['side']} "
            f"intent_type={r['intent_type']} reason={r['reason']} "
            f"rows={r['rows']} last_ts={r['last_ts']}"
        )
    print()

    print("NG_CLOSED_AFTER_GATE")
    print(
        "CLOSED_ROW "
        f"trades={closed['trades']} "
        f"net_pnl={closed['net_pnl']} "
        f"expectancy={closed['expectancy']} "
        f"winrate={closed['winrate']}"
    )
    print()

    if total == 0:
        verdict = "NO_GATE_EVENTS_YET"
    elif blocked > 0:
        verdict = "NG_SMART_ENTRY_GATE_RUNTIME_BLOCKING_CONFIRMED"
    else:
        verdict = "NG_SMART_ENTRY_GATE_RUNTIME_ALLOW_ONLY"

    print(f"VERDICT={verdict}")
    print("NG_SMART_ENTRY_QUALITY_GATE_RUNTIME_EFFECTIVENESS_V1_OK")


if __name__ == "__main__":
    main()
