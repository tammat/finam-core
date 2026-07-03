#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_INSTRUMENT_REFERENCE_V1 ==="

mkdir -p sql/marketcore src/scripts scripts

cat > sql/marketcore/003_instrument_reference_v1.sql <<'SQL'
CREATE SCHEMA IF NOT EXISTS marketcore;

CREATE TABLE IF NOT EXISTS marketcore.instrument_reference_v1 (
    symbol TEXT PRIMARY KEY,
    display_name TEXT NOT NULL DEFAULT '',
    short_name TEXT NOT NULL DEFAULT '',
    asset_class TEXT NOT NULL DEFAULT '',
    exchange TEXT NOT NULL DEFAULT '',
    board TEXT NOT NULL DEFAULT '',
    currency TEXT NOT NULL DEFAULT '',
    lot_size NUMERIC(20,6),
    min_price_step NUMERIC(20,8),
    price_scale INTEGER,
    tick_value NUMERIC(20,8),
    contract_size NUMERIC(20,8),
    expiration_date DATE,
    underlying_symbol TEXT NOT NULL DEFAULT '',
    finam_security_code TEXT NOT NULL DEFAULT '',
    finam_market TEXT NOT NULL DEFAULT '',
    moex_secid TEXT NOT NULL DEFAULT '',
    isin TEXT NOT NULL DEFAULT '',
    figi TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_tradable BOOLEAN NOT NULL DEFAULT true,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source TEXT NOT NULL DEFAULT 'MARKET_SNAPSHOT',
    source_version TEXT NOT NULL DEFAULT 'INSTRUMENT_REFERENCE_V1',
    build_id TEXT NOT NULL DEFAULT 'manual'
);

CREATE INDEX IF NOT EXISTS ix_instrument_reference_v1_asset_class
ON marketcore.instrument_reference_v1(asset_class);

CREATE INDEX IF NOT EXISTS ix_instrument_reference_v1_exchange
ON marketcore.instrument_reference_v1(exchange);

CREATE INDEX IF NOT EXISTS ix_instrument_reference_v1_active
ON marketcore.instrument_reference_v1(is_active);

GRANT USAGE ON SCHEMA marketcore TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA marketcore TO alex;
SQL

cat > src/scripts/build_instrument_reference_v1.py <<'PY'
from __future__ import annotations

import os
import re
import uuid
from datetime import date

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "INSTRUMENT_REFERENCE_V1"

MONTHS = {
    "F": "январь", "G": "февраль", "H": "март", "J": "апрель",
    "K": "май", "M": "июнь", "N": "июль", "Q": "август",
    "U": "сентябрь", "V": "октябрь", "X": "ноябрь", "Z": "декабрь",
}

ROOT_NAMES = {
    "BR": "Нефть Brent",
    "NG": "Природный газ",
    "GD": "Золото",
    "GL": "Золото",
    "SV": "Серебро",
    "USDRUBF": "Фьючерс доллар / рубль",
    "CNYRUBF": "Фьючерс юань / рубль",
}

SPOT_NAMES = {
    "SBER@MISX": "Сбербанк",
    "GAZP@MISX": "Газпром",
    "LKOH@MISX": "Лукойл",
    "PLZL@MISX": "Полюс",
    "VTBR@MISX": "ВТБ",
    "CNYRUB_TOM@MISX": "Юань / рубль TOM",
    "IMOEX": "Индекс МосБиржи",
    "BTCUSD": "Bitcoin / USD",
    "ETHUSD": "Ethereum / USD",
}

def fut_name(symbol: str) -> str:
    base = symbol.split("@")[0]
    if base in ROOT_NAMES:
        return ROOT_NAMES[base]
    m = re.match(r"([A-Z]+)([FGHJKMNQUVXZ])(\d)$", base)
    if not m:
        return ROOT_NAMES.get(base, symbol)
    root, month_code, year_digit = m.groups()
    name = ROOT_NAMES.get(root, root)
    year = 2020 + int(year_digit)
    month = MONTHS.get(month_code, month_code)
    return f"{name}, {month} {year}"

def exchange(symbol: str) -> str:
    if symbol.endswith("@RTSX"):
        return "FORTS"
    if symbol.endswith("@MISX"):
        return "MOEX"
    if symbol in {"BTCUSD", "ETHUSD"}:
        return "CRYPTO_PROXY"
    if symbol == "IMOEX":
        return "MOEX_INDEX"
    return "UNKNOWN"

def display_name(symbol: str) -> str:
    if symbol in SPOT_NAMES:
        return SPOT_NAMES[symbol]
    if symbol.endswith("@RTSX"):
        return fut_name(symbol)
    return symbol

def main() -> None:
    build_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT symbol, max(asset_class) AS asset_class, min(bar_ts) AS first_seen, max(bar_ts) AS last_seen
                FROM marketcore.market_snapshot_v1
                GROUP BY symbol
                ORDER BY symbol;
            """)
            rows = cur.fetchall()

            for r in rows:
                symbol = r["symbol"]
                name = display_name(symbol)
                cur.execute("""
                    INSERT INTO marketcore.instrument_reference_v1 (
                        symbol, display_name, short_name, asset_class, exchange,
                        first_seen, last_seen, updated_at,
                        source, source_version, build_id
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,now(),'MARKET_SNAPSHOT',%s,%s)
                    ON CONFLICT(symbol) DO UPDATE SET
                        display_name=EXCLUDED.display_name,
                        short_name=EXCLUDED.short_name,
                        asset_class=EXCLUDED.asset_class,
                        exchange=EXCLUDED.exchange,
                        last_seen=EXCLUDED.last_seen,
                        updated_at=now(),
                        source_version=EXCLUDED.source_version,
                        build_id=EXCLUDED.build_id;
                """, (
                    symbol, name, name, r["asset_class"] or "", exchange(symbol),
                    r["first_seen"], r["last_seen"], SOURCE_VERSION, build_id
                ))

    print("=== INSTRUMENT_REFERENCE_V1 ===")
    print(f"rows_written={len(rows)}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=INSTRUMENT_REFERENCE_V1_READY")

if __name__ == "__main__":
    main()
PY

cat > scripts/test_instrument_reference_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_INSTRUMENT_REFERENCE_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore/003_instrument_reference_v1.sql

PYTHONPATH=src python -m py_compile src/scripts/build_instrument_reference_v1.py

DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_instrument_reference_v1.py | tee /tmp/instrument_reference_v1.txt

grep -q "VERDICT=INSTRUMENT_REFERENCE_V1_READY" /tmp/instrument_reference_v1.txt

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore.instrument_reference_v1;")
named=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore.instrument_reference_v1 WHERE display_name <> '';")

test "$rows" -gt 0
test "$named" -gt 0

psql -d finam_core -c "
SELECT symbol, display_name, asset_class, exchange, source
FROM marketcore.instrument_reference_v1
ORDER BY symbol
LIMIT 40;
"

echo "instrument_reference_rows=$rows"
echo "named_rows=$named"
echo "VERDICT=TEST_INSTRUMENT_REFERENCE_V1_OK"
SH_TEST

chmod +x scripts/test_instrument_reference_v1.sh
scripts/test_instrument_reference_v1.sh

echo "VERDICT=BUILD_INSTRUMENT_REFERENCE_V1_OK"
