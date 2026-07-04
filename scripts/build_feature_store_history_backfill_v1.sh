#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_FEATURE_STORE_HISTORY_BACKFILL_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/004_feature_snapshot_history_backfill_v1.sql <<'SQL'
ALTER TABLE analytics.feature_snapshot_v1
ADD COLUMN IF NOT EXISTS return1_pct NUMERIC(20,8),
ADD COLUMN IF NOT EXISTS return5_pct NUMERIC(20,8),
ADD COLUMN IF NOT EXISTS volume_sma20 NUMERIC(20,4),
ADD COLUMN IF NOT EXISTS volume_ratio20 NUMERIC(20,8);
SQL

cat > src/scripts/build_market_snapshot_history_backfill_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LIMIT = int(os.getenv("BACKFILL_LIMIT", "200000"))
SOURCE_VERSION = "MARKET_SNAPSHOT_HISTORY_BACKFILL_V1"

def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO marketcore.market_snapshot_v1 (
                    symbol, display_name, asset_class, timeframe, bar_ts,
                    open, high, low, close, volume,
                    freshness_sec, quality_status,
                    source_table, source_version, build_id, refreshed_at
                )
                SELECT
                    mb.symbol,
                    '',
                    CASE
                        WHEN mb.symbol LIKE '%@MISX' THEN 'MOEX_SPOT'
                        WHEN mb.symbol LIKE '%@RTSX' THEN 'MOEX_FUTURES'
                        WHEN mb.symbol IN ('BTCUSD','ETHUSD') THEN 'CRYPTO_PROXY'
                        WHEN mb.symbol='IMOEX' THEN 'INDEX'
                        ELSE 'UNKNOWN'
                    END,
                    mb.timeframe,
                    mb.ts,
                    mb.open,
                    mb.high,
                    mb.low,
                    mb.close,
                    mb.volume,
                    EXTRACT(EPOCH FROM (now() - mb.ts::timestamptz))::int,
                    CASE WHEN EXTRACT(EPOCH FROM (now() - mb.ts::timestamptz))::int < 86400 THEN 'FRESH' ELSE 'STALE' END,
                    'public.market_bars',
                    %s,
                    %s,
                    now()
                FROM (
                    SELECT *
                    FROM public.market_bars
                    WHERE ts IS NOT NULL
                      AND close IS NOT NULL
                    ORDER BY ts DESC
                    LIMIT %s
                ) mb
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
            """, (SOURCE_VERSION, build_id, LIMIT))

            cur.execute("SELECT count(*) AS rows FROM marketcore.market_snapshot_v1;")
            rows = int(cur.fetchone()["rows"])

    print("=== MARKET_SNAPSHOT_HISTORY_BACKFILL_V1 ===")
    print(f"market_snapshot_rows={rows}")
    print(f"backfill_limit={LIMIT}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKET_SNAPSHOT_HISTORY_BACKFILL_V1_READY")

if __name__ == "__main__":
    main()
PY

cat > src/scripts/build_feature_snapshot_history_backfill_v1.py <<'PY'
from __future__ import annotations

import os
import uuid
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "FEATURE_STORE_HISTORY_BACKFILL_V1"

def main() -> None:
    build_id = str(uuid.uuid4())

    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                INSERT INTO analytics.feature_snapshot_v1 (
                    symbol, asset_class, timeframe, bar_ts,
                    open, high, low, close, volume,
                    range_abs, range_pct,
                    body_abs, body_pct,
                    upper_wick_pct, lower_wick_pct,
                    hour_msk, weekday_msk,
                    freshness_sec, market_quality_status, feature_quality_score,
                    return1_pct, return5_pct, volume_sma20, volume_ratio20,
                    source_table, source_version, build_id, refreshed_at
                )
                WITH src AS (
                    SELECT
                        ms.*,
                        lag(close, 1) OVER (PARTITION BY symbol, timeframe ORDER BY bar_ts) AS close_lag1,
                        lag(close, 5) OVER (PARTITION BY symbol, timeframe ORDER BY bar_ts) AS close_lag5,
                        avg(volume) OVER (
                            PARTITION BY symbol, timeframe
                            ORDER BY bar_ts
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) AS vol_sma20
                    FROM marketcore.market_snapshot_v1 ms
                    WHERE close IS NOT NULL
                )
                SELECT
                    symbol, asset_class, timeframe, bar_ts,
                    open, high, low, close, volume,

                    (high - low),
                    CASE WHEN close <> 0 THEN ((high - low) / close) * 100 ELSE NULL END,

                    abs(close - open),
                    CASE WHEN close <> 0 THEN (abs(close - open) / close) * 100 ELSE NULL END,

                    CASE WHEN close <> 0 THEN ((high - greatest(open, close)) / close) * 100 ELSE NULL END,
                    CASE WHEN close <> 0 THEN ((least(open, close) - low) / close) * 100 ELSE NULL END,

                    EXTRACT(HOUR FROM bar_ts AT TIME ZONE 'Europe/Moscow')::int,
                    EXTRACT(ISODOW FROM bar_ts AT TIME ZONE 'Europe/Moscow')::int,

                    freshness_sec,
                    quality_status,
                    CASE
                        WHEN quality_status = 'FRESH' AND freshness_sec <= 300 THEN 1.0000
                        WHEN quality_status = 'FRESH' AND freshness_sec <= 900 THEN 0.8500
                        WHEN quality_status = 'FRESH' THEN 0.7000
                        ELSE 0.2500
                    END,

                    CASE WHEN close_lag1 IS NOT NULL AND close_lag1 <> 0 THEN ((close - close_lag1) / close_lag1) * 100 ELSE NULL END,
                    CASE WHEN close_lag5 IS NOT NULL AND close_lag5 <> 0 THEN ((close - close_lag5) / close_lag5) * 100 ELSE NULL END,
                    vol_sma20,
                    CASE WHEN vol_sma20 IS NOT NULL AND vol_sma20 <> 0 THEN volume / vol_sma20 ELSE NULL END,

                    'marketcore.market_snapshot_v1',
                    %s,
                    %s,
                    now()
                FROM src
                ON CONFLICT (symbol, timeframe, bar_ts) DO UPDATE SET
                    open=EXCLUDED.open,
                    high=EXCLUDED.high,
                    low=EXCLUDED.low,
                    close=EXCLUDED.close,
                    volume=EXCLUDED.volume,
                    range_abs=EXCLUDED.range_abs,
                    range_pct=EXCLUDED.range_pct,
                    body_abs=EXCLUDED.body_abs,
                    body_pct=EXCLUDED.body_pct,
                    upper_wick_pct=EXCLUDED.upper_wick_pct,
                    lower_wick_pct=EXCLUDED.lower_wick_pct,
                    return1_pct=EXCLUDED.return1_pct,
                    return5_pct=EXCLUDED.return5_pct,
                    volume_sma20=EXCLUDED.volume_sma20,
                    volume_ratio20=EXCLUDED.volume_ratio20,
                    source_version=EXCLUDED.source_version,
                    build_id=EXCLUDED.build_id,
                    refreshed_at=now();
            """, (SOURCE_VERSION, build_id))

            cur.execute("SELECT count(*) AS rows FROM analytics.feature_snapshot_v1;")
            rows = int(cur.fetchone()["rows"])
            cur.execute("SELECT count(DISTINCT symbol) AS symbols FROM analytics.feature_snapshot_v1;")
            symbols = int(cur.fetchone()["symbols"])

    print("=== FEATURE_STORE_HISTORY_BACKFILL_V1 ===")
    print(f"feature_rows={rows}")
    print(f"feature_symbols={symbols}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=FEATURE_STORE_HISTORY_BACKFILL_V1_READY")

