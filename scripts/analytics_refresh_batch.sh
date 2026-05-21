#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

TIMEFRAME="${TIMEFRAME:-M5}"
DEFAULT_STRATEGY="${DEFAULT_STRATEGY:-br_conservative_breakout}"
COMMISSION="${COMMISSION:-0.0001}"
TOP_N="${TOP_N:-5}"

python - <<'PY' > /tmp/analytics_symbols.tsv
from finam_core.analytics.statistics_repository import StatisticsRepository
import psycopg
import os

repo = StatisticsRepository()
top_n = int(os.getenv("TOP_N", "5"))
from finam_core.analytics.symbol_strategy_mapper import map_symbol_to_strategy

timeframe = os.getenv("TIMEFRAME", "M5")

rows = []

with psycopg.connect(repo.database_url) as conn:
    with conn.cursor() as cur:
        # 1. Символы из текущего портфеля / реальных позиций
        for table in ("real_portfolio_snapshots", "broker_position_snapshots", "portfolio_snapshots"):
            try:
                cur.execute(f"""
                    SELECT DISTINCT symbol
                    FROM {table}
                    WHERE symbol IS NOT NULL
                      AND symbol <> ''
                    LIMIT 100
                """)
                for (symbol,) in cur.fetchall():
                    sym = str(symbol)
                    rows.append((sym, map_symbol_to_strategy(sym), timeframe, "portfolio"))
            except Exception:
                pass

        # 2. Топ-5 MOEX / radar candidates
        for table in ("market_opportunity_metrics", "moex_top_universe", "moex_liquid_universe"):
            try:
                cur.execute(f"""
                    SELECT DISTINCT symbol
                    FROM {table}
                    WHERE symbol IS NOT NULL
                      AND symbol <> ''
                    LIMIT %s
                """, (top_n,))
                for (symbol,) in cur.fetchall():
                    sym = str(symbol)
                    rows.append((sym, map_symbol_to_strategy(sym), timeframe, "moex_top"))
                break
            except Exception:
                pass

seen = set()
for symbol, strategy, timeframe, source in rows:
    key = (symbol, strategy, timeframe)
    if key in seen:
        continue
    seen.add(key)
    print(f"{symbol}\t{strategy}\t{timeframe}\t{source}")
PY

echo "ANALYTICS_BATCH_SYMBOLS"
cat /tmp/analytics_symbols.tsv

while IFS=$'\t' read -r SYMBOL STRATEGY TIMEFRAME SOURCE; do
  [ -z "${SYMBOL:-}" ] && continue

  echo "ANALYTICS_BATCH_START symbol=$SYMBOL strategy=$STRATEGY timeframe=$TIMEFRAME source=$SOURCE"

  ./scripts/analytics_refresh_all.sh "$SYMBOL" "$STRATEGY" "$TIMEFRAME" "$COMMISSION" || {
    echo "ANALYTICS_BATCH_FAILED symbol=$SYMBOL strategy=$STRATEGY timeframe=$TIMEFRAME source=$SOURCE"
    continue
  }

  echo "ANALYTICS_BATCH_OK symbol=$SYMBOL strategy=$STRATEGY timeframe=$TIMEFRAME source=$SOURCE"

done < /tmp/analytics_symbols.tsv

echo "ANALYTICS_REFRESH_BATCH_OK"
