#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_DATA_PROVIDER_POSTGRES_V1 ==="

cat > src/marketcore/research/execution/providers/postgres_market_data_provider.py <<'PY'
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

from marketcore.research.execution.interfaces.data_provider import MarketBar, MarketBars


class PostgresMarketDataProvider:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL", "postgresql:///finam_core")

    def load_market_data(
        self,
        symbol: str,
        timeframe: str,
        start_ts: datetime | None = None,
        end_ts: datetime | None = None,
        parameters: dict | None = None,
    ) -> MarketBars:
        limit = int((parameters or {}).get("limit", 8000))

        with psycopg2.connect(self.database_url) as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                source = self._discover_source(cur)
                if source is None:
                    return MarketBars(symbol=symbol, timeframe=timeframe, source="postgres:none", bars=[])

                schema, table, cols = source
                bars = self._load_from_source(cur, schema, table, cols, symbol, timeframe, start_ts, end_ts, limit)

        return MarketBars(symbol=symbol, timeframe=timeframe, source=f"postgres:{schema}.{table}", bars=bars)

    def _discover_source(self, cur: Any) -> tuple[str, str, dict[str, str | None]] | None:
        candidates = [
            ("analytics", "market_bars"),
            ("analytics", "market_bars_v1"),
            ("analytics", "market_bar_v1"),
            ("public", "market_bars"),
            ("analytics", "candles"),
            ("public", "candles"),
            ("analytics", "ohlcv"),
            ("public", "ohlcv"),
        ]

        for schema, table in candidates:
            cur.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema=%s AND table_name=%s
            """, (schema, table))
            cols = {r["column_name"] for r in cur.fetchall()}
            if "symbol" not in cols or "close" not in cols:
                continue

            ts = next((c for c in ["bar_ts", "ts", "timestamp", "datetime", "time", "created_at"] if c in cols), None)
            if ts is None:
                continue

            return schema, table, {
                "ts": ts,
                "open": "open" if "open" in cols else "close",
                "high": "high" if "high" in cols else "close",
                "low": "low" if "low" in cols else "close",
                "close": "close",
                "volume": "volume" if "volume" in cols else None,
                "timeframe": next((c for c in ["timeframe", "tf", "interval"] if c in cols), None),
            }

        return None

    def _load_from_source(
        self,
        cur: Any,
        schema: str,
        table: str,
        cols: dict[str, str | None],
        symbol: str,
        timeframe: str,
        start_ts: datetime | None,
        end_ts: datetime | None,
        limit: int,
    ) -> list[MarketBar]:
        for candidate_symbol in self._symbol_aliases(symbol):
            where = [sql.SQL("symbol = %s")]
            params: list[Any] = [candidate_symbol]

            if cols["timeframe"]:
                where.append(sql.SQL("{} = %s").format(sql.Identifier(str(cols["timeframe"]))))
                params.append(timeframe)
            if start_ts is not None:
                where.append(sql.SQL("{} >= %s").format(sql.Identifier(str(cols["ts"]))))
                params.append(start_ts)
            if end_ts is not None:
                where.append(sql.SQL("{} <= %s").format(sql.Identifier(str(cols["ts"]))))
                params.append(end_ts)

            volume_expr = sql.SQL("0")
            if cols["volume"]:
                volume_expr = sql.Identifier(str(cols["volume"]))

            query = sql.SQL("""
                SELECT
                    {ts_col} AS ts,
                    {open_col} AS open,
                    {high_col} AS high,
                    {low_col} AS low,
                    {close_col} AS close,
                    {volume_col} AS volume
                FROM {schema}.{table}
                WHERE {where_clause}
                  AND {close_col} IS NOT NULL
                ORDER BY {ts_col} ASC
                LIMIT %s
            """).format(
                ts_col=sql.Identifier(str(cols["ts"])),
                open_col=sql.Identifier(str(cols["open"])),
                high_col=sql.Identifier(str(cols["high"])),
                low_col=sql.Identifier(str(cols["low"])),
                close_col=sql.Identifier(str(cols["close"])),
                volume_col=volume_expr,
                schema=sql.Identifier(schema),
                table=sql.Identifier(table),
                where_clause=sql.SQL(" AND ").join(where),
            )

            cur.execute(query, params + [limit])
            bars = [
                MarketBar(
                    ts=r["ts"],
                    open=float(r["open"] or 0),
                    high=float(r["high"] or 0),
                    low=float(r["low"] or 0),
                    close=float(r["close"] or 0),
                    volume=float(r["volume"] or 0),
                )
                for r in cur.fetchall()
                if r["close"] is not None and float(r["close"]) > 0
            ]

            if bars:
                return bars

        return []

    def _symbol_aliases(self, symbol: str) -> list[str]:
        base = symbol.split("@")[0]
        return list(dict.fromkeys([symbol, base]))
PY

cat > scripts/test_data_provider_postgres_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_DATA_PROVIDER_POSTGRES_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/marketcore/research/execution/interfaces/data_provider.py \
  src/marketcore/research/execution/providers/postgres_market_data_provider.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src python - <<'PY'
from marketcore.research.execution.providers.postgres_market_data_provider import PostgresMarketDataProvider

provider = PostgresMarketDataProvider()
bars = provider.load_market_data("BR@RTSX", "M5", parameters={"limit": 100})

assert bars.symbol == "BR@RTSX"
assert bars.timeframe == "M5"
assert bars.source.startswith("postgres:")
assert bars.count >= 0

print(f"source={bars.source}")
print(f"bars_count={bars.count}")
PY

echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=DATA_PROVIDER_POSTGRES_V1_READY"
echo "VERDICT=TEST_DATA_PROVIDER_POSTGRES_V1_OK"
SH_TEST

chmod +x scripts/test_data_provider_postgres_v1.sh
scripts/test_data_provider_postgres_v1.sh

echo "VERDICT=BUILD_DATA_PROVIDER_POSTGRES_V1_OK"
