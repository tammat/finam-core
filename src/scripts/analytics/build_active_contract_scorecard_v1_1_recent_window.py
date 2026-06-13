from datetime import datetime, timezone, timedelta
import os
import psycopg2
from psycopg2.extras import RealDictCursor

WINDOW_DAYS = int(os.getenv("WINDOW_DAYS", "7"))

sql = """
SELECT
    COALESCE(root_symbol,
        CASE
            WHEN symbol LIKE 'NG%%' THEN 'NG'
            WHEN symbol LIKE 'BR%%' THEN 'BR'
            WHEN symbol LIKE 'USDRUB%%' THEN 'USDRUB'
            ELSE split_part(symbol,'@',1)
        END
    ) AS root_symbol,
    symbol,
    COUNT(*) trades,
    ROUND(SUM(net_pnl)::numeric,6) net_pnl,
    ROUND(AVG(net_pnl)::numeric,6) expectancy,
    ROUND(
        100.0 *
        SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*),0),
        2
    ) winrate,
    MAX(exit_ts) last_trade_ts
FROM closed_trades
WHERE exit_ts >= NOW() - (%s || ' days')::interval
GROUP BY 1,2
ORDER BY net_pnl DESC;
"""

conn = psycopg2.connect(os.environ["DATABASE_URL"])

with conn.cursor(cursor_factory=RealDictCursor) as cur:
    cur.execute(sql, (WINDOW_DAYS,))
    rows = cur.fetchall()

print("=== ACTIVE CONTRACT SCORECARD V1.1 RECENT WINDOW ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print(f"window_days={WINDOW_DAYS}")
print()

for r in rows:
    print(
        f"ROW root={r['root_symbol']} "
        f"symbol={r['symbol']} "
        f"trades={r['trades']} "
        f"net_pnl={r['net_pnl']} "
        f"expectancy={r['expectancy']} "
        f"winrate={r['winrate']} "
        f"last_trade_ts={r['last_trade_ts']}"
    )

print()
print(f"ROWS={len(rows)}")
print("ACTIVE_CONTRACT_SCORECARD_V1_1_RECENT_WINDOW_OK")
