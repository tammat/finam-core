#!/usr/bin/env python3

import os
import psycopg2


conn = psycopg2.connect(os.environ["DATABASE_URL"])
cur = conn.cursor()

print("=== CLEAN TRADE STATISTICS V1 ===")
print()

cur.execute("""
select count(*), coalesce(sum(net_pnl),0)
from closed_trades;
""")
raw_trades, raw_pnl = cur.fetchone()

cur.execute("""
select count(*)
from research_closed_trades_quarantine;
""")
quarantined = cur.fetchone()[0]

cur.execute("""
with clean as (
    select *
    from closed_trades ct
    where not exists (
        select 1
        from research_closed_trades_quarantine q
        where q.trade_id = ct.id
    )
)
select
    count(*),
    coalesce(sum(net_pnl),0),
    coalesce(sum(case when net_pnl > 0 then net_pnl else 0 end),0),
    coalesce(sum(case when net_pnl < 0 then abs(net_pnl) else 0 end),0),
    coalesce(avg(net_pnl),0),
    coalesce(
        avg(case when net_pnl > 0 then 1 else 0 end),
        0
    )
from clean;
""")

(
    clean_trades,
    clean_pnl,
    gross_profit,
    gross_loss,
    expectancy,
    winrate,
) = cur.fetchone()

pf = 0.0
if gross_loss > 0:
    pf = float(gross_profit) / float(gross_loss)

print(
    f"RAW_TRADES={raw_trades} "
    f"RAW_NET_PNL={float(raw_pnl):.8f}"
)

print(
    f"QUARANTINED_TRADES={quarantined}"
)

print(
    f"CLEAN_TRADES={clean_trades}"
)

print(
    f"CLEAN_NET_PNL={float(clean_pnl):.8f}"
)

print(
    f"GROSS_PROFIT={float(gross_profit):.8f}"
)

print(
    f"GROSS_LOSS={float(gross_loss):.8f}"
)

print(
    f"PF={pf:.8f}"
)

print(
    f"EXPECTANCY={float(expectancy):.8f}"
)

print(
    f"WINRATE={float(winrate):.4f}"
)

print()
print("BY_SYMBOL")

cur.execute("""
with clean as (
    select *
    from closed_trades ct
    where not exists (
        select 1
        from research_closed_trades_quarantine q
        where q.trade_id = ct.id
    )
)
select
    symbol,
    count(*),
    sum(net_pnl)
from clean
group by symbol
order by sum(net_pnl) desc;
""")

for symbol, trades, pnl in cur.fetchall():
    print(
        f"SYMBOL_ROW "
        f"symbol={symbol} "
        f"trades={trades} "
        f"net_pnl={float(pnl):.8f}"
    )

print()
print("BY_STRATEGY")

cur.execute("""
with clean as (
    select *
    from closed_trades ct
    where not exists (
        select 1
        from research_closed_trades_quarantine q
        where q.trade_id = ct.id
    )
)
select
    coalesce(strategy,'UNKNOWN'),
    count(*),
    sum(net_pnl)
from clean
group by 1
order by sum(net_pnl) desc;
""")

for strategy, trades, pnl in cur.fetchall():
    print(
        f"STRATEGY_ROW "
        f"strategy={strategy} "
        f"trades={trades} "
        f"net_pnl={float(pnl):.8f}"
    )

print()
print("VERDICT=OK")
