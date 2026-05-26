#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

SYMBOL="${SYMBOL:-BRM6@RTSX}"
TRADE_SOURCE="${TRADE_SOURCE:-paper}"

python - <<'PY'
import os
from collections import defaultdict
import psycopg

from finam_core.analytics.trade_pnl_reconstructor import reconstruct_closed_trades
from finam_core.analytics.trade_regime_classifier import classify_trade_regime
from finam_core.analytics.trade_session_segmenter import build_trade_sessions

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
        rows = list(cur.fetchall())

by_id = {int(row["id"]): row for row in rows}
sessions = build_trade_sessions(rows)

matrix = defaultdict(list)

for session in sessions:
    if not session.strategy or not session.timeframe:
        continue

    session_rows = [
        row for row in rows
        if session.start_trade_id <= int(row["id"]) <= session.end_trade_id
    ]

    closed = reconstruct_closed_trades(session_rows)

    for trade in closed:
        entry_row = by_id.get(int(trade.entry_trade_id))
        if not entry_row:
            continue

        regime = classify_trade_regime(entry_row["ts"])

        key = (
            session.strategy,
            session.timeframe,
            regime.market_session,
            regime.hour,
        )

        matrix[key].append(trade.net_pnl)

print(
    "REGIME_EDGE_MATRIX",
    f"symbol={symbol}",
    f"trade_source={trade_source}",
    f"groups={len(matrix)}",
)

for key, pnl_values in sorted(matrix.items(), key=lambda x: (x[0][2], x[0][3])):
    strategy, timeframe, market_session, hour = key

    trades = len(pnl_values)
    net = sum(pnl_values)
    wins = sum(1 for x in pnl_values if x > 0)
    losses = sum(1 for x in pnl_values if x < 0)
    winrate = wins / trades if trades else 0.0
    avg = net / trades if trades else 0.0

    status = "VALID" if trades >= 5 and net > 0 and winrate >= 0.45 else "WEAK"

    print(
        "REGIME_EDGE",
        f"status={status}",
        f"strategy={strategy}",
        f"timeframe={timeframe}",
        f"market_session={market_session}",
        f"hour={hour}",
        f"trades={trades}",
        f"net={net:.4f}",
        f"avg={avg:.4f}",
        f"wins={wins}",
        f"losses={losses}",
        f"winrate={winrate:.4f}",
    )
PY
