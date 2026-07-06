#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_MODEL_V1 ==="

mkdir -p sql/marketcore src/scripts scripts

cat > sql/marketcore/001_market_model_v1.sql <<'SQL'
CREATE SCHEMA IF NOT EXISTS marketcore;

CREATE TABLE IF NOT EXISTS marketcore.market_snapshot_v1 (
    symbol TEXT NOT NULL,
    display_name TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    timeframe TEXT NOT NULL,
    bar_ts TIMESTAMPTZ NOT NULL,
    open NUMERIC(20,8),
    high NUMERIC(20,8),
    low NUMERIC(20,8),
    close NUMERIC(20,8),
    volume NUMERIC(20,4),
    freshness_sec INTEGER,
    quality_status TEXT NOT NULL DEFAULT 'UNKNOWN',
    source_table TEXT NOT NULL DEFAULT 'public.market_bars',
    source_version TEXT NOT NULL DEFAULT 'MARKET_MODEL_V1',
    build_id TEXT NOT NULL DEFAULT 'manual',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (symbol, timeframe, bar_ts)
);

CREATE INDEX IF NOT EXISTS ix_market_snapshot_v1_symbol_tf_ts
ON marketcore.market_snapshot_v1(symbol, timeframe, bar_ts DESC);
SQL

cat > src/scripts/build_market_model_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKET_MODEL_V1"

def asset_class(symbol: str) -> str:
    if symbol.endswith("@MISX"):
        return "MOEX_SPOT"
    if symbol.endswith("@RTSX"):
        return "MOEX_FUTURES"
    if symbol in {"BTCUSD", "ETHUSD"}:
        return "CRYPTO_PROXY"
    if symbol == "IMOEX":
        return "INDEX"
    return "UNKNOWN"

def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("DELETE FROM marketcore.market_snapshot_v1;")

            cur.execute("""
                SELECT DISTINCT ON (symbol, timeframe)
                    symbol, timeframe, ts AS bar_ts,
                    open, high, low, close, volume
                FROM public.market_bars
                WHERE ts IS NOT NULL
                ORDER BY symbol, timeframe, ts DESC;
            """)
            rows = cur.fetchall()

            inserted = 0
            for r in rows:
                cur.execute("""
                    SELECT EXTRACT(EPOCH FROM (now() - %s::timestamptz))::int AS age;
                """, (r["bar_ts"],))
                freshness_sec = cur.fetchone()["age"]

                quality_status = "FRESH" if freshness_sec is not None and freshness_sec < 86400 else "STALE"

                cur.execute("""
                    INSERT INTO marketcore.market_snapshot_v1 (
                        symbol, display_name, asset_class, timeframe, bar_ts,
                        open, high, low, close, volume,
                        freshness_sec, quality_status,
                        source_table, source_version, build_id, refreshed_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            'public.market_bars',%s,%s,now())
                    ON CONFLICT (symbol, timeframe, bar_ts) DO UPDATE SET
                        open=EXCLUDED.open,
                        high=EXCLUDED.high,
                        low=EXCLUDED.low,
                        close=EXCLUDED.close,
                        volume=EXCLUDED.volume,
                        freshness_sec=EXCLUDED.freshness_sec,
                        quality_status=EXCLUDED.quality_status,
                        source_version=EXCLUDED.source_version,
                        build_id=EXCLUDED.build_id,
                        refreshed_at=now();
                """, (
                    r["symbol"], "", asset_class(r["symbol"]), r["timeframe"], r["bar_ts"],
                    r["open"], r["high"], r["low"], r["close"], r["volume"],
                    freshness_sec, quality_status, SOURCE_VERSION, build_id,
                ))
                inserted += 1

    print("=== MARKET_MODEL_V1 ===")
    print(f"rows_written={inserted}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_MODEL_V1_READY")

if __name__ == "__main__":
    main()
PY

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core -f sql/marketcore/001_market_model_v1.sql

PYTHONPATH=src python -m py_compile src/scripts/build_market_model_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_market_model_v1.py | tee /tmp/market_model_v1.txt

grep -q "VERDICT=MARKET_MODEL_V1_READY" /tmp/market_model_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore.market_snapshot_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM marketcore.market_snapshot_v1;")

test "$rows" -gt 0
test "$symbols" -gt 1

psql -d finam_core -c "
SELECT symbol, asset_class, timeframe, bar_ts, close, freshness_sec, quality_status
FROM marketcore.market_snapshot_v1
ORDER BY bar_ts DESC
LIMIT 30;
"

echo "market_snapshot_rows=$rows"
echo "market_snapshot_symbols=$symbols"
echo "VERDICT=TEST_MARKET_MODEL_V1_OK"
