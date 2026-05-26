#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

SYMBOL="${SYMBOL:-BRM6@RTSX}"
TRADE_SOURCE="${TRADE_SOURCE:-paper}"
STRATEGY="${STRATEGY:-}"
TIMEFRAME="${TIMEFRAME:-}"

python - <<'PY'
import os
import psycopg
from finam_core.analytics.trade_pnl_reconstructor import reconstruct_closed_trades

database_url = os.environ.get("DATABASE_URL")
symbol = os.environ.get("SYMBOL", "BRM6@RTSX")
trade_source = os.environ.get("TRADE_SOURCE", "paper")
strategy = os.environ.get("STRATEGY", "")
timeframe = os.environ.get("TIMEFRAME", "")

sql = """
select
    id,
    symbol,
    side,
    qty,
    price,
    commission,
    ts,
    trade_source,
    strategy,
    timeframe
from trades
where is_invalid = false
  and symbol = %(symbol)s
  and trade_source = %(trade_source)s
  and (%(strategy)s = '' or strategy = %(strategy)s)
  and (%(timeframe)s = '' or timeframe = %(timeframe)s)
order by ts asc, id asc
"""

params = {
    "symbol": symbol,
    "trade_source": trade_source,
    "strategy": strategy,
    "timeframe": timeframe,
}

with psycopg.connect(database_url) as conn:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

closed = reconstruct_closed_trades(rows)

gross = sum(x.gross_pnl for x in closed)
net = sum(x.net_pnl for x in closed)
wins = sum(1 for x in closed if x.net_pnl > 0)
losses = sum(1 for x in closed if x.net_pnl < 0)
winrate = wins / len(closed) if closed else 0.0

print(
    "CLOSED_TRADES",
    f"symbol={symbol}",
    f"trade_source={trade_source}",
    f"strategy={strategy or 'ALL'}",
    f"timeframe={timeframe or 'ALL'}",
    f"fills={len(rows)}",
    f"closed={len(closed)}",
    f"gross={gross:.4f}",
    f"net={net:.4f}",
    f"wins={wins}",
    f"losses={losses}",
    f"winrate={winrate:.4f}",
)

for x in closed[-20:]:
    print(
        "CLOSED_TRADE",
        f"entry_id={x.entry_trade_id}",
        f"exit_id={x.exit_trade_id}",
        f"entry={x.entry_side}@{x.entry_price}",
        f"exit={x.exit_side}@{x.exit_price}",
        f"qty={x.qty:.4f}",
        f"net={x.net_pnl:.4f}",
    )
PY
