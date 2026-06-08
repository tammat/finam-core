#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ["DATABASE_URL"]
SINCE_UTC = os.getenv("POST_FILTER_SINCE_UTC", "2026-06-08 14:40:00+00")
SINCE_MSK = os.getenv("POST_FILTER_SINCE_MSK", "2026-06-08 17:40:00")
SYMBOLS = [s.strip() for s in os.getenv("POST_FILTER_SYMBOLS", "BRN6@RTSX,NGN6@RTSX").split(",") if s.strip()]

GATE_RE = re.compile(r"PIPE_NG_SMART_ENTRY_QUALITY_GATE_V1 .*?allowed=(?P<allowed>[01]) ")

SQL = """
WITH base AS (
    SELECT
        CASE
            WHEN root_symbol IS NOT NULL AND root_symbol <> '' THEN root_symbol
            WHEN symbol LIKE 'BR%%' THEN 'BR'
            WHEN symbol LIKE 'NG%%' THEN 'NG'
            ELSE split_part(symbol,'@',1)
        END AS root,
        symbol,
        net_pnl,
        COALESCE(exit_ts, closed_at, created_at) AS ts
    FROM closed_trades
    WHERE symbol = ANY(%s)
      AND COALESCE(exit_ts, closed_at, created_at) >= %s
)
SELECT
    root,
    COUNT(*) closed_trades,
    ROUND(COALESCE(SUM(net_pnl),0)::numeric,6) net_pnl,
    ROUND(COALESCE(AVG(net_pnl),0)::numeric,6) expectancy,
    ROUND(100.0 * SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) / NULLIF(COUNT(*),0),2) winrate,
    ROUND(COALESCE(SUM(CASE WHEN net_pnl > 0 THEN net_pnl ELSE 0 END),0)::numeric,6) gross_profit,
    ROUND(COALESCE(ABS(SUM(CASE WHEN net_pnl < 0 THEN net_pnl ELSE 0 END)),0)::numeric,6) gross_loss,
    MAX(ts) last_trade_ts
FROM base
GROUP BY root
ORDER BY root;
"""

def pf(gp, gl):
    gp = float(gp or 0)
    gl = float(gl or 0)
    return None if gl <= 0 else round(gp / gl, 4)

def main():
    print("=== BR NG POST FILTER SCORECARD V2 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"since_utc={SINCE_UTC}")
    print(f"symbols={','.join(SYMBOLS)}")
    print()

    proc = subprocess.run(
        ["journalctl", "-u", "finam-paper-pipeline.service", "--since", SINCE_MSK, "--no-pager", "-l"],
        text=True, capture_output=True, check=False,
    )

    ng_total = ng_allowed = ng_blocked = 0
    for line in proc.stdout.splitlines():
        m = GATE_RE.search(line)
        if not m:
            continue
        ng_total += 1
        if m.group("allowed") == "1":
            ng_allowed += 1
        else:
            ng_blocked += 1

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL, (SYMBOLS, SINCE_UTC))
            rows = {r["root"]: dict(r) for r in cur.fetchall()}

    print("POST_FILTER_ROOT_ROWS")
    for root in ("BR", "NG"):
        r = rows.get(root, {})
        closed = int(r.get("closed_trades") or 0)
        expectancy = float(r.get("expectancy") or 0)
        profit_factor = pf(r.get("gross_profit"), r.get("gross_loss"))

        if closed < 20:
            status = "WATCH_LOW_SAMPLE"
        elif expectancy > 0 and profit_factor and profit_factor > 1:
            status = "PROFITABLE"
        elif expectancy < 0:
            status = "UNDER_REVIEW"
        else:
            status = "WATCH"

        print(
            "ROOT_ROW "
            f"root={root} "
            f"signals_total={ng_total if root == 'NG' else None} "
            f"signals_allowed={ng_allowed if root == 'NG' else None} "
            f"signals_blocked={ng_blocked if root == 'NG' else None} "
            f"closed_trades={closed} "
            f"net_pnl={r.get('net_pnl') or 0} "
            f"expectancy={r.get('expectancy') or 0} "
            f"winrate={r.get('winrate')} "
            f"profit_factor={profit_factor} "
            f"last_trade_ts={r.get('last_trade_ts')} "
            f"status={status}"
        )

    print()
    print("BR_NG_POST_FILTER_SCORECARD_V2_OK")

if __name__ == "__main__":
    main()
