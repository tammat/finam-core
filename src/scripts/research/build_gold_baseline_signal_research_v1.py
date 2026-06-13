#!/usr/bin/env python3

import os
import psycopg2
import psycopg2.extras

DATABASE_URL=os.environ["DATABASE_URL"]

SYMBOL=os.getenv("GOLD_SYMBOL","GDM6@RTSX")
TIMEFRAME=os.getenv("GOLD_TIMEFRAME","M5")

SQL="""
SELECT ts, close
FROM market_bars
WHERE symbol=%s
  AND timeframe=%s
ORDER BY ts
"""

with psycopg2.connect(DATABASE_URL) as conn:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:

        cur.execute(SQL,(SYMBOL,TIMEFRAME))

        rows=list(cur.fetchall())

closes=[float(r["close"]) for r in rows]

trades=[]

for i in range(20,len(closes)-5):

    mean20=sum(closes[i-20:i])/20.0

    entry=closes[i]
    exit_price=closes[i+5]

    if entry > mean20*1.002:

        pnl=exit_price-entry

        trades.append(pnl)

    elif entry < mean20*0.998:

        pnl=entry-exit_price

        trades.append(pnl)

wins=[x for x in trades if x>0]
losses=[x for x in trades if x<=0]

gross_profit=sum(wins)
gross_loss=abs(sum(losses))

pf=None

if gross_loss>0:
    pf=round(gross_profit/gross_loss,4)

net=sum(trades)

expectancy=0.0

if trades:
    expectancy=net/len(trades)

winrate=0.0

if trades:
    winrate=100.0*len(wins)/len(trades)

print("=== GOLD BASELINE SIGNAL RESEARCH V1 ===")
print("mode=research_only")
print("execution=disabled")
print("runtime_changed=0")
print()

print(
    f"BASELINE_ROW "
    f"symbol={SYMBOL} "
    f"timeframe={TIMEFRAME} "
    f"trades={len(trades)} "
    f"net_pnl={round(net,6)} "
    f"expectancy={round(expectancy,6)} "
    f"winrate={round(winrate,2)} "
    f"profit_factor={pf} "
    f"max_win={round(max(wins),6) if wins else 0} "
    f"max_loss={round(min(losses),6) if losses else 0}"
)

print()
print("VERDICT=GOLD_BASELINE_RESEARCH_RECORDED")
print("GOLD_BASELINE_SIGNAL_RESEARCH_V1_OK")
