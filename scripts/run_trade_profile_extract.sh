#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python - <<'PY'
import os
import psycopg
from finam_core.analytics.trade_profile_extractor import extract_trade_profile_rows

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise SystemExit("DATABASE_URL is not set")

sql = """
select
    id,
    symbol,
    side,
    qty,
    price,
    0.0 as realized_pnl,
    strategy,
    timeframe,
    payload as raw_json
from trades
where is_invalid = false
order by id desc
limit 50
"""

with psycopg.connect(database_url) as conn:
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(sql)
        rows = cur.fetchall()

profiles = extract_trade_profile_rows(rows)

print(f"TRADE_PROFILE_ROWS count={len(profiles)}")

for p in profiles[:20]:
    print(
        "TRADE_PROFILE",
        f"id={p.trade_id}",
        f"symbol={p.symbol}",
        f"side={p.side}",
        f"qty={p.qty}",
        f"price={p.price}",
        f"pnl={p.realized_pnl}",
        f"strategy={p.strategy or 'NA'}",
        f"regime={p.regime or 'NA'}",
        f"session={p.session or 'NA'}",
        f"entry={p.entry_reason or 'NA'}",
        f"exit={p.exit_reason or 'NA'}",
    )
PY