if __name__ == "__main__":
    main()
PY

cat > scripts/test_feature_store_history_backfill_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_FEATURE_STORE_HISTORY_BACKFILL_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/004_feature_snapshot_history_backfill_v1.sql

PYTHONPATH=src python -m py_compile \
  src/scripts/build_market_snapshot_history_backfill_v1.py \
  src/scripts/build_feature_snapshot_history_backfill_v1.py

DATABASE_URL=postgresql:///finam_core BACKFILL_LIMIT=200000 PYTHONPATH=src \
python src/scripts/build_market_snapshot_history_backfill_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_feature_snapshot_history_backfill_v1.py | tee /tmp/feature_store_history_backfill_v1.txt

grep -q "VERDICT=FEATURE_STORE_HISTORY_BACKFILL_V1_READY" /tmp/feature_store_history_backfill_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1;")
symbols=$(psql -At -d finam_core -c "SELECT count(DISTINCT symbol) FROM analytics.feature_snapshot_v1;")
with_return=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1 WHERE return1_pct IS NOT NULL;")
bad_source=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.feature_snapshot_v1 WHERE source_table <> 'marketcore.market_snapshot_v1';")

test "$rows" -gt 136
test "$symbols" -gt 1
test "$with_return" -gt 0
test "$bad_source" = "0"

psql -d finam_core -c "
SELECT symbol, timeframe, bar_ts, close, return1_pct, return5_pct, volume_ratio20, feature_quality_score
FROM analytics.feature_snapshot_v1
ORDER BY bar_ts DESC, symbol
LIMIT 30;
"

echo "feature_history_rows=$rows"
echo "feature_history_symbols=$symbols"
echo "with_return=$with_return"
echo "bad_source=$bad_source"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_FEATURE_STORE_HISTORY_BACKFILL_V1_OK"
SH_TEST

chmod +x scripts/test_feature_store_history_backfill_v1.sh
scripts/test_feature_store_history_backfill_v1.sh

echo "VERDICT=BUILD_FEATURE_STORE_HISTORY_BACKFILL_V1_OK"
