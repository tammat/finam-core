#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

SYMBOL="${SYMBOL:-BRM6@RTSX}"
TRADE_SOURCE="${TRADE_SOURCE:-paper}"

python - <<'PY'
import os
import psycopg

from finam_core.analytics.session_edge_builder import build_session_edge_results

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise SystemExit("DATABASE_URL is not set")

symbol = os.environ.get("SYMBOL", "BRM6@RTSX")
trade_source = os.environ.get("TRADE_SOURCE", "paper")

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
    timeframe,
    payload
from trades
where is_invalid = false
  and symbol = %(symbol)s
  and trade_source = %(trade_source)s
order by ts asc, id asc
"""

with psycopg.connect(database_url) as conn:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            sql,
            {
                "symbol": symbol,
                "trade_source": trade_source,
            },
        )
        rows = cur.fetchall()

results = build_session_edge_results(rows)

print(
    "SESSION_EDGE_SUMMARY",
    f"symbol={symbol}",
    f"trade_source={trade_source}",
    f"fills={len(rows)}",
    f"sessions={len(results)}",
)

total_trades = 0
total_net = 0.0
total_wins = 0
total_losses = 0

for item in results:
    b = item.bucket
    s = item.session

    total_trades += b.trades
    total_net += b.gross_pnl
    total_wins += b.wins
    total_losses += b.losses

    print(
        "SESSION_EDGE",
        f"session={s.session_id}",
        f"ids={s.start_trade_id}-{s.end_trade_id}",
        f"fills={s.fills}",
        f"strategy={s.strategy or 'NA'}",
        f"timeframe={s.timeframe or 'NA'}",
        f"closed={b.trades}",
        f"net={b.gross_pnl:.4f}",
        f"avg={b.avg_pnl:.4f}",
        f"wins={b.wins}",
        f"losses={b.losses}",
        f"winrate={b.winrate:.4f}",
    )

total_winrate = total_wins / total_trades if total_trades else 0.0

print(
    "EDGE_TOTAL_CLEAN",
    f"closed={total_trades}",
    f"net={total_net:.4f}",
    f"wins={total_wins}",
    f"losses={total_losses}",
    f"winrate={total_winrate:.4f}",
)
PY
