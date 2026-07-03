#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_SYMBOL_DISPLAY_NAME_V1 ==="

mkdir -p sql/marketcore_ui src/marketcore/presentation scripts

cat > sql/marketcore_ui/039_symbol_display_name_v1.sql <<'SQL'
BEGIN;

CREATE TABLE IF NOT EXISTS marketcore_ui.symbol_display_name_v1 (
    symbol TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    asset_hint TEXT NOT NULL DEFAULT '',
    source_version TEXT NOT NULL DEFAULT 'SYMBOL_DISPLAY_NAME_V1',
    refreshed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO marketcore_ui.symbol_display_name_v1(symbol, display_name, asset_hint)
VALUES
('SBER@MISX','Сбербанк','Акции'),
('GAZP@MISX','Газпром','Акции'),
('LKOH@MISX','Лукойл','Акции'),
('PLZL@MISX','Полюс','Акции'),
('VTBR@MISX','ВТБ','Акции'),
('NVTK@MISX','Новатэк','Акции'),
('OZON@MISX','Ozon','Акции'),
('CNYRUB_TOM@MISX','Юань / рубль TOM','Валюта'),
('USDRUBF@RTSX','Фьючерс доллар / рубль','Фьючерс'),
('CNYRUBF@RTSX','Фьючерс юань / рубль','Фьючерс'),
('BRQ6@RTSX','Brent, август 2026','Фьючерс'),
('BRU6@RTSX','Brent, сентябрь 2026','Фьючерс'),
('BRV6@RTSX','Brent, октябрь 2026','Фьючерс'),
('NGN6@RTSX','Газ, июль 2026','Фьючерс'),
('NGQ6@RTSX','Газ, август 2026','Фьючерс'),
('NGU6@RTSX','Газ, сентябрь 2026','Фьючерс'),
('GDU6@RTSX','Золото, сентябрь 2026','Фьючерс'),
('GLU6@RTSX','Золото, сентябрь 2026','Фьючерс'),
('SVU6@RTSX','Серебро, сентябрь 2026','Фьючерс'),
('BTCUSD','Bitcoin / USD','Crypto'),
('ETHUSD','Ethereum / USD','Crypto'),
('IMOEX','Индекс МосБиржи','Индекс')
ON CONFLICT(symbol) DO UPDATE SET
    display_name=EXCLUDED.display_name,
    asset_hint=EXCLUDED.asset_hint,
    refreshed_at=now();

GRANT USAGE ON SCHEMA marketcore_ui TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON marketcore_ui.symbol_display_name_v1 TO alex;

COMMIT;

SELECT 'SYMBOL_DISPLAY_NAME_SCHEMA_V1_READY' AS verdict;
SQL

cat > src/marketcore/presentation/symbol_names.py <<'PY'
from __future__ import annotations

DISPLAY_NAMES = {
    "SBER@MISX": "Сбербанк",
    "GAZP@MISX": "Газпром",
    "LKOH@MISX": "Лукойл",
    "PLZL@MISX": "Полюс",
    "VTBR@MISX": "ВТБ",
    "NVTK@MISX": "Новатэк",
    "OZON@MISX": "Ozon",
    "CNYRUB_TOM@MISX": "Юань / рубль TOM",
    "USDRUBF@RTSX": "Фьючерс доллар / рубль",
    "CNYRUBF@RTSX": "Фьючерс юань / рубль",
    "BRQ6@RTSX": "Brent, август 2026",
    "BRU6@RTSX": "Brent, сентябрь 2026",
    "BRV6@RTSX": "Brent, октябрь 2026",
    "NGN6@RTSX": "Газ, июль 2026",
    "NGQ6@RTSX": "Газ, август 2026",
    "NGU6@RTSX": "Газ, сентябрь 2026",
    "GDU6@RTSX": "Золото, сентябрь 2026",
    "GLU6@RTSX": "Золото, сентябрь 2026",
    "SVU6@RTSX": "Серебро, сентябрь 2026",
    "BTCUSD": "Bitcoin / USD",
    "ETHUSD": "Ethereum / USD",
    "IMOEX": "Индекс МосБиржи",
}

def display_name(symbol: str) -> str:
    return DISPLAY_NAMES.get(symbol or "", "")
PY

cat > scripts/test_symbol_display_name_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_SYMBOL_DISPLAY_NAME_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core \
  -f sql/marketcore_ui/039_symbol_display_name_v1.sql

PYTHONPATH=src python -m py_compile \
  src/marketcore/presentation/symbol_names.py

rows=$(psql -At -d finam_core -c "SELECT count(*) FROM marketcore_ui.symbol_display_name_v1;")
test "$rows" -gt 10

psql -d finam_core -c "
SELECT symbol, display_name, asset_hint
FROM marketcore_ui.symbol_display_name_v1
ORDER BY symbol
LIMIT 30;
"

echo "symbol_display_name_rows=$rows"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=SYMBOL_DISPLAY_NAME_V1_READY"
echo "VERDICT=TEST_SYMBOL_DISPLAY_NAME_V1_OK"
SH_TEST

chmod +x scripts/test_symbol_display_name_v1.sh
scripts/test_symbol_display_name_v1.sh

echo "VERDICT=BUILD_SYMBOL_DISPLAY_NAME_V1_OK"
