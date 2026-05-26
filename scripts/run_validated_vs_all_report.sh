#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

SYMBOL="${SYMBOL:-BRM6@RTSX}"
TRADE_SOURCE="${TRADE_SOURCE:-paper}"

python - <<'PY'
import os
import psycopg

from finam_core.analytics.trade_pnl_reconstructor import reconstruct_closed_trades
from finam_core.analytics.trade_regime_classifier import classify_trade_regime
from finam_core.analytics.trade_session_segmenter import build_trade_sessions
from finam_core.analytics.validated_profile import is_validated_profile
from finam_core.analytics.validated_vs_all_report import compare_validated_vs_all

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

all_pnl = []
validated_pnl = []
rejected_pnl = []

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

        is_validated = is_validated_profile(
            symbol=str(entry_row["symbol"]),
            strategy=str(session.strategy),
            timeframe=str(session.timeframe),
            hour_utc=int(regime.hour),
        )

        all_pnl.append(trade.net_pnl)

        if is_validated:
            validated_pnl.append(trade.net_pnl)
        else:
            rejected_pnl.append(trade.net_pnl)

stats = compare_validated_vs_all(
    all_pnl=all_pnl,
    validated_pnl=validated_pnl,
    rejected_pnl=rejected_pnl,
)

print(
    "VALIDATED_VS_ALL_SUMMARY",
    f"symbol={symbol}",
    f"trade_source={trade_source}",
    f"all_trades={len(all_pnl)}",
    f"validated_trades={len(validated_pnl)}",
    f"rejected_trades={len(rejected_pnl)}",
)

for item in stats:
    print(
        "EDGE_COMPARE",
        f"name={item.name}",
        f"trades={item.trades}",
        f"net={item.net_pnl:.4f}",
        f"gross_profit={item.gross_profit:.4f}",
        f"gross_loss={item.gross_loss:.4f}",
        f"avg={item.avg_pnl:.4f}",
        f"winrate={item.winrate:.4f}",
        f"profit_factor={item.profit_factor:.4f}",
        f"max_consecutive_losses={item.max_consecutive_losses}",
        f"max_drawdown={item.max_drawdown:.4f}",
    )
PY
