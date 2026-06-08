#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]

SINCE_MSK = os.getenv("NG_POST_GATE_SINCE_MSK", "2026-06-08 17:40:00")
SINCE_UTC = os.getenv("NG_POST_GATE_SINCE_UTC", "2026-06-08 14:40:00+00")

GATE_RE = re.compile(
    r"PIPE_NG_SMART_ENTRY_QUALITY_GATE_V1 .*?"
    r"symbol=(?P<symbol>\S+) .*?"
    r"entry_reason=(?P<entry_reason>\S+) .*?"
    r"regime=(?P<regime>\S*) .*?"
    r"allowed=(?P<allowed>[01]) .*?"
    r"action=(?P<action>\S+) .*?"
    r"reason=(?P<reason>\S+)"
)

SQL_CLOSED = """
SELECT
    COUNT(*) AS trades,
    ROUND(COALESCE(SUM(net_pnl),0)::numeric,6) AS net_pnl,
    ROUND(COALESCE(AVG(net_pnl),0)::numeric,6) AS expectancy,
    ROUND(
        100.0 * SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0),
        2
    ) AS winrate,
    MAX(COALESCE(exit_ts, closed_at, created_at)) AS last_trade_ts
FROM closed_trades
WHERE symbol='NGN6@RTSX'
  AND COALESCE(exit_ts, closed_at, created_at) >= %s;
"""

SQL_FILLS = """
SELECT
    side,
    payload->>'intent_type' AS intent_type,
    payload->>'reason' AS reason,
    COUNT(*) AS rows,
    MAX(ts) AS last_ts
FROM trades
WHERE symbol='NGN6@RTSX'
  AND ts >= %s
  AND is_invalid=false
GROUP BY side, payload->>'intent_type', payload->>'reason'
ORDER BY last_ts DESC;
"""

def main() -> None:
    print("=== NG POST QUALITY GATE SCORECARD V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"since_msk={SINCE_MSK}")
    print(f"since_utc={SINCE_UTC}")
    print()

    proc = subprocess.run(
        [
            "journalctl",
            "-u",
            "finam-paper-pipeline.service",
            "--since",
            SINCE_MSK,
            "--no-pager",
            "-l",
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    gate_rows = []
    for line in proc.stdout.splitlines():
        m = GATE_RE.search(line)
        if m:
            gate_rows.append(m.groupdict())

    total = len(gate_rows)
    blocked = sum(1 for r in gate_rows if r["allowed"] == "0")
    allowed = sum(1 for r in gate_rows if r["allowed"] == "1")

    by_regime = {}
    for r in gate_rows:
        key = (r["regime"] or "EMPTY", r["action"], r["reason"])
        by_regime[key] = by_regime.get(key, 0) + 1

    print("GATE_SUMMARY")
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
            cur.execute(SQL_CLOSED, (SINCE_UTC,))
            closed = cur.fetchone()

            cur.execute(SQL_FILLS, (SINCE_UTC,))
            fills = cur.fetchall()

    print("POST_GATE_CLOSED_SUMMARY")
    print(
        "CLOSED_ROW "
        f"trades={closed['trades']} "
        f"net_pnl={closed['net_pnl']} "
        f"expectancy={closed['expectancy']} "
        f"winrate={closed['winrate']} "
        f"last_trade_ts={closed['last_trade_ts']}"
    )
    print()

    print("POST_GATE_FILLS")
    if not fills:
        print("NONE")
    for r in fills:
        print(
            "FILL_ROW "
            f"side={r['side']} "
            f"intent_type={r['intent_type']} "
            f"reason={r['reason']} "
            f"rows={r['rows']} "
            f"last_ts={r['last_ts']}"
        )
    print()

    if total == 0:
        verdict = "NO_GATE_EVENTS"
    elif blocked > 0 and int(closed["trades"] or 0) == 0:
        verdict = "GATE_BLOCKING_NO_NEW_CLOSED_TRADES_YET"
    elif blocked > 0:
        verdict = "POST_GATE_RESULT_AVAILABLE"
    else:
        verdict = "GATE_ALLOW_ONLY"

    print(f"VERDICT={verdict}")
    print("NG_POST_QUALITY_GATE_SCORECARD_V1_OK")


if __name__ == "__main__":
    main()
