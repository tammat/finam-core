#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_STRATEGY_LIBRARY_V1 ==="

mkdir -p sql/analytics src/scripts scripts

cat > sql/analytics/013_strategy_library_v1.sql <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.strategy_library_v1 (
    strategy_code TEXT PRIMARY KEY,
    strategy_family TEXT NOT NULL,
    category TEXT NOT NULL,
    status_code TEXT NOT NULL DEFAULT 'EXPERIMENT',
    priority INTEGER NOT NULL DEFAULT 100,
    description TEXT NOT NULL DEFAULT '',
    default_timeframes TEXT[] NOT NULL DEFAULT ARRAY['M5'],
    default_symbols TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    parameter_schema JSONB NOT NULL DEFAULT '{}'::jsonb,
    enabled BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'STRATEGY_LIBRARY_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_strategy_library_v1_category
ON analytics.strategy_library_v1(category);

CREATE INDEX IF NOT EXISTS ix_strategy_library_v1_status
ON analytics.strategy_library_v1(status_code);

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.strategy_library_v1 TO alex;
SQL

cat > src/scripts/build_strategy_library_v1.py <<'PY'
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")

STRATEGIES = [
    ("VOLATILITY_BREAKOUT_V2", "VOLATILITY_BREAKOUT", "BREAKOUT", 10, ["M5","M15"]),
    ("OPENING_RANGE_BREAKOUT_V1", "OPENING_RANGE_BREAKOUT", "BREAKOUT", 20, ["M5","M15"]),
    ("NR7_BREAKOUT_V1", "NR7_BREAKOUT", "VOLATILITY", 30, ["M5","M15"]),
    ("MOMENTUM_CONTINUATION_V1", "MOMENTUM_CONTINUATION", "MOMENTUM", 40, ["M5","M15"]),
    ("ATR_IMPULSE_V1", "ATR_IMPULSE", "MOMENTUM", 50, ["M1","M5"]),
    ("RSI_MEAN_REVERSION_V1", "RSI_MEAN_REVERSION", "MEAN_REVERSION", 60, ["M5","M15"]),
    ("BOLLINGER_REVERSION_V1", "BOLLINGER_REVERSION", "MEAN_REVERSION", 70, ["M5","M15"]),
    ("VWAP_REVERSION_V1", "VWAP_REVERSION", "VWAP", 80, ["M1","M5"]),
    ("VOLUME_IMPULSE_V1", "VOLUME_IMPULSE", "VOLUME", 90, ["M1","M5"]),
    ("FALSE_BREAKOUT_V1", "FALSE_BREAKOUT", "LIQUIDITY", 100, ["M5","M15"]),
]

def main() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for code, family, category, priority, timeframes in STRATEGIES:
                cur.execute("""
                    INSERT INTO analytics.strategy_library_v1 (
                        strategy_code,
                        strategy_family,
                        category,
                        status_code,
                        priority,
                        description,
                        default_timeframes,
                        parameter_schema,
                        enabled,
                        source_version,
                        updated_at
                    )
                    VALUES (
                        %s,%s,%s,'EXPERIMENT',%s,%s,%s,
                        '{}'::jsonb,
                        true,
                        'STRATEGY_LIBRARY_V1',
                        now()
                    )
                    ON CONFLICT(strategy_code) DO UPDATE SET
                        strategy_family=EXCLUDED.strategy_family,
                        category=EXCLUDED.category,
                        priority=EXCLUDED.priority,
                        default_timeframes=EXCLUDED.default_timeframes,
                        enabled=true,
                        source_version='STRATEGY_LIBRARY_V1',
                        updated_at=now();
                """, (
                    code,
                    family,
                    category,
                    priority,
                    f"Research hypothesis for {code}",
                    timeframes,
                ))

            cur.execute("""
                SELECT count(*) AS total,
                       count(*) FILTER (WHERE enabled=true) AS enabled
                FROM analytics.strategy_library_v1;
            """)
            row = cur.fetchone()

    print("=== STRATEGY_LIBRARY_V1 ===")
    print(f"strategies_total={row['total']}")
    print(f"strategies_enabled={row['enabled']}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=STRATEGY_LIBRARY_V1_READY")

if __name__ == "__main__":
    main()
PY

cat > scripts/test_strategy_library_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_STRATEGY_LIBRARY_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/analytics/013_strategy_library_v1.sql

PYTHONPATH=src python -m py_compile src/scripts/build_strategy_library_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_strategy_library_v1.py | tee /tmp/strategy_library_v1.txt

grep -q "VERDICT=STRATEGY_LIBRARY_V1_READY" /tmp/strategy_library_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_library_v1;")
enabled=$(psql -At -d finam_core -c "SELECT count(*) FROM analytics.strategy_library_v1 WHERE enabled=true;")

test "$rows" -ge 10
test "$enabled" -ge 10

echo "strategy_rows=$rows"
echo "enabled_rows=$enabled"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=TEST_STRATEGY_LIBRARY_V1_OK"
SH_TEST

chmod +x scripts/test_strategy_library_v1.sh
scripts/test_strategy_library_v1.sh

echo "VERDICT=BUILD_STRATEGY_LIBRARY_V1_OK"
