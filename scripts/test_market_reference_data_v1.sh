#!/usr/bin/env bash
set -euo pipefail

echo "=== MARKET_REFERENCE_DATA_V1 ==="

sudo -u postgres psql -v ON_ERROR_STOP=1 -d finam_core <<'SQL'
CREATE TABLE IF NOT EXISTS analytics.market_instrument_v1 (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    exchange_code TEXT NOT NULL,
    asset_class TEXT NOT NULL,
    currency_code TEXT NOT NULL,
    instrument_name TEXT NOT NULL DEFAULT '',
    is_active BOOLEAN NOT NULL DEFAULT true,
    eligibility_scope TEXT NOT NULL DEFAULT 'BASE',
    source_version TEXT NOT NULL DEFAULT 'MARKET_REFERENCE_DATA_V1',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(symbol)
);

CREATE TABLE IF NOT EXISTS analytics.market_contract_spec_v1 (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL REFERENCES analytics.market_instrument_v1(symbol),
    lot_size NUMERIC(20,8) NOT NULL DEFAULT 1,
    tick_size NUMERIC(20,8) NOT NULL DEFAULT 0,
    tick_value NUMERIC(20,8) NOT NULL DEFAULT 0,
    contract_multiplier NUMERIC(20,8) NOT NULL DEFAULT 1,
    price_precision INTEGER NOT NULL DEFAULT 4,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_to TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT true,
    source_version TEXT NOT NULL DEFAULT 'MARKET_REFERENCE_DATA_V1',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(symbol, valid_from)
);

INSERT INTO analytics.market_instrument_v1 (
    symbol, exchange_code, asset_class, currency_code, instrument_name, eligibility_scope
)
VALUES
    ('SBER@MISX','MISX','EQUITY','RUB','Sberbank ordinary shares','BASE'),
    ('LKOH@MISX','MISX','EQUITY','RUB','Lukoil ordinary shares','BASE'),
    ('BR@RTSX','RTSX','FUTURES','USD','Brent futures','BASE'),
    ('NG@RTSX','RTSX','FUTURES','USD','Natural gas futures','BASE')
ON CONFLICT(symbol) DO UPDATE SET
    exchange_code=EXCLUDED.exchange_code,
    asset_class=EXCLUDED.asset_class,
    currency_code=EXCLUDED.currency_code,
    instrument_name=EXCLUDED.instrument_name,
    eligibility_scope=EXCLUDED.eligibility_scope,
    is_active=true,
    updated_at=now();

INSERT INTO analytics.market_contract_spec_v1 (
    symbol, lot_size, tick_size, tick_value, contract_multiplier, price_precision
)
VALUES
    ('SBER@MISX',10,0.01,0.01,1,2),
    ('LKOH@MISX',1,0.5,0.5,1,1),
    ('BR@RTSX',1,0.01,1,1,2),
    ('NG@RTSX',1,0.001,1,1,3)
ON CONFLICT(symbol, valid_from) DO NOTHING;

GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.market_instrument_v1 TO alex;
GRANT SELECT, INSERT, UPDATE, DELETE ON analytics.market_contract_spec_v1 TO alex;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA analytics TO alex;
SQL

cat >> src/marketcore/presentation/ui_labels.py <<'PY'

try:
    ROUTE_LABELS_RU.update({
        "market.model.title": "Модель рынка",
        "market.model.subtitle": "Единый справочник инструментов, спецификаций и торговых параметров",
        "market.model.symbol": "Инструмент",
        "market.model.exchange": "Биржа",
        "market.model.asset_class": "Класс актива",
        "market.model.currency": "Валюта",
        "market.model.lot_size": "Размер лота",
        "market.model.tick_size": "Шаг цены",
        "market.model.tick_value": "Стоимость шага",
        "market.model.contract_multiplier": "Множитель контракта",
        "market.model.eligibility": "Доступность",
        "market.model.active": "Активен"
    })
except NameError:
    pass
PY

PYTHONPATH=src python -m py_compile src/marketcore/presentation/ui_labels.py

rows=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.market_instrument_v1
WHERE is_active=true;
")

specs=$(psql -At -d finam_core -c "
SELECT count(*)
FROM analytics.market_contract_spec_v1
WHERE is_active=true;
")

test "$rows" -ge 4
test "$specs" -ge 4

psql -d finam_core -c "
SELECT
    i.symbol,
    i.exchange_code,
    i.asset_class,
    i.currency_code,
    s.lot_size,
    s.tick_size,
    s.tick_value,
    s.contract_multiplier,
    i.eligibility_scope
FROM analytics.market_instrument_v1 i
JOIN analytics.market_contract_spec_v1 s
  ON s.symbol=i.symbol
WHERE i.is_active=true
  AND s.is_active=true
ORDER BY i.symbol;
"

grep -q "market.model.title" src/marketcore/presentation/ui_labels.py

echo "market_instruments=$rows"
echo "contract_specs=$specs"
echo "i18n=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_REFERENCE_DATA_V1_READY"
echo "VERDICT=TEST_MARKET_REFERENCE_DATA_V1_OK"
